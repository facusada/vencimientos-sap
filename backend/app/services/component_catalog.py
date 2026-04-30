from dataclasses import dataclass
import re


DEFAULT_COMPONENT_COLUMNS = [
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
OTHER_COMPONENTS_COLUMN = "Otros componentes"


@dataclass(slots=True)
class ComponentCatalogMatch:
    canonical_name: str
    is_cataloged: bool


def normalize_component_name(name: str) -> ComponentCatalogMatch:
    cleaned = _clean_component_name(name)
    lowered = cleaned.lower()

    if not cleaned:
        return ComponentCatalogMatch(canonical_name="", is_cataloged=False)

    if _contains_any(lowered, ("sap product version", "main product version")):
        return ComponentCatalogMatch("SAP Product Version", True)

    if "netweaver" in lowered:
        return ComponentCatalogMatch("SAP NetWeaver", True)

    if _contains_any(lowered, ("sap solution manager", "solution manager", "solman")):
        return ComponentCatalogMatch("SAP Solution Manager", True)

    if _contains_any(lowered, ("fiori", "sap_ui", "sap ui")):
        return ComponentCatalogMatch("SAP Fiori", True)

    if "kernel" in lowered:
        return ComponentCatalogMatch("SAP Kernel", True)

    if "support package stack" in lowered:
        return ComponentCatalogMatch("Support Package Stack", True)

    if _contains_any(lowered, ("database", "hana db", "sap hana", "hana database")):
        return ComponentCatalogMatch("Database", True)

    if _contains_any(lowered, ("operating system", "os vendor support", "os family")):
        return ComponentCatalogMatch("Operating System", True)

    if "certificate" in lowered:
        return ComponentCatalogMatch("Certificates", True)

    return ComponentCatalogMatch(canonical_name=cleaned, is_cataloged=False)


def _clean_component_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip(" .:-")


def _contains_any(value: str, needles: tuple[str, ...]) -> bool:
    return any(needle in value for needle in needles)
