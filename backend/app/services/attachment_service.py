import io
import logging

logger = logging.getLogger(__name__)

UNAVAILABLE = "Attachment text extraction unavailable"
MAX_TEXT = 20000


def extract_attachment_text(filename: str, mime_type: str, data: bytes) -> str:
    if not data:
        return ""
    name = (filename or "").lower()
    mime = (mime_type or "").lower()
    try:
        if mime.startswith("text/") or name.endswith((".txt", ".csv", ".md")):
            return data.decode("utf-8", errors="replace")[:MAX_TEXT].strip()
        if mime == "application/pdf" or name.endswith(".pdf"):
            return _extract_pdf(data)
        if mime.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff")):
            return _extract_image(data)
    except Exception:
        logger.exception("attachment_extract_failed file=%s", filename)
        return UNAVAILABLE
    return ""


def _extract_pdf(data: bytes) -> str:
    try:
        import fitz
    except Exception:
        logger.info("pdf_extractor_unavailable")
        return UNAVAILABLE
    try:
        document = fitz.open(stream=data, filetype="pdf")
        pages = [page.get_text("text") for page in document]
        document.close()
        text = "\n".join(pages).strip()
        return text[:MAX_TEXT] if text else ""
    except Exception:
        logger.exception("pdf_extract_failed")
        return UNAVAILABLE


def _extract_image(data: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        logger.info("ocr_dependencies_unavailable")
        return UNAVAILABLE
    try:
        image = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(image).strip()
        return text[:MAX_TEXT] if text else UNAVAILABLE
    except Exception:
        logger.info("ocr_unavailable")
        return UNAVAILABLE
