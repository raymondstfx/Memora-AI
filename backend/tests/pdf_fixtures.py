import hashlib
import math
import re

import pymupdf


def pdf_bytes(pages=None, encrypted=False):
    pages = (
        pages
        if pages is not None
        else [
            "MEMORA PROJECT BRIEF\nAPI owner: Alex. Testing owner: Bailey.\n"
            "The API deadline is November 5, 2026.\n"
            "The project uses FastAPI and PostgreSQL.\n",
            "ACCEPTANCE MILESTONES\nThe customer demo is November 9, 2026.\n"
            "Bailey verifies API integration and test data before the demonstration.\n",
        ]
    )
    with pymupdf.open() as document:
        for text in pages:
            page = document.new_page()
            page.insert_text((72, 72), text, fontsize=12)
        kwargs = (
            {
                "encryption": pymupdf.PDF_ENCRYPT_AES_256,
                "owner_pw": "fixture-owner",
                "user_pw": "fixture-user",
            }
            if encrypted
            else {}
        )
        return document.tobytes(garbage=4, deflate=True, **kwargs)


def vector(text, dimensions):
    result = [0.0] * dimensions
    if "deadline" in text.lower():
        result[0] += 8
    for token in re.findall(r"\w+", text.lower()):
        result[
            int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % dimensions
        ] += 1
    norm = math.sqrt(sum(x * x for x in result)) or 1
    return [x / norm for x in result]
