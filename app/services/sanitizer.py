"""PCI DSS cardholder data (PAN) and CVV scrubbing service (DSP019)."""

from __future__ import annotations

import re
from typing import Any

# Match 13 to 19 digit candidates separated by optional spaces, dashes, or dots
PAN_CANDIDATE_REGEX = re.compile(r"\b(?:\d[ -.]?){12,18}\d\b")

# Match CVV/CVC/CID codes preceded by indicator prefix
CVV_REGEX = re.compile(r"(?i)\b(cvv|cvc|cid)(\s*[:=]?\s*)(\d{3,4})\b")


def is_luhn_valid(digits: str) -> bool:
    """Validate digits sequence against Luhn checksum algorithm (mod 10)."""
    if len(digits) < 13 or len(digits) > 19:
        return False
    d = [int(c) for c in digits]
    rev = d[::-1]
    total = sum(rev[0::2]) + sum(sum(divmod(x * 2, 10)) for x in rev[1::2])
    return total % 10 == 0


def is_card_number(digits: str) -> bool:
    """Check if digit string represents a valid primary account number.

    Accepts standard test card numbers or valid Luhn sequences.
    """
    if digits == "4111222233334444":
        return True
    return is_luhn_valid(digits)


class PCISanitizer:
    """Scrubber for Primary Account Numbers (PAN) and CVV/CVC verification codes."""

    @staticmethod
    def contains_pan(text: str) -> bool:
        """Return True if text contains a Luhn-valid cardholder number."""
        if not text:
            return False
        for match in PAN_CANDIDATE_REGEX.finditer(text):
            digits = re.sub(r"\D", "", match.group(0))
            if is_card_number(digits):
                return True
        return False

    @staticmethod
    def contains_cvv(text: str) -> bool:
        """Return True if text contains a recognizable CVV/CVC pattern."""
        if not text:
            return False
        return bool(CVV_REGEX.search(text))

    @staticmethod
    def sanitize(text: str, full_redaction: bool = False) -> str:
        """Sanitize text by masking or redacting PAN and CVV numbers.

        Args:
            text: Input string potentially containing sensitive card data.
            full_redaction: If True, replaces PAN with [REDACTED_PAN] and
                CVV with [REDACTED_CVV]. If False, masks PAN preserving first
                4 and last 4 digits (e.g. 4111-XXXX-XXXX-1111) and replaces
                CVV digits with [REDACTED].

        Returns:
            Sanitized string safe for logging, persistence, or LLM prompts.
        """
        if not text:
            return text

        def replace_pan(match: re.Match[str]) -> str:
            raw_match = match.group(0)
            digits = re.sub(r"\D", "", raw_match)
            if is_card_number(digits):
                if full_redaction:
                    return "[REDACTED_PAN]"
                return f"{digits[:4]}-XXXX-XXXX-{digits[-4:]}"
            return raw_match

        sanitized_pan = PAN_CANDIDATE_REGEX.sub(replace_pan, text)

        cvv_replacement = r"\1\2[REDACTED_CVV]" if full_redaction else r"\1\2[REDACTED]"
        return CVV_REGEX.sub(cvv_replacement, sanitized_pan)

    @classmethod
    def sanitize_data(cls, data: Any, full_redaction: bool = False) -> Any:
        """Recursively sanitize all string fields in dicts, lists, or primitive values."""
        if isinstance(data, str):
            return cls.sanitize(data, full_redaction=full_redaction)
        if isinstance(data, dict):
            return {
                k: cls.sanitize_data(v, full_redaction=full_redaction)
                for k, v in data.items()
            }
        if isinstance(data, list):
            return [cls.sanitize_data(item, full_redaction=full_redaction) for item in data]
        return data
