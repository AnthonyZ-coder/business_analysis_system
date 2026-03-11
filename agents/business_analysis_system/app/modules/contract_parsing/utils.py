import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_json_text(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}

    try:
        data = json.loads(value)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def dump_json_text(value: Dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False)


def merge_dict(base: Optional[Dict[str, Any]], patch: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = dict(base or {})

    if not patch:
        return result

    for key, val in patch.items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dict(result.get(key), val)
        else:
            result[key] = val

    return result


def safe_text_preview(text: str, max_chars: int = 2000) -> str:
    if not text:
        return ""

    cleaned = text.replace("\x00", " ").strip()
    if len(cleaned) <= max_chars:
        return cleaned

    return cleaned[:max_chars]


def validate_file_path(file_path: str) -> Path:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"file does not exist: {file_path}")

    if not path.is_file():
        raise FileNotFoundError(f"path is not a file: {file_path}")

    return path


def extract_text_from_pdf(file_path: str, max_pages=None):

    from pypdf import PdfReader
    reader = PdfReader(file_path)

    text_all = []
    warnings = []

    for i, page in enumerate(reader.pages):

        if max_pages and i >= max_pages:
            break

        text = page.extract_text()

        if text and text.strip():
            text_all.append(text)
            continue

        warnings.append(f"page {i+1} extracted empty text, fallback OCR")

        # OCR fallback
        from pdf2image import convert_from_path
        import pytesseract

        images = convert_from_path(file_path, first_page=i+1, last_page=i+1)

        ocr_text = pytesseract.image_to_string(images[0], lang="chi_sim")

        text_all.append(ocr_text)

    extracted_text = "\n".join(text_all)

    return extracted_text, len(text_all), warnings