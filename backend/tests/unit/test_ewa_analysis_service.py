from app.models.expiration import AiUsageMetrics
from app.services.document_intelligence import DocumentIntelligenceProvider
from app.services.ewa_analysis_service import analyze_ewa_files_for_consolidation
from app.services.ewa_analysis_service import _is_section_heading
from app.services.ewa_analysis_service import build_expiration_records


class StubAiUsageRepository:
    def __init__(self) -> None:
        self.saved_usages = []

    def save_usages(self, usages) -> None:
        self.saved_usages.extend(usages)


class StubProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        assert "supported until 02.2027" in text
        return [
            {"nombre": "SAP Product Version", "fecha": "02.2027"},
            {"nombre": "SAP Product Version", "fecha": "02.2027"},
            {"nombre": "Kernel", "fecha": "2026-12-31"},
            {"nombre": "Broken", "fecha": "2026-99-99"},
        ]


def test_build_expiration_records_normalizes_and_deduplicates():
    provider = StubProvider()

    result = build_expiration_records(
        "SAP Product Version is supported until 02.2027. Kernel expires on 2026-12-31.",
        provider,
    )

    assert [
        (item.source_section, item.name, item.expiration_date, item.milestone) for item in result
    ] == [
        ("", "SAP Product Version", "2027-02-28", ""),
        ("", "Kernel", "2026-12-31", ""),
    ]


class UsageAwareProvider(DocumentIntelligenceProvider):
    def extract_expirations_with_usage(self, text: str):
        return (
            [{"nombre": "Kernel", "fecha": "2026-12-31"}],
            AiUsageMetrics(input_tokens=700, output_tokens=80, total_tokens=780),
        )

    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        return [{"nombre": "Kernel", "fecha": "2026-12-31"}]


def test_analyze_ewa_files_for_consolidation_persists_ai_usage(monkeypatch):
    repository = StubAiUsageRepository()
    monkeypatch.setattr(
        "app.services.ewa_analysis_service.extract_text",
        lambda filename, payload: "Kernel expires on 2026-12-31.",
    )

    analyze_ewa_files_for_consolidation(
        files=[("a.pdf", b"a"), ("b.pdf", b"b")],
        clients=["Cliente A", "Cliente B"],
        period="2026-04",
        provider=UsageAwareProvider(),
        usage_repository=repository,
    )

    assert [
        (item.client, item.input_tokens, item.output_tokens, item.total_tokens)
        for item in repository.saved_usages
    ] == [
        ("Cliente A", 700, 80, 780),
        ("Cliente B", 700, 80, 780),
    ]


class HallucinatedNameProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        return [
            {"nombre": "Your main priority", "fecha": "2027-12-31"},
        ]


def test_build_expiration_records_reconciles_hallucinated_name_with_source_text():
    provider = HallucinatedNameProvider()

    result = build_expiration_records(
        "SAP Product Version is supported until 2027-12-31.",
        provider,
    )

    assert [(item.source_section, item.name, item.expiration_date, item.milestone) for item in result] == [
        ("", "SAP Product Version", "2027-12-31", ""),
    ]


class GenericEWANameProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        return [
            {"nombre": "Your main product version", "fecha": "31.12.2027"},
            {"nombre": "Your SAP NetWeaver version", "fecha": "31.12.2027"},
        ]


class SpecificProductNameProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        return [
            {"nombre": "EHP7 FOR SAP ERP 6.0", "fecha": "31.12.2027"},
            {"nombre": "SAP NETWEAVER 7.4", "fecha": "31.12.2027"},
        ]


class StructuredPdfNameProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        return [
            {"nombre": "SAP Fiori Front-End Server", "fecha": "31.12.2027"},
            {"nombre": "SUSE Linux Enterprise Server 15 (x86_64)", "fecha": "31.07.2028"},
        ]


def test_build_expiration_records_prefers_structured_product_names_from_ewa_tables():
    provider = GenericEWANameProvider()
    text = """
    SAP Application Release - Maintenance Phases
    SAP Product Version
    End of Mainstream Maintenance
    Status
    EHP7 FOR SAP ERP 6.0
    31.12.2027

    SAP NetWeaver Version
    End of Mainstream Maintenance
    Status
    SAP NETWEAVER 7.4
    31.12.2027

    Your main product version runs under SAP mainstream maintenance until 31.12.2027.
    Your SAP NetWeaver version is supported in combination with your main product version until 31.12.2027.
    """

    result = build_expiration_records(text, provider)

    assert [(item.source_section, item.name, item.expiration_date, item.milestone) for item in result] == [
        ("SAP Application Release - Maintenance Phases", "EHP7 FOR SAP ERP 6.0", "2027-12-31", ""),
        ("SAP Application Release - Maintenance Phases", "SAP NETWEAVER 7.4", "2027-12-31", ""),
    ]


def test_build_expiration_records_keeps_specific_ai_names_when_pdf_text_is_layout_collapsed():
    provider = StructuredPdfNameProvider()
    text = """
    4.2 Maintenance and Update Strategy for SAP Fiori Front-End Server
    SoftwareProduct SAP_UIRelease EndofMaintenance Rating
    SAPFioriFES6.0 | 754 | 31.12.2027 |

    4.6 Operating System(s) - Maintenance Phases
    Host | OperatingSystem | EndofStandard VendorSupport* | EndofExtendedVendor Support* | Comment
    2Hosts | SUSELinuxEnterprise Server15(x86_64) | 31.07.2028 | 31.07.2031 | Limited(LTSS)
    """

    result = build_expiration_records(text, provider)

    assert [(item.source_section, item.name, item.expiration_date, item.milestone) for item in result] == [
        ("", "SAP Fiori Front-End Server", "2027-12-31", ""),
        ("4.6 Operating System(s) - Maintenance Phases", "SUSE Linux Enterprise Server 15 (x86_64)", "2028-07-31", ""),
    ]


def test_build_expiration_records_prefers_component_block_section_over_later_kernel_heading():
    provider = SpecificProductNameProvider()
    text = """
    SAP Application Release - Maintenance Phases
    SAP Product Version
    Status
    EHP7 FOR SAP ERP 6.0

    SAP NetWeaver Version
    Status
    SAP NETWEAVER 7.4

    SAP Kernel Release
    Instance(s)
    SAP Kernel Release
    Patch Level
    Age in Months
    srv-pr-uap-h_UAP_00
    749
    500
    97

    EHP7 FOR SAP ERP 6.0 is supported until 31.12.2027.
    SAP NETWEAVER 7.4 is supported in combination with your main product version until 31.12.2027.
    """

    result = build_expiration_records(text, provider)

    assert [(item.source_section, item.name, item.expiration_date, item.milestone) for item in result] == [
        ("SAP Application Release - Maintenance Phases", "EHP7 FOR SAP ERP 6.0", "2027-12-31", ""),
        ("SAP Application Release - Maintenance Phases", "SAP NETWEAVER 7.4", "2027-12-31", ""),
    ]


class KernelProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        return [
            {"nombre": "SAP Kernel 7.49", "fecha": "2026-12-31"},
        ]


def test_build_expiration_records_keeps_kernel_section_for_kernel_findings():
    text = """
    SAP Kernel Release
    SAP Kernel 7.49
    End of Mainstream Maintenance
    2026-12-31
    """

    result = build_expiration_records(text, KernelProvider())

    assert [(item.source_section, item.name, item.expiration_date, item.milestone) for item in result] == [
        ("SAP Kernel Release", "SAP Kernel 7.49", "2026-12-31", ""),
    ]


class HANAFalsePositiveProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        return [
            {"nombre": "SAP HANA Database", "fecha": "31.12.2023"},
            {"nombre": "SAP HANA Database", "fecha": "06.04.2026"},
            {"nombre": "SAP HANA Database", "fecha": "12.04.2026"},
            {"nombre": "SAP HANA Database", "fecha": "31.05.2029"},
            {"nombre": "SAP HANA Database", "fecha": "31.05.2031"},
        ]


def test_build_expiration_records_filters_analysis_dates_while_preserving_specific_ai_names():
    provider = HANAFalsePositiveProvider()
    text = """
    HANA Database Support Package Stack for HEP
    Support Package Stack
    Current Version
    Maintenance end
    2
    06
    31.12.2023

    Operating System(s) - Maintenance Phases
    Host
    Operating System
    End of Standard Vendor Support*
    End of Extended Vendor Support*
    3 Hosts
    Red Hat Enterprise Linux 8 (x86_64)
    31.05.2029
    31.05.2031

    Analysis Type
    Analysis of Thread Samples
    Data Source
    HOST_SERVICE_THREAD_SAMPLES
    First Day
    06.04.2026
    Last Day
    12.04.2026
    """

    result = build_expiration_records(text, provider)

    assert [(item.source_section, item.name, item.expiration_date, item.milestone) for item in result] == [
        ("HANA Database Support Package Stack for HEP", "SAP HANA Database", "2023-12-31", ""),
        ("Operating System(s) - Maintenance Phases", "SAP HANA Database", "2029-05-31", ""),
        ("Operating System(s) - Maintenance Phases", "SAP HANA Database", "2031-05-31", ""),
    ]


class OperationalDatesProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        return [
            {"nombre": "SAP HANA Database", "fecha": "29.06.2022"},
            {"nombre": "SAP HANA Database", "fecha": "20.09.2022"},
            {"nombre": "SAP HANA Database", "fecha": "02.08.2021"},
            {"nombre": "SAP HANA Database", "fecha": "08.10.2022"},
            {"nombre": "SAP HANA Database", "fecha": "31.12.2023"},
        ]


def test_build_expiration_records_filters_operational_hana_dates_from_revision_and_age_tables():
    provider = OperationalDatesProvider()
    text = """
    4.7 HANA Database Version for HEP
    The following table shows your current SAP HANA database revision.
    Rating | ProductVersion | HANARevision | ReleaseDate | AgeofRevisionin Months | Deployment Date | Ageof Deployment DateinMonths
    2.00SP06 | 2.00.063.00 | 29.06.2022 | 44 | 20.09.2022 | 41

    4.7.1 HANA Database Support Package Stack for HEP
    CurrentVersion | CurrentSupport PackageStack | Available Version | Available Support PackageStack | Maintenance end | Numberofdays until Maintenance End | Rating
    2 | 06 | 2 | 07 | 31.12.2023 | ...Textcut,see SAPNote 3210457

    9.3.1 Age of Support Packages
    Software Component | Release | SupportPackage | Finalassembly date | Ageoffinal assembly datein months | Support Package importdate | AgeofSP importdate inmonths | Rating
    SAP_ABA | 750 | 22 | 02.08.2021 | 55 | 08.10.2022 | 40
    """

    result = build_expiration_records(text, provider)

    assert [(item.source_section, item.name, item.expiration_date, item.milestone) for item in result] == [
        ("4.7.1 HANA Database Support Package Stack for HEP", "SAP HANA Database", "2023-12-31", ""),
    ]


class RatingLegendProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        return [
            {
                "nombre": "Mainstream / Extended maintenance offered by SAP has expired or will expire in the next 6 months.",
                "fecha": "31.12.2027",
            }
        ]


def test_build_expiration_records_rejects_rating_legend_text_as_component_name():
    provider = RatingLegendProvider()
    text = """
    SAP Application Release - Maintenance Phases
    SAP Product Version
    End of Mainstream Maintenance
    Status
    EHP8 FOR SAP ERP 6.0
    31.12.2027

    Rating Legend
    Rating
    Description
    Mainstream / Extended maintenance offered by SAP has expired or will expire in the next 6 months.
    """

    result = build_expiration_records(text, provider)

    assert [(item.source_section, item.name, item.expiration_date, item.milestone) for item in result] == [
        ("SAP Application Release - Maintenance Phases", "EHP8 FOR SAP ERP 6.0", "2027-12-31", ""),
    ]


def test_build_expiration_records_keeps_vendor_support_dates_from_ewa_overview_tables():
    provider = GenericEWANameProvider()
    text = """
    Operating System(s) - Maintenance Phases
    SAP Kernel Release
    End of Standard Vendor Support*
    End of Extended Vendor Support*
    Comment
    SQL Server 2012
    11.07.2017
    12.07.2022
    Planned Date
    1177356
    * Maintenance phases and duration for the DB version are defined by the vendor.
    Standard vendor support for your database version has already ended / will end in the near future.
    09.01.2018
    10.10.2023
    1177282
    * Maintenance phases and duration for the operating system version are defined by the vendor.
    The following table lists all information about your SAP kernel(s) currently in use.
    Instance(s)
    Age in Months
    OS Family
    749
    500
    97
    Windows Server (x86_64)
    """

    class VendorSupportProvider(DocumentIntelligenceProvider):
        def extract_expirations(self, text: str) -> list[dict[str, str]]:
            return [
                {
                    "nombre": "SQL Server 2012",
                    "fecha": "11.07.2017",
                    "hito": "End of Standard Vendor Support",
                },
                {
                    "nombre": "SQL Server 2012",
                    "fecha": "12.07.2022",
                    "hito": "End of Extended Vendor Support",
                },
                {
                    "nombre": "Operating System",
                    "fecha": "09.01.2018",
                    "hito": "End of Standard Vendor Support",
                },
                {
                    "nombre": "Operating System",
                    "fecha": "10.10.2023",
                    "hito": "End of Extended Vendor Support",
                },
            ]

    result = build_expiration_records(text, VendorSupportProvider())

    assert [(item.source_section, item.name, item.expiration_date, item.milestone) for item in result] == [
        ("Operating System(s) - Maintenance Phases", "SQL Server 2012", "2022-07-12", "End of Extended Vendor Support"),
        ("Operating System(s) - Maintenance Phases", "Operating System", "2023-10-10", "End of Extended Vendor Support"),
    ]


def test_build_expiration_records_prefers_word_table_row_component_for_os_vendor_dates():
    class OperatingSystemProvider(DocumentIntelligenceProvider):
        def extract_expirations(self, text: str) -> list[dict[str, str]]:
            assert "srv-pr-uap-h | Windows Server 2012 R2 | 09.01.2018 | 10.10.2023" in text
            return [
                {"nombre": "Operating System", "fecha": "09.01.2018", "hito": "End of Standard Vendor Support"},
                {"nombre": "Operating System", "fecha": "10.10.2023", "hito": "End of Extended Vendor Support"},
            ]

    text = """
    Operating System(s) - Maintenance Phases
    Host
    Operating System
    End of Standard Vendor Support*
    End of Extended Vendor Support*
    srv-pr-uap-h | Windows Server 2012 R2 | 09.01.2018 | 10.10.2023

    SAP Kernel Release
    The following table lists all information about your SAP kernel(s) currently in use.
    """

    result = build_expiration_records(text, OperatingSystemProvider())

    assert [(item.source_section, item.name, item.expiration_date, item.milestone) for item in result] == [
        ("Operating System(s) - Maintenance Phases", "Operating System", "2023-10-10", "End of Extended Vendor Support"),
    ]


def test_is_section_heading_rejects_recommendation_sentence_with_support_package_stack_phrase():
    line = (
        "You should only consider using a more recent SAP kernel patch than that shipped with the "
        "latest Support Package Stack for your product if specific errors occur."
    )

    assert _is_section_heading(line) is False


def test_build_expiration_records_does_not_use_recommendation_sentence_as_section():
    class VendorSupportProvider(DocumentIntelligenceProvider):
        def extract_expirations(self, text: str) -> list[dict[str, str]]:
            return [
                {"nombre": "SQL Server 2012", "fecha": "11.07.2017", "hito": "End of Standard Vendor Support"},
                {"nombre": "Windows Server 2012 R2", "fecha": "09.01.2018", "hito": "End of Standard Vendor Support"},
                {"nombre": "EHP7 FOR SAP ERP 6.0", "fecha": "31.12.2027"},
            ]

    text = """
    4.5 Database - Maintenance Phases
    Database Version
    End of Standard Vendor Support*
    SQL Server 2012
    11.07.2017

    4.6 Operating System(s) - Maintenance Phases
    Host
    Operating System
    End of Standard Vendor Support*
    srv-pr-uap-h | Windows Server 2012 R2 | 09.01.2018 | 10.10.2023

    4.6.2 Additional Remarks
    You should only consider using a more recent SAP kernel patch than that shipped with the latest Support Package Stack for your product if specific errors occur.

    4.1 SAP Application Release - Maintenance Phases
    EHP7 FOR SAP ERP 6.0
    31.12.2027
    """

    result = build_expiration_records(text, VendorSupportProvider())

    assert [(item.source_section, item.name) for item in result] == [
        ("4.5 Database - Maintenance Phases", "SQL Server 2012"),
        ("4.6 Operating System(s) - Maintenance Phases", "Windows Server 2012 R2"),
        ("4.1 SAP Application Release - Maintenance Phases", "EHP7 FOR SAP ERP 6.0"),
    ]
