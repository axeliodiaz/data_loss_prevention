from unittest.mock import patch

import pytest
from rest_framework import status

from apps.dlp.constants import (
    EVENT_CALLBACK,
    EVENT_TYPE_MESSAGE,
)


@pytest.mark.django_db
class TestSlackEventView:
    @patch("apps.dlp.views.send_to_sqs")
    def test_post_event_callback_message_with_file(
        self, mock_send_to_sqs, client, slack_event_url
    ):
        """Test Slack event callback with a file containing sensitive data."""
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
        mock_send_to_sqs.assert_called_once_with(
            task_name="process_file",
            kwargs={"file_id": "file123", "channel_id": "C123456"},
        )

    @patch("apps.dlp.views.send_to_sqs")
    def test_post_event_callback_message_with_leak(
        self, mock_send_to_sqs, client, slack_event_url
    ):
        """Test Slack event callback with a message containing sensitive data."""
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
        mock_send_to_sqs.assert_called_once_with(
            task_name="process_message",
            kwargs={
                "message": message,
                "channel_id": "C123456",
                "ts": "1626181234.000200",
            },
        )

    @patch("apps.dlp.views.send_to_sqs")
    def test_post_event_callback_message_with_clean_file(
        self, mock_send_to_sqs, client, slack_event_url
    ):
        """Test Slack event callback with a clean file."""
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
        mock_send_to_sqs.assert_called_once_with(
            task_name="process_file",
            kwargs={"file_id": "file123", "channel_id": "C123456"},
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

    @patch("apps.dlp.views.send_to_sqs")
    def test_post_event_callback_file_with_leak(
        self, mock_send_to_sqs, client, slack_event_url
    ):
        """Test Slack event callback with a file containing sensitive data."""
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
        mock_send_to_sqs.assert_called_once_with(
            task_name="process_file",
            kwargs={"file_id": "file_with_leak", "channel_id": "C123456"},
        )

    @patch("apps.dlp.views.send_to_sqs")
    def test_post_event_callback_file_with_no_leak(
        self, mock_send_to_sqs, client, slack_event_url
    ):
        """Test Slack event callback with a clean file."""
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
        mock_send_to_sqs.assert_called_once_with(
            task_name="process_file",
            kwargs={"file_id": "file_with_no_leak", "channel_id": "C123456"},
        )
