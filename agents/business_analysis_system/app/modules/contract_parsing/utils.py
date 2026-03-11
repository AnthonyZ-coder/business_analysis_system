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


def extract_text_from_pdf(file_path: str, max_pages: Optional[int] = None) -> Tuple[str, int, List[str]]:
    """
    Return:
    - extracted_text
    - processed_page_count
    - warnings
    """
    from pypdf import PdfReader  # lazy import

    path = validate_file_path(file_path)
    reader = PdfReader(str(path))

    warnings: List[str] = []
    texts: List[str] = []

    total_pages = len(reader.pages)
    pages_to_process = total_pages if max_pages is None else min(total_pages, max_pages)

    for idx in range(pages_to_process):
        try:
            page = reader.pages[idx]
            text = page.extract_text() or ""

            if not text.strip():
                warnings.append(f"page {idx + 1} extracted empty text")

            texts.append(text)
        except Exception as exc:
            warnings.append(f"page {idx + 1} extract failed: {str(exc)}")
            texts.append("")

    extracted_text = "\n".join(texts).strip()
    return extracted_text, pages_to_process, warnings