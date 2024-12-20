import pytest

from apps.dlp.models import DetectedMessage, Pattern
from apps.dlp.services import (
    scan_message,
    create_detected_messages,
    scan_file,
    process_file,
)
from data_loss_prevention.settings import SLACK_BOT_TOKEN


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
        # Case 3: Binary content (corrupt or unsupported format)
        (
            b"\x89PNG",  # Binary data resembling a PNG file header
            [],
        ),
    ],
)
def test_scan_file(create_patterns, file_content, expected):
    """
    Test the scan_file function for detecting sensitive patterns in file content.

    This test verifies the ability of scan_file to:
    1. Detect predefined patterns in textual file content.
    2. Handle clean files without any matches.
    3. Safely process binary or corrupt content without raising errors.

    Args:
        create_patterns (fixture): Creates test patterns in the database.
        file_content (bytes): The content of the file to be scanned.
        expected (list): The expected list of matched pattern names.

    Steps:
    - Calls scan_file with the given file content.
    - Extracts the names of matched patterns from the results.
    - Asserts that the matched pattern names match the expected list.
    """
    # Call scan_file and collect the results
    matches = scan_file(file_content)

    # Extract the names of the matched patterns
    matched_names = [pattern.name for pattern in matches]

    # Assert that the matched pattern names match the expected results
    assert matched_names == expected


class TestProcessFile:
    @pytest.mark.parametrize(
        "file_id, file_info_response, file_content",
        [
            (
                "file123",
                {
                    "ok": True,
                    "file": {"url_private": "https://slack.com/files/private-file"},
                },
                b"This is test content from Slack.",
            ),
        ],
    )
    def test_process_file_success(
        self,
        mocker,
        mock_requests_get,
        mock_scan_file,
        file_id,
        file_info_response,
        file_content,
    ):
        """
        Test that process_file successfully retrieves and scans a file.
        """
        # Mock the response for files.info
        mock_requests_get.side_effect = [
            mocker.Mock(json=lambda: file_info_response),
            mocker.Mock(content=file_content),
        ]

        # Call the function
        process_file(file_id)

        # Assertions
        mock_requests_get.assert_any_call(
            "https://slack.com/api/files.info",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            params={"file": file_id},
        )
        mock_requests_get.assert_any_call(
            file_info_response["file"]["url_private"],
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        )
        mock_scan_file.assert_called_once_with(file_content)

    @pytest.mark.parametrize(
        "file_id, file_info_response, file_content",
        [
            (
                "file123",
                {
                    "ok": True,
                    "file": {"url_private": "https://slack.com/files/private-file"},
                },
                b"",
            ),
        ],
    )
    def test_process_file_empty_file(
        self,
        mocker,
        mock_requests_get,
        mock_scan_file,
        file_id,
        file_info_response,
        file_content,
    ):
        """
        Test that process_file handles an empty file correctly.
        """
        # Mock the response for files.info
        mock_requests_get.side_effect = [
            mocker.Mock(json=lambda: file_info_response),  # First call to files.info
            mocker.Mock(content=file_content),  # Second call to download the file
        ]

        # Call the function
        process_file(file_id)

        # Assertions
        mock_requests_get.assert_any_call(
            "https://slack.com/api/files.info",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            params={"file": file_id},
        )
        mock_scan_file.assert_called_once_with(file_content)
