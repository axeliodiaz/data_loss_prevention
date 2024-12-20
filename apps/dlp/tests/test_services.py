import pytest
from apps.dlp.models import DetectedMessage, Pattern
from apps.dlp.services import scan_message, create_detected_messages, scan_file


@pytest.fixture
def create_patterns(db):
    """
    Fixture to create test patterns in the database.
    """
    Pattern.objects.create(name="Credit Card", regex=r"\b\d{4}-\d{4}-\d{4}-\d{4}\b")
    Pattern.objects.create(
        name="Email", regex=r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"
    )
    Pattern.objects.create(
        name="Phone",
        regex=r"\b\+?[1-9]\d{0,2}[-.\s]?\(?\d{2,3}\)?[-.\s]\d{3}[-.\s]\d{4}\b",
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "message,expected_matches",
    [
        # Case 1: A message with one match
        (
            "This is a message containing a credit card number 1234-5678-9012-3456",
            ["Credit Card"],
        ),
        # Case 2: A clean message with no matches
        (
            "This is a clean message",
            [],
        ),
        # Case 3: A message with multiple matches
        (
            "The email is example@email.com and the credit card number is 1234-5678-9012-3456",
            ["Credit Card", "Email"],
        ),
        # Case 4: Patterns that do not match
        (
            "Message without numbers or emails",
            [],
        ),
    ],
)
def test_scan_message(create_patterns, message, expected_matches):
    """
    Test scan_message with database patterns and expected matches.
    """
    # Call the function
    matches = scan_message(message)

    # Compare the names of the matched patterns
    matched_names = [pattern.name for pattern in matches]
    assert sorted(matched_names) == sorted(expected_matches)


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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "file_content,expected",
    [
        # Case 1: File with sensitive patterns
        (
            b"This is a test with credit card 1234-5678-9012-3456.",
            ["Credit Card"],
        ),
        # Case 2: File without sensitive patterns
        (
            b"This is a clean file with no sensitive data.",
            [],
        ),
        # Case 3: Corrupt file content
        (
            b"\x89\x50\x4E\x47",  # Binary data (e.g., PNG file header)
            [],
        ),
    ],
)
def test_scan_file(create_patterns, file_content, expected):
    matches = scan_file(file_content)
    matched_names = [pattern.name for pattern in matches]
    assert matched_names == expected
