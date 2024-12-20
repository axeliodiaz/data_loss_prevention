from unittest.mock import Mock

import pytest
from slack_sdk.errors import SlackApiError

from apps.dlp.models import DetectedMessage
from apps.dlp.services import (
    create_detected_messages,
    get_file_info,
)
from apps.dlp.services import process_file, scan_message
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


class TestProcessFile:
    @pytest.mark.parametrize(
        "file_id, file_info_response, file_content, expected_matches",
        [
            (
                "file123",
                {
                    "ok": True,
                    "file": {
                        "url_private_download": "https://slack.com/files/private-file"
                    },
                },
                "This is test content from Slack.",
                ["test"],  # Simulated matches from scan_message
            ),
        ],
    )
    def test_process_file_success(
        self,
        mocker,
        file_id,
        file_info_response,
        file_content,
        expected_matches,
    ):
        """
        Test that process_file successfully retrieves and scans a file.
        """
        # Mock get_file_info to return file content
        mocker.patch("apps.dlp.services.get_file_info", return_value=file_content)

        # Mock scan_message to return expected matches
        mocker.patch("apps.dlp.services.scan_message", return_value=expected_matches)

        # Call the function
        matches = process_file(file_id)

        # Assertions
        assert matches == expected_matches

    @pytest.mark.parametrize(
        "file_id, file_info_response",
        [
            (
                "file123",
                {"ok": False, "error": "file_not_found"},
            ),
        ],
    )
    def test_process_file_no_file(
        self,
        mocker,
        file_id,
        file_info_response,
    ):
        """
        Test that process_file handles an error when file info is unavailable.
        """
        # Mock get_file_info to return None
        mocker.patch("apps.dlp.services.get_file_info", return_value=None)

        # Call the function
        matches = process_file(file_id)

        # Assertions
        assert matches == []

    @pytest.mark.parametrize(
        "file_id, file_content",
        [
            ("file123", ""),
        ],
    )
    def test_process_file_empty_file(
        self,
        mocker,
        file_id,
        file_content,
    ):
        """
        Test that process_file handles an empty file correctly.
        """
        # Mock get_file_info to return empty content
        mocker.patch("apps.dlp.services.get_file_info", return_value=file_content)

        # Mock scan_message to return an empty list
        mocker.patch("apps.dlp.services.scan_message", return_value=[])

        # Call the function
        matches = process_file(file_id)

        # Assertions
        assert matches == []

    @pytest.mark.parametrize(
        "file_id, slack_error",
        [
            ("file123", SlackApiError("An error occurred", Mock(status_code=404))),
        ],
    )
    def test_process_file_slack_error(
        self,
        mocker,
        file_id,
        slack_error,
    ):
        """
        Test that process_file handles a Slack API error correctly.
        """
        # Mock get_file_info to raise SlackApiError
        mocker.patch("slack_sdk.web.client.WebClient", side_effect=slack_error)

        # Call the function
        matches = process_file(file_id)

        # Assertions
        assert matches == []


class TestGetFileInfo:
    @pytest.mark.parametrize(
        "file_id, slack_response, file_content",
        [
            (
                "file123",
                {
                    "ok": True,
                    "file": {
                        "url_private_download": "https://slack.com/files/private-file"
                    },
                },
                "This is test content from Slack.",
            ),
        ],
    )
    def test_get_file_info_success(self, mocker, file_id, slack_response, file_content):
        """
        Test that get_file_info retrieves file content successfully.
        """
        # Mock the Slack client response
        mock_client = mocker.patch(
            "apps.dlp.services.client.files_info", return_value=slack_response
        )

        # Mock the requests.get call to fetch file content
        mock_requests = mocker.patch("requests.get")
        mock_requests.return_value = Mock(status_code=200, text=file_content)

        # Call the function
        result = get_file_info(file_id)

        # Assertions
        assert result == file_content
        mock_client.assert_called_once_with(file=file_id)
        mock_requests.assert_called_once_with(
            slack_response["file"]["url_private_download"],
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        )

    @pytest.mark.parametrize(
        "file_id, slack_error",
        [
            (
                "file123",
                SlackApiError(
                    "An error occurred",
                    {"error": "file_not_found"},  # Usar un diccionario real
                ),
            ),
        ],
    )
    def test_get_file_info_slack_error(self, mocker, file_id, slack_error):
        """
        Test that get_file_info handles Slack API errors correctly.
        """
        # Mock the Slack client to raise SlackApiError
        mocker.patch("apps.dlp.services.client.files_info", side_effect=slack_error)

        # Call the function
        result = get_file_info(file_id)

        # Assertions
        assert result is None

    @pytest.mark.parametrize(
        "file_id, slack_response",
        [
            (
                "file123",
                {"ok": False, "error": "file_not_found"},
            ),
        ],
    )
    def test_get_file_info_slack_not_ok(self, mocker, file_id, slack_response):
        """
        Test that get_file_info handles Slack responses with 'ok': False.
        """
        # Mock the Slack client response
        mocker.patch("apps.dlp.services.client.files_info", return_value=slack_response)

        # Call the function
        result = get_file_info(file_id)

        # Assertions
        assert result is None

    @pytest.mark.parametrize(
        "file_id, slack_response",
        [
            (
                "file123",
                {
                    "ok": True,
                    "file": {
                        "url_private_download": "https://slack.com/files/private-file"
                    },
                },
            ),
        ],
    )
    def test_get_file_info_failed_file_download(self, mocker, file_id, slack_response):
        """
        Test that get_file_info handles file download errors.
        """
        # Mock the Slack client response
        mocker.patch("apps.dlp.services.client.files_info", return_value=slack_response)

        # Mock the requests.get call to simulate a failed file download
        mock_requests = mocker.patch("requests.get")
        mock_requests.return_value = Mock(status_code=404, text="")

        # Call the function
        result = get_file_info(file_id)

        # Assertions
        assert result is None
        mock_requests.assert_called_once_with(
            slack_response["file"]["url_private_download"],
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        )
