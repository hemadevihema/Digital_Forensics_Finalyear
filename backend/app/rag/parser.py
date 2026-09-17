import re
from pathlib import Path
from typing import Dict, List, Tuple
from pypdf import PdfReader
import docx

class DocumentParser:
    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx"}

    @classmethod
    def is_supported(cls, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def clean_text(cls, text: str) -> str:
        if not text:
            return ""
        # Remove null bytes, normalize weird spaces/line breaks
        text = text.replace("\x00", "")
        text = re.sub(r"\r\n|\r", "\n", text)
        # Collapse excessive consecutive spaces but preserve paragraphs
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def parse_file(cls, file_path: Path, original_filename: str) -> Tuple[List[Dict[str, any]], int]:
        """
        Parses a file and returns a list of page/section dicts:
        [{ "text": "...", "page": 1, "source": original_filename }]
        and total page count.
        """
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return cls._parse_pdf(file_path, original_filename)
        elif ext in {".txt", ".md", ".markdown"}:
            return cls._parse_text(file_path, original_filename)
        elif ext == ".docx":
            return cls._parse_docx(file_path, original_filename)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {', '.join(cls.SUPPORTED_EXTENSIONS)}")

    @classmethod
    def _parse_pdf(cls, file_path: Path, filename: str) -> Tuple[List[Dict[str, any]], int]:
        pages_data = []
        reader = PdfReader(str(file_path))
        total_pages = len(reader.pages)

        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            cleaned = cls.clean_text(page_text)
            if cleaned:
                pages_data.append({
                    "text": cleaned,
                    "page": page_idx + 1,
                    "source": filename
                })

        # If PDF had pages but no extractable text (e.g. empty or scans)
        if not pages_data and total_pages > 0:
            pages_data.append({
                "text": "[Empty or Non-Extractable PDF Content]",
                "page": 1,
                "source": filename
            })

        return pages_data, max(total_pages, 1)

    @classmethod
    def _parse_text(cls, file_path: Path, filename: str) -> Tuple[List[Dict[str, any]], int]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        cleaned = cls.clean_text(content)
        pages_data = [{
            "text": cleaned,
            "page": 1,
            "source": filename
        }]
        return pages_data, 1

    @classmethod
    def _parse_docx(cls, file_path: Path, filename: str) -> Tuple[List[Dict[str, any]], int]:
        doc = docx.Document(str(file_path))
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)

        cleaned = cls.clean_text("\n\n".join(full_text))
        pages_data = [{
            "text": cleaned,
            "page": 1,
            "source": filename
        }]
        return pages_data, 1
