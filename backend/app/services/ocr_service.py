from __future__ import annotations

import os
from io import BytesIO


class TesseractOCRService:
    def extract_text_from_images(self, images: list[bytes]) -> str:
        if not images:
            return ""

        pytesseract = _load_pytesseract()
        _configure_tesseract_binary(pytesseract)
        segments: list[str] = []

        for image in images:
            text = pytesseract.image_to_string(_load_pil_image(image), lang="eng").strip()
            if text:
                segments.append(text)

        return "\n".join(segments).strip()


def _load_pytesseract():
    try:
        import pytesseract
    except ImportError as exc:
        raise ValueError("OCR dependency is not installed") from exc

    return pytesseract


def _load_pil_image(payload: bytes):
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("OCR image dependencies are not installed") from exc

    return Image.open(BytesIO(payload)).convert("RGB")


def _configure_tesseract_binary(pytesseract) -> None:
    configured_binary = os.getenv("TESSERACT_CMD", "").strip()
    if configured_binary:
        pytesseract.pytesseract.tesseract_cmd = configured_binary


def create_ocr_service() -> TesseractOCRService:
    return TesseractOCRService()


def render_pdf_pages_to_images(payload: bytes) -> list[bytes]:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise ValueError("PDF rendering dependency is not installed") from exc

    pdf = pdfium.PdfDocument(BytesIO(payload))
    images: list[bytes] = []

    for page_index in range(len(pdf)):
        page = pdf[page_index]
        bitmap = page.render(scale=2.0)
        pil_image = bitmap.to_pil()
        buffer = BytesIO()
        pil_image.save(buffer, format="PNG")
        images.append(buffer.getvalue())
        pil_image.close()
        bitmap.close()
        page.close()

    pdf.close()
    return images
