import json

import pytest
from django.urls import reverse
from rest_framework import status

from apps.dlp.constants import EVENT_CALLBACK, EVENT_TYPE_MESSAGE


@pytest.mark.django_db
class TestSlackEventView:
    def test_post_url_verification(self, client, slack_event_url):
        """Test a valid Slack URL verification request."""
        data = {"type": "url_verification", "challenge": "test_challenge"}
        response = client.post(slack_event_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "challenge": "test_challenge",
            "status": "received",
        }

    def test_post_event_callback_message(
        self, client, slack_event_url, mock_logger_info
    ):
        """Test a valid Slack event callback with a message."""
        message = "Hello, world!"
        data = {
            "type": EVENT_CALLBACK,
            "event": {"type": EVENT_TYPE_MESSAGE, "text": message},
        }
        response = client.post(slack_event_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "received"}
        mock_logger_info.assert_called_once_with(f"Message received: {message}")

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

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "received"}
        mock_logger_debug.assert_called_once_with(f"Unhandled event type: {event_type}")

    def test_post_invalid_payload(self, client, slack_event_url):
        """Test a POST request with an invalid payload."""
        data = {"type": "invalid_type"}
        response = client.post(slack_event_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"status": "received"}

    def test_get_method_not_allowed(self, client, slack_event_url):
        """Test that GET requests are not allowed."""
        response = client.get(slack_event_url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestPatternListAPIView:
    def test_get_patterns_success(self, client, pattern_email):
        """
        Test that the API endpoint returns a list of patterns successfully.
        """
        url = reverse("dlp:pattern-list")
        response = client.get(url)

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == pattern_email.name
        assert response.data[0]["regex"] == pattern_email.regex

    def test_get_patterns_empty(self, client):
        """
        Test that the API endpoint returns an empty list if no patterns exist.
        """
        url = reverse("dlp:pattern-list")
        response = client.get(url)

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


@pytest.mark.django_db
class TestDetectedMessageCreateAPIView:
    def test_create_detected_message_invalid_payload(self, client):
        """
        Test that an invalid payload returns a 400 error.
        """
        url = reverse("dlp:detected-message-create")
        # Incorrect payload (missing pattern field)
        payload = {"content": "This is a detected message"}

        # Send as JSON
        response = client.post(
            url, data=json.dumps(payload), content_type="application/json"
        )

        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "pattern" in response.data
