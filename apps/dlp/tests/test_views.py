import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


@pytest.fixture
def mock_logger_info(mocker):
    """Mock the logger.info method for SlackEventView."""
    return mocker.patch("apps.dlp.views.logger.info")


@pytest.fixture
def mock_logger_debug(mocker):
    """Mock the logger.debug method for SlackEventView."""
    return mocker.patch("apps.dlp.views.logger.debug")


@pytest.mark.django_db
class TestSlackEventView:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("dlp:slack_event")  # Ensure the URL name matches

    def test_post_url_verification(self):
        """Test a valid Slack URL verification request."""
        data = {"type": "url_verification", "challenge": "test_challenge"}
        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "challenge": "test_challenge",
            "status": "received",
        }

    def test_post_event_callback_message(self, mock_logger_info):
        """Test a valid Slack event callback with a message."""
        message = "Hello, world!"
        data = {
            "type": "event_callback",
            "event": {"type": "message", "text": message},
        }
        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "status": "received",
        }
        mock_logger_info.assert_called_once_with(f"Message received: {message}")

    def test_post_event_callback_non_message(self, mock_logger_debug):
        """Test a valid Slack event callback with a non-message event."""
        event_type = "reaction_added"
        data = {
            "type": "event_callback",
            "event": {"type": event_type, "reaction": "thumbsup"},
        }
        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "status": "received",
        }
        mock_logger_debug.assert_called_once_with(f"Unhandled event type: {event_type}")

    def test_post_invalid_payload(self):
        """Test a POST request with an invalid payload."""
        data = {"type": "invalid_type"}
        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "status": "received",
        }

    def test_get_method_not_allowed(self):
        """Test that GET requests are not allowed."""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
