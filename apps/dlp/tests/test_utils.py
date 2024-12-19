import pytest
from apps.dlp.utils import scan_message
from collections import namedtuple

# Simulate the Pattern model using a namedtuple
Pattern = namedtuple("Pattern", ["regex"])


@pytest.mark.parametrize(
    "message,patterns,expected_matches",
    [
        # Case 1: A message with one match
        (
            "This is a message containing a credit card number 1234-5678-9012-3456",
            [Pattern(r"\d{4}-\d{4}-\d{4}-\d{4}")],
            [Pattern(r"\d{4}-\d{4}-\d{4}-\d{4}")],
        ),
        # Case 2: A clean message with no matches
        ("This is a clean message", [Pattern(r"\d{4}-\d{4}-\d{4}-\d{4}")], []),
        # Case 3: A message with multiple matches
        (
            "The email is example@email.com and the credit card number is 1234-5678-9012-3456",
            [
                Pattern(r"\d{4}-\d{4}-\d{4}-\d{4}"),
                Pattern(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
            ],
            [
                Pattern(r"\d{4}-\d{4}-\d{4}-\d{4}"),
                Pattern(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
            ],
        ),
        # Case 4: Patterns that do not match
        (
            "Message without numbers or emails",
            [Pattern(r"\d+"), Pattern(r"[A-Z]{6}")],  # Adjusted pattern
            [],
        ),
    ],
)
def test_scan_message(message, patterns, expected_matches):
    matches = scan_message(message, patterns)
    assert matches == expected_matches
