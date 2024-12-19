import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
class TestSlackEventView:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("dlp:slack_event")

    def test_post_valid_json(self):
        data = {
            "type": "event_callback",
            "event": {"type": "message", "text": "Hello, world!"},
        }
        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "received"}

    def test_post_invalid_json(self):
        # Simula un POST con JSON inválido
        response = self.client.post(
            self.url, "invalid json", content_type="application/json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_method_not_allowed(self):
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.json() == {"error": "method not allowed"}
