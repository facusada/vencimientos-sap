from app.services.document_intelligence import DocumentIntelligenceProvider
from app.services.ewa_analysis_service import build_expiration_records


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
        (item.source_section, item.name, item.expiration_date) for item in result
    ] == [
        ("", "SAP Product Version", "2027-02-28"),
        ("", "Kernel", "2026-12-31"),
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

    assert [(item.source_section, item.name, item.expiration_date) for item in result] == [
        ("", "SAP Product Version", "2027-12-31"),
    ]


class GenericEWANameProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        return [
            {"nombre": "Your main product version", "fecha": "31.12.2027"},
            {"nombre": "Your SAP NetWeaver version", "fecha": "31.12.2027"},
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

    assert [(item.source_section, item.name, item.expiration_date) for item in result] == [
        ("SAP Application Release - Maintenance Phases", "EHP7 FOR SAP ERP 6.0", "2027-12-31"),
        ("SAP Application Release - Maintenance Phases", "SAP NETWEAVER 7.4", "2027-12-31"),
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


def test_build_expiration_records_filters_analysis_dates_and_reclassifies_os_support_dates():
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

    assert [(item.source_section, item.name, item.expiration_date) for item in result] == [
        ("HANA Database Support Package Stack for HEP", "SAP HANA Database", "2023-12-31"),
        ("Operating System(s) - Maintenance Phases", "Red Hat Enterprise Linux 8 (x86_64)", "2029-05-31"),
        ("Operating System(s) - Maintenance Phases", "Red Hat Enterprise Linux 8 (x86_64)", "2031-05-31"),
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

    assert [(item.source_section, item.name, item.expiration_date) for item in result] == [
        ("SAP Application Release - Maintenance Phases", "EHP8 FOR SAP ERP 6.0", "2027-12-31"),
    ]
