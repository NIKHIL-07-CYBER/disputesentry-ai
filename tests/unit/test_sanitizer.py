"""Unit tests for PCI DSS cardholder data and CVV scrubbing (DSP019)."""

from __future__ import annotations

from app.services.sanitizer import PCISanitizer


def test_t03_02_cardholder_scrubbing() -> None:
    """T03-02: PCI DSS cardholder scrubbing (DSP019).

    Input: "Buyer card: 4111 2222 3333 4444 CVV 123"
    Expected: "Buyer card: 4111-XXXX-XXXX-4444 CVV [REDACTED]"
    """
    input_text = "Buyer card: 4111 2222 3333 4444 CVV 123"
    sanitized = PCISanitizer.sanitize(input_text)
    assert sanitized == "Buyer card: 4111-XXXX-XXXX-4444 CVV [REDACTED]"


def test_positive_luhn_card_masking() -> None:
    """Verify Luhn-valid card numbers are masked preserving first 4 and last 4 digits."""
    # 4532015698741235 is a valid Visa test card from DSP019 fixture
    raw = "Customer said payment card 4532015698741235 was charged twice."
    sanitized = PCISanitizer.sanitize(raw)
    assert sanitized == "Customer said payment card 4532-XXXX-XXXX-1235 was charged twice."


def test_positive_cvv_and_cvc_masking() -> None:
    """Verify 3 and 4 digit CVVs preceded by CVV, CVC, or CID are masked."""
    cases = [
        ("Security code CVV 456", "Security code CVV [REDACTED]"),
        ("Card cvv: 789 on back", "Card cvv: [REDACTED] on back"),
        ("cvc=1234", "cvc=[REDACTED]"),
        ("CID: 987", "CID: [REDACTED]"),
    ]
    for raw, expected in cases:
        assert PCISanitizer.sanitize(raw) == expected


def test_positive_full_redaction_mode() -> None:
    """Verify full redaction mode uses [REDACTED_PAN] and [REDACTED_CVV] per DSP019."""
    raw = "Please refund my card 4532015698741235 (exp 08/28, CVV 321) immediately!"
    expected = "Please refund my card [REDACTED_PAN] (exp 08/28, CVV [REDACTED_CVV]) immediately!"
    assert PCISanitizer.sanitize(raw, full_redaction=True) == expected


def test_negative_non_luhn_digits_left_unmasked() -> None:
    """Verify non-Luhn digit sequences (e.g., 16 random non-card digits) are left unmasked."""
    # 1234567890123456 fails Luhn checksum
    non_card = "Tracking ID 1234567890123456 was updated."
    assert PCISanitizer.sanitize(non_card) == non_card
    assert not PCISanitizer.contains_pan(non_card)


def test_negative_order_and_tracking_numbers_not_masked() -> None:
    """Ensure standard tracking numbers and order IDs are not masked."""
    text = "Order ORD-1234 shipped with USPS tracking 9400100000000000000001."
    assert PCISanitizer.sanitize(text) == text
    assert not PCISanitizer.contains_pan(text)


def test_boundary_card_delimiter_variants() -> None:
    """Verify card numbers with dashes, dots, spaces, or no delimiters are detected and masked."""
    # 4111-1111-1111-1111 is Luhn valid
    variants = [
        "Card: 4111-1111-1111-1111",
        "Card: 4111.1111.1111.1111",
        "Card: 4111 1111 1111 1111",
        "Card: 4111111111111111",
    ]
    for variant in variants:
        sanitized = PCISanitizer.sanitize(variant)
        assert "4111-XXXX-XXXX-1111" in sanitized
        assert PCISanitizer.contains_pan(variant)


def test_boundary_empty_and_clean_text() -> None:
    """Verify empty strings and clean customer notes remain untouched."""
    assert PCISanitizer.sanitize("") == ""
    assert not PCISanitizer.contains_pan("")
    assert not PCISanitizer.contains_cvv("")
    clean_note = (
        "I placed order ORD-1234 on Oct 20 for two pairs of shoes, but only one pair arrived."
    )
    assert PCISanitizer.sanitize(clean_note) == clean_note
    assert not PCISanitizer.contains_pan(clean_note)
    assert not PCISanitizer.contains_cvv(clean_note)


def test_cvv_detection_and_nested_list_sanitization() -> None:
    """Test CVV pattern detection helper and list structure sanitization."""
    assert PCISanitizer.contains_cvv("CVV 123") is True
    assert PCISanitizer.contains_cvv("No code here") is False

    nested_list = ["Clean string", "Card 4532015698741235 CVV 123", 42, None]
    sanitized = PCISanitizer.sanitize_data(nested_list)
    assert sanitized[0] == "Clean string"
    assert "4532-XXXX-XXXX-1235" in sanitized[1]
    assert "[REDACTED]" in sanitized[1]
    assert sanitized[2] == 42
    assert sanitized[3] is None

