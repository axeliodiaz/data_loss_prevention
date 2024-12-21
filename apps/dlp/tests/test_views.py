import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status

from apps.dlp.constants import (
    EVENT_CALLBACK,
    EVENT_TYPE_MESSAGE,
    SLACK_BLOCKING_MESSAGE,
)


@pytest.mark.django_db
class TestSlackEventView:
    @patch("apps.dlp.views.process_file")
    @patch("apps.dlp.views.create_detected_messages")
    @patch("apps.dlp.views.delete_file_and_notify")
    def test_post_event_callback_message_with_file(
        self,
        mock_delete_file_and_notify,
        mock_create_detected_messages,
        mock_process_file,
        client,
        slack_event_url,
        pattern_email,
    ):
        """Test Slack event callback with a file containing sensitive data."""
        file_content = "Sensitive content: 1234-5678-9012-3456"
        mock_process_file.return_value = (file_content, [pattern_email])
        mock_create_detected_messages.return_value = []  # Mock bulk creation
        mock_delete_file_and_notify.return_value = None

        data = {
            "type": EVENT_CALLBACK,
            "event": {
                "type": EVENT_TYPE_MESSAGE,
                "text": "Here is a file",
                "channel": "C123456",
                "ts": "1626181234.000200",
                "files": [{"id": "file123"}],
            },
        }
        response = client.post(slack_event_url, data, format="json")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "received"}
        mock_process_file.assert_called_once_with("file123")
        mock_create_detected_messages.assert_called_once_with(
            message=file_content, patterns=[pattern_email]
        )
        mock_delete_file_and_notify.assert_called_once_with(
            channel_id="C123456",
            file_id="file123",
        )

    @patch("apps.dlp.views.scan_message")
    @patch("apps.dlp.views.create_detected_messages")
    @patch("apps.dlp.views.replace_message")
    def test_post_event_callback_message_with_leak(
        self,
        mock_replace_message,
        mock_create_detected_messages,
        mock_scan_message,
        client,
        slack_event_url,
        pattern_email,
    ):
        """Test Slack event callback with a message containing sensitive data."""
        mock_scan_message.return_value = [pattern_email]
        mock_create_detected_messages.return_value = []  # Mock bulk creation
        mock_replace_message.return_value = {"ok": True}

        message = "Sensitive data: 1234-5678-9012-3456"
        data = {
            "type": EVENT_CALLBACK,
            "event": {
                "type": EVENT_TYPE_MESSAGE,
                "text": message,
                "channel": "C123456",
                "ts": "1626181234.000200",
            },
        }
        response = client.post(slack_event_url, data, format="json")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "received"}

        # Adjusted assertion to account for keyword arguments
        mock_scan_message.assert_called_once_with(message=message)
        mock_create_detected_messages.assert_called_once_with(
            message=message, patterns=[pattern_email]
        )
        mock_replace_message.assert_called_once_with(
            channel_id="C123456",
            ts="1626181234.000200",
            new_message=SLACK_BLOCKING_MESSAGE,
        )

    def test_post_event_callback_non_message(
        self, client, slack_event_url, mock_logger_debug
    ):
        """Test a valid Slack event callback with a non-message event."""
        event_type = "reaction_added"
        data = {
            "type": EVENT_CALLBACK,
            "event": {"type": event_type, "reaction": "thumbsup"},
        }
        response = client.post(slack_event_url, data, format="json")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "received"}
        mock_logger_debug.assert_called_once_with(f"Unhandled event type: {event_type}")

    @patch("apps.dlp.views.process_file")
    def test_post_event_callback_message_with_clean_file(
        self, mock_process_file, client, slack_event_url
    ):
        """Test Slack event callback with a clean file."""
        mock_process_file.return_value = ("Clean file content.", [])
        data = {
            "type": EVENT_CALLBACK,
            "event": {
                "type": EVENT_TYPE_MESSAGE,
                "text": "Here is a clean file",
                "channel": "C123456",
                "ts": "1626181234.000200",
                "files": [{"id": "file123"}],
            },
        }
        response = client.post(slack_event_url, data, format="json")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "received"}
        mock_process_file.assert_called_once_with("file123")

    @patch("apps.dlp.views.process_file")
    @patch("apps.dlp.views.create_detected_messages")
    @patch("apps.dlp.views.delete_file_and_notify")
    def test_post_event_callback_file_with_leak(
        self,
        mock_delete_file_and_notify,
        mock_create_detected_messages,
        mock_process_file,
        client,
        slack_event_url,
        pattern_email,
    ):
        """Test Slack event callback with a file containing sensitive data."""
        # Mocked file content and detected patterns
        file_content = "Sensitive content: test@example.com"
        mock_process_file.return_value = (file_content, [pattern_email])
        mock_create_detected_messages.return_value = []  # Mock bulk creation
        mock_delete_file_and_notify.return_value = None

        data = {
            "type": EVENT_CALLBACK,
            "event": {
                "type": EVENT_TYPE_MESSAGE,
                "text": "Here is a sensitive file",
                "channel": "C123456",
                "ts": "1626181234.000200",
                "files": [{"id": "file_with_leak"}],
            },
        }
        response = client.post(slack_event_url, data, format="json")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "received"}

        # Assert file processing
        mock_process_file.assert_called_once_with("file_with_leak")

        # Assert detected messages were created
        mock_create_detected_messages.assert_called_once_with(
            message=file_content, patterns=[pattern_email]
        )

        # Assert file was deleted and notification sent
        mock_delete_file_and_notify.assert_called_once_with(
            channel_id="C123456",
            file_id="file_with_leak",
        )

    @patch("apps.dlp.views.process_file")
    @patch("apps.dlp.views.delete_file_and_notify")
    def test_post_event_callback_file_with_no_leak(
        self,
        mock_delete_file_and_notify,
        mock_process_file,
        client,
        slack_event_url,
    ):
        """Test Slack event callback with a clean file."""
        # Mocked file content with no detected patterns
        mock_process_file.return_value = ("Clean file content", [])
        mock_delete_file_and_notify.return_value = None

        data = {
            "type": EVENT_CALLBACK,
            "event": {
                "type": EVENT_TYPE_MESSAGE,
                "text": "Here is a clean file",
                "channel": "C123456",
                "ts": "1626181234.000200",
                "files": [{"id": "file_with_no_leak"}],
            },
        }
        response = client.post(slack_event_url, data, format="json")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "received"}

        # Assert file processing
        mock_process_file.assert_called_once_with("file_with_no_leak")

        # Assert no detected messages were created
        mock_delete_file_and_notify.assert_not_called()
