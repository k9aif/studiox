# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# k9_aif_abb/k9_utils/ocr.py

import os
import logging

try:
    from docling import DocumentConverter  # if Docling is available
except ImportError:
    DocumentConverter = None

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None

logger = logging.getLogger("OCRUtils")

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from a document or image using available OCR backends.
    Supported formats: PDF, JPG, PNG, TIFF.
    Automatically selects the best available backend.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return ""

    ext = os.path.splitext(file_path)[1].lower()
    logger.info(f"Extracting text from {file_path} (type={ext})")

    text = ""
    try:
        # 1. Use Docling if available (best for PDFs)
        if DocumentConverter and ext == ".pdf":
            converter = DocumentConverter()
            result = converter.convert(file_path)
            text = result.document.export_to_markdown()
            logger.info("OCR via Docling successful.")

        # 2. Fall back to Tesseract (best for images)
        elif pytesseract and ext in [".jpg", ".jpeg", ".png", ".tiff"]:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            logger.info("OCR via Tesseract successful.")

        # 3. Placeholder: Hyperscience API or other ABB integration
        else:
            logger.warning("No supported OCR backend found - returning empty string.")
            text = ""

    except Exception as e:
        logger.exception(f"OCR extraction failed: {e}")
        text = ""

    return text.strip()