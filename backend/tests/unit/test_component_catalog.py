from app.services.component_catalog import DEFAULT_COMPONENT_COLUMNS
from app.services.component_catalog import OTHER_COMPONENTS_COLUMN
from app.services.component_catalog import normalize_component_name


def test_normalize_component_name_maps_known_ewa_variants_to_canonical_names():
    assert normalize_component_name("SAP Kernel Release").canonical_name == "SAP Kernel"
    assert normalize_component_name("Kernel").canonical_name == "SAP Kernel"
    assert normalize_component_name("SAP NETWEAVER 7.4").canonical_name == "SAP NetWeaver"
    assert normalize_component_name("SAP Fiori Front-End Server").canonical_name == "SAP Fiori"
    assert normalize_component_name("SAP Solution Manager 7.2").canonical_name == "SAP Solution Manager"
    assert normalize_component_name("HANA Database Support Package Stack").canonical_name == "Support Package Stack"
    assert normalize_component_name("Operating System Version").canonical_name == "Operating System"


def test_normalize_component_name_prefers_support_package_stack_over_database():
    result = normalize_component_name("HANA Database Support Package Stack")

    assert result.canonical_name == "Support Package Stack"
    assert result.is_cataloged is True


def test_normalize_component_name_marks_unknown_components_for_review():
    result = normalize_component_name("SAP Cloud Connector")

    assert result.canonical_name == "SAP Cloud Connector"
    assert result.is_cataloged is False


def test_default_component_columns_are_stable_for_client_view():
    assert DEFAULT_COMPONENT_COLUMNS == [
        "SAP Product Version",
        "SAP NetWeaver",
        "SAP Solution Manager",
        "SAP Fiori",
        "SAP Kernel",
        "Database",
        "Operating System",
        "Support Package Stack",
        "Certificates",
    ]
    assert OTHER_COMPONENTS_COLUMN == "Otros componentes"
