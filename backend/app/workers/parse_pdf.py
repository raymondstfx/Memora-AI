"""Bounded native parser subprocess; emits only structured internal output."""

import importlib
import json
import os
import sys

import pymupdf


def main() -> None:
    if os.name != "nt":
        resource = importlib.import_module("resource")

        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024,) * 2)
    try:
        with pymupdf.open(sys.argv[1]) as document:  # type: ignore[no-untyped-call]
            if not document.is_pdf or document.is_repaired:
                raise ValueError("PDF_CORRUPT")
            if document.needs_pass:
                raise ValueError("PDF_ENCRYPTED")
            if not 0 < len(document) <= int(sys.argv[2]):
                raise ValueError("PDF_PAGE_LIMIT")
            pages = []
            total = 0
            for page in document:
                text = page.get_text("text", sort=True)
                total += len(text)
                if total > int(sys.argv[3]):
                    raise ValueError("PDF_TEXT_LIMIT")
                pages.append(text)
        print(json.dumps({"pages": pages}, ensure_ascii=False))
    except Exception as exc:
        code = (
            str(exc)
            if str(exc)
            in {"PDF_CORRUPT", "PDF_ENCRYPTED", "PDF_PAGE_LIMIT", "PDF_TEXT_LIMIT"}
            else "PDF_CORRUPT"
        )
        print(
            json.dumps(
                {
                    "error_code": code,
                    "message": "PDF parsing failed: "
                    + code
                    + ". Encrypted/corrupt files and limit violations are unsupported.",
                }
            )
        )


if __name__ == "__main__":
    main()
