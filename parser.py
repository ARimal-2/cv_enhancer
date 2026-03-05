"""
parser.py
---------
Handles PDF resume text extraction using pdfplumber.
"""
import pdfplumber


def extract_text(file) -> str:
    """
    Extract and return all text from a PDF file.

    Args:
        file: A file-like object (e.g. from Streamlit's file uploader).

    Returns:
        A single string containing the combined text of all pages,
        or an error message string if extraction fails.
    """
    extracted = []

    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted.append(page_text)
    except Exception as exc:
        return f"[Error] Could not extract text from PDF: {exc}"

    combined = "\n".join(extracted).strip()
    return combined if combined else "[Warning] No text found in the uploaded PDF."
