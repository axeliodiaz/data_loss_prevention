import json
from unittest.mock import MagicMock, Mock

import pytest
from slack_sdk.errors import SlackApiError

from apps.dlp.constants import SLACK_BLOCKING_FILE
from apps.dlp.models import DetectedMessage
from apps.dlp.services import (
    create_detected_messages,
    get_file_info,
    delete_file_and_notify,
    replace_message,
    process_file,
    scan_message,
    send_to_sqs,
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
        result_content, result_matches = process_file(file_id)

        # Assertions
        assert result_content == file_content
        assert result_matches == expected_matches

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
        result_content, result_matches = process_file(file_id)

        # Assertions
        assert result_content is None
        assert result_matches == []

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
        result_content, result_matches = process_file(file_id)

        # Assertions
        assert result_content == file_content
        assert result_matches == []

    @pytest.mark.parametrize(
        "file_id, slack_error",
        [
            (
                "file123",
                SlackApiError(
                    "An error occurred",
                    {"error": "file_not_found"},
                ),
            ),
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
        mocker.patch("apps.dlp.services.client.files_info", side_effect=slack_error)

        # Call the function
        result_content, result_matches = process_file(file_id)

        # Assertions
        assert result_content is None
        assert result_matches == []


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


@pytest.mark.parametrize(
    "response, expected_response",
    [
        ({"ok": True}, {"ok": True}),
        (
            {"ok": False, "error": "message_not_found"},
            {"ok": False, "error": "message_not_found"},
        ),
    ],
)
def test_replace_message(mocker, response, expected_response):
    """
    Test replace_message functionality using mocker.
    """
    mock_chat_update = mocker.patch(
        "apps.dlp.services.client.chat_update", return_value=response
    )

    result = replace_message("C123456", "1626181234.000200", "Updated message")

    # Assertions
    mock_chat_update.assert_called_once_with(
        channel="C123456",
        ts="1626181234.000200",
        text="Updated message",
    )
    assert result == expected_response


@pytest.mark.parametrize(
    "delete_response, notify_response, expected_notify_call, expected_log_calls",
    [
        (
            {"ok": True},
            {"ok": True},
            True,
            [
                ("info", "File file123 deleted successfully."),
                ("info", "Notification message sent to channel C123456."),
            ],
        ),
        (
            {"ok": True},
            {"ok": False, "error": "notification_failed"},
            False,
            [
                ("info", "File file123 deleted successfully."),
                ("error", "Failed to send notification: notification_failed"),
            ],
        ),
        (
            {"ok": False, "error": "file_not_found"},
            None,
            False,
            [("error", "Failed to delete file: file_not_found")],
        ),
    ],
)
def test_delete_file_and_notify(
    mocker,
    delete_response,
    notify_response,
    expected_notify_call,
    expected_log_calls,
):
    """
    Test the delete_file_and_notify functionality.
    """
    # Mock Slack API calls
    mock_files_delete = mocker.patch(
        "apps.dlp.services.client.files_delete", return_value=delete_response
    )
    mock_chat_postMessage = mocker.patch(
        "apps.dlp.services.client.chat_postMessage", return_value=notify_response
    )
    mock_logger = mocker.patch("apps.dlp.services.logger")

    # Call the function
    delete_file_and_notify(file_id="file123", channel_id="C123456")

    # Assertions
    mock_files_delete.assert_called_once_with(file="file123")

    if delete_response["ok"]:
        if expected_notify_call:
            mock_chat_postMessage.assert_called_once_with(
                channel="C123456", text=SLACK_BLOCKING_FILE
            )
        else:
            mock_chat_postMessage.assert_called_once_with(
                channel="C123456", text=SLACK_BLOCKING_FILE
            )
    else:
        mock_chat_postMessage.assert_not_called()

    # Verify logger calls
    for log_method, log_message in expected_log_calls:
        getattr(mock_logger, log_method).assert_any_call(log_message)


class TestSendToSQS:

    @pytest.mark.django_db
    def test_send_to_sqs_success(self, mocker):
        """Test that send_to_sqs sends a message to SQS successfully."""
        mock_sqs_client = mocker.patch("apps.dlp.services.boto3.client")
        mock_send_message = MagicMock()
        mock_sqs_client.return_value.send_message = mock_send_message

        # Mock settings values
        mocker.patch(
            "django.conf.settings.AWS_SQS_QUEUE_URL", "https://example.com/queue"
        )
        mocker.patch(
            "django.conf.settings.AWS_SQS_ENDPOINT_URL", "http://localhost:9324"
        )
        mocker.patch("django.conf.settings.AWS_REGION_NAME", "us-east-1")
        mocker.patch("django.conf.settings.AWS_ACCESS_KEY_ID", "test-access-key")
        mocker.patch("django.conf.settings.AWS_SECRET_ACCESS_KEY", "test-secret-key")

        task_name = "process_message"
        args = ["test_message"]
        kwargs = {"extra_data": "value"}

        send_to_sqs(task_name, args, kwargs)

        # Assertions
        mock_sqs_client.assert_called_once_with(
            "sqs",
            endpoint_url="http://localhost:9324",
            region_name="us-east-1",
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
        )

        expected_message = {
            "task": task_name,
            "args": args,
            "kwargs": kwargs,
        }
        mock_send_message.assert_called_once_with(
            QueueUrl="https://example.com/queue",
            MessageBody=json.dumps(expected_message),
        )

    @pytest.mark.django_db
    def test_send_to_sqs_with_defaults(self, mocker):
        """Test that send_to_sqs works with default args and kwargs."""
        mock_sqs_client = mocker.patch("apps.dlp.services.boto3.client")
        mock_send_message = MagicMock()
        mock_sqs_client.return_value.send_message = mock_send_message

        # Mock settings values
        mocker.patch(
            "django.conf.settings.AWS_SQS_QUEUE_URL", "https://example.com/queue"
        )
        mocker.patch(
            "django.conf.settings.AWS_SQS_ENDPOINT_URL", "http://localhost:9324"
        )
        mocker.patch("django.conf.settings.AWS_REGION_NAME", "us-east-1")
        mocker.patch("django.conf.settings.AWS_ACCESS_KEY_ID", "test-access-key")
        mocker.patch("django.conf.settings.AWS_SECRET_ACCESS_KEY", "test-secret-key")

        task_name = "process_file"

        send_to_sqs(task_name)

        # Assertions
        mock_sqs_client.assert_called_once_with(
            "sqs",
            endpoint_url="http://localhost:9324",
            region_name="us-east-1",
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
        )

        expected_message = {
            "task": task_name,
            "args": [],
            "kwargs": {},
        }
        mock_send_message.assert_called_once_with(
            QueueUrl="https://example.com/queue",
            MessageBody=json.dumps(expected_message),
        )

    @pytest.mark.django_db
    def test_send_to_sqs_failure(self, mocker):
        """Test that send_to_sqs handles errors from SQS."""
        mock_sqs_client = mocker.patch("apps.dlp.services.boto3.client")
        mock_send_message = MagicMock(side_effect=Exception("SQS Error"))
        mock_sqs_client.return_value.send_message = mock_send_message

        # Mock settings values
        mocker.patch(
            "django.conf.settings.AWS_SQS_QUEUE_URL", "https://example.com/queue"
        )
        mocker.patch(
            "django.conf.settings.AWS_SQS_ENDPOINT_URL", "http://localhost:9324"
        )
        mocker.patch("django.conf.settings.AWS_REGION_NAME", "us-east-1")
        mocker.patch("django.conf.settings.AWS_ACCESS_KEY_ID", "test-access-key")
        mocker.patch("django.conf.settings.AWS_SECRET_ACCESS_KEY", "test-secret-key")

        task_name = "process_file"

        with pytest.raises(Exception, match="SQS Error"):
            send_to_sqs(task_name)

        # Assertions
        mock_sqs_client.assert_called_once_with(
            "sqs",
            endpoint_url="http://localhost:9324",
            region_name="us-east-1",
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
        )
        mock_send_message.assert_called_once()
