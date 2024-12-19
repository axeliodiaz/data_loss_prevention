import pytest
from collections import namedtuple
from apps.dlp.models import DetectedMessage, Pattern
from apps.dlp.services import scan_message, create_detected_messages


Pattern = namedtuple("Pattern", ["regex"])


@pytest.mark.django_db
@pytest.mark.parametrize(
    "message,mocked_patterns,expected_matches",
    [
        # Case 1: A message with one match
        (
            "This is a message containing a credit card number 1234-5678-9012-3456",
            [Pattern(r"\d{4}-\d{4}-\d{4}-\d{4}")],
            [Pattern(r"\d{4}-\d{4}-\d{4}-\d{4}")],
        ),
        # Case 2: A clean message with no matches
        (
            "This is a clean message",
            [Pattern(r"\d{4}-\d{4}-\d{4}-\d{4}")],
            [],
        ),
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
def test_scan_message(mocker, message, mocked_patterns, expected_matches):
    # Mock Pattern.objects.all() using mocker
    mocker.patch("apps.dlp.services.Pattern.objects.all", return_value=mocked_patterns)

    # Call the function and assert matches
    matches = scan_message(message)
    assert matches == expected_matches


@pytest.mark.django_db
class TestCreateDetectedMessage:
    def test_create_detected_messages_success(self, pattern_credit_card, pattern_email):
        """Test creating multiple DetectedMessage objects with matched patterns."""
        message = "This is a test message with sensitive data."

        detected_messages = create_detected_messages(
            message, [pattern_credit_card, pattern_email]
        )

        assert len(detected_messages) == 2
        assert DetectedMessage.objects.count() == 2
        assert detected_messages[0].content == message
        assert detected_messages[0].pattern == pattern_credit_card
        assert detected_messages[1].pattern == pattern_email

    def test_create_detected_messages_empty_patterns(self):
        """Test creating no DetectedMessage objects when no patterns match."""
        message = "This is a clean message with no sensitive data."

        detected_messages = create_detected_messages(message, [])

        assert len(detected_messages) == 0
        assert DetectedMessage.objects.count() == 0
