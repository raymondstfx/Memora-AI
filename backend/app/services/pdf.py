import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.services.llm.provider import ChatError

TOKEN = re.compile(r"[\u3400-\u9fff]|[A-Za-z0-9_]{1,16}|[^\s]", re.UNICODE)


def lexical_text(text: str) -> str:
    return " ".join(TOKEN.findall(text.lower()))


@dataclass
class ChunkText:
    page_no: int
    chunk_index: int
    text: str
    token_count: int
    text_hash: str


def chunk_pages(
    pages: list[str], size: int, overlap: int, max_chunks: int
) -> list[ChunkText]:
    result: list[ChunkText] = []
    for page_no, raw in enumerate(pages, 1):
        text = " ".join(raw.replace("\x00", "").split())
        matches = list(TOKEN.finditer(text))
        if not matches:
            raise ChatError(
                "PDF_OCR_REQUIRED",
                f"Page {page_no} has no extractable text. "
                "OCR/blank-page review is required.",
                422,
            )
        for start in range(0, len(matches), size - overlap):
            stop = min(start + size, len(matches))
            content = text[matches[start].start() : matches[stop - 1].end()]
            result.append(
                ChunkText(
                    page_no,
                    len(result),
                    content,
                    stop - start,
                    hashlib.sha256(content.encode()).hexdigest(),
                )
            )
            if len(result) > max_chunks:
                raise ChatError(
                    "PDF_TOO_MANY_CHUNKS", "PDF exceeded the chunk limit.", 422
                )
            if stop == len(matches):
                break
    return result


def extract_pages(path: Path, settings: Settings) -> list[str]:
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.workers.parse_pdf",
                str(path),
                str(settings.pdf_max_pages),
                str(settings.pdf_max_text_chars),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=settings.pdf_parse_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise ChatError(
            "PDF_PARSE_TIMEOUT",
            "PDF parsing timed out; file was not marked ready.",
            422,
        ) from exc
    try:
        body = json.loads(result.stdout)
        if body.get("error_code"):
            raise ChatError(body["error_code"], body["message"], 422)
        pages = body["pages"]
        if result.returncode or not isinstance(pages, list) or not pages:
            raise ValueError("No pages")
        return [str(page) for page in pages]
    except (ValueError, KeyError) as exc:
        raise ChatError("PDF_CORRUPT", "PDF is corrupt or unsupported.", 422) from exc
