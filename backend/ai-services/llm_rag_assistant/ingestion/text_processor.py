"""
ingestion/text_processor.py
Text cleaning, normalization, and language detection utilities.
"""
from __future__ import annotations

import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Normalize whitespace, fix unicode encoding anomalies, and trim text.
    Preserves Arabic and English characters, punctuation, and structural linebreaks.
    """
    if not text:
        return ""

    # Normalize unicode (NFKC)
    text = unicodedata.normalize("NFKC", text)

    # Replace carriage returns and excessive tabs
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace multiple consecutive spaces with a single space (preserving newlines)
    text = re.sub(r"[ \t]+", " ", text)

    # Replace 3 or more consecutive newlines with 2 newlines (paragraph boundary)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def detect_language(text: str) -> str:
    """
    Heuristic language detection: checks ratio of Arabic unicode range characters.
    Returns 'ar' for Arabic, 'en' for English/Latin.
    """
    if not text:
        return "en"

    # Arabic unicode block: 0600 - 06FF
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    total_letters = sum(1 for c in text if c.isalpha())

    if total_letters == 0:
        return "en"

    ratio = arabic_chars / total_letters
    return "ar" if ratio > 0.25 else "en"
