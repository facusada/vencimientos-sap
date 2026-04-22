import pytest

from app.parsers.text_extractor import extract_text


def test_extract_text_supports_pdf_files(monkeypatch: pytest.MonkeyPatch):
    class FakePage:
        def extract_text(self, layout: bool = False) -> str:
            return "4.6 Operating System(s) - Maintenance Phases\nSUSE Linux Enterprise"

        def extract_tables(self) -> list[list[list[str]]]:
            return [
                [
                    ["Host", "Operating System", "End of Standard Vendor Support"],
                    ["2 Hosts", "SUSE Linux Enterprise Server 15 (x86_64)", "31.07.2028"],
                ]
            ]

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("pdfplumber.open", lambda stream: FakePdf())

    result = extract_text("ewa.pdf", b"fake-pdf")

    assert "4.6 Operating System(s) - Maintenance Phases" in result
    assert "Host | Operating System | End of Standard Vendor Support" in result
    assert "2 Hosts | SUSE Linux Enterprise Server 15 (x86_64) | 31.07.2028" in result


def test_extract_text_rejects_non_pdf_files():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text("ewa.docx", b"irrelevant")

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text("ewa.doc", b"irrelevant")


def test_extract_text_requires_extractable_pdf_text(monkeypatch: pytest.MonkeyPatch):
    class FakePage:
        def extract_text(self, layout: bool = False) -> str:
            return ""

        def extract_tables(self) -> list[list[list[str]]]:
            return []

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("pdfplumber.open", lambda stream: FakePdf())

    with pytest.raises(ValueError, match="PDF does not contain extractable text"):
        extract_text("ewa.pdf", b"fake-pdf")
