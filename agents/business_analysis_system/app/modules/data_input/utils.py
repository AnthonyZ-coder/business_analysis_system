import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


ALLOWED_SUFFIXES = {".pdf"}


def build_saved_filename(original_name: str) -> str:
    """
    Build a unique saved filename while preserving the original suffix.
    """
    suffix = Path(original_name).suffix.lower()
    if not suffix:
        suffix = ".pdf"
    return f"{uuid4().hex}{suffix}"


def calculate_sha256(content: bytes) -> str:
    """
    Calculate SHA256 hash for uploaded file content.
    """
    return hashlib.sha256(content).hexdigest()


def validate_pdf_file(upload_file: UploadFile) -> None:
    """
    Validate current file is a PDF by filename suffix.
    Current MVP does not do deeper MIME verification.
    """
    filename = upload_file.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("only pdf files are supported in current version")


def ensure_parent_dir(path: Path) -> None:
    """
    Ensure parent directory exists.
    """
    path.parent.mkdir(parents=True, exist_ok=True)