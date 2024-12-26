import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from unittest.mock import patch
from apps.dlp.models import Pattern, DetectedMessage
from apps.dlp.serializers import PatternSerializer


@pytest.fixture
def detected_message(pattern):
    return DetectedMessage.objects.create(content="Test content", pattern=pattern)


# Tests for SlackEventView
@pytest.mark.django_db
@patch("apps.dlp.views.send_to_sqs")
def test_slack_event_view_process_message(mock_send_to_sqs, api_client):
    """
    Test SlackEventView processes message events correctly by sending a task to SQS.
    """
    url = reverse("dlp:slack_event")  # Replace with the actual URL name
    payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "text": "Test message",
            "channel": "C123456789",
            "ts": "1234567890.123456",
        },
    }

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 200
    mock_send_to_sqs.assert_called_once_with(
        task_name="process_message",
        kwargs={
            "message": "Test message",
            "channel_id": "C123456789",
            "ts": "1234567890.123456",
        },
    )


@pytest.mark.django_db
@patch("apps.dlp.views.send_to_sqs")
def test_slack_event_view_process_file(mock_send_to_sqs, api_client):
    """
    Test SlackEventView processes file events correctly by sending a task to SQS.
    """
    url = reverse("dlp:slack_event")
    payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "files": [{"id": "F123456"}],
            "channel": "C123456789",
        },
    }

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 200
    mock_send_to_sqs.assert_called_once_with(
        task_name="process_file",
        kwargs={"file_id": "F123456", "channel_id": "C123456789"},
    )


def test_slack_event_view_challenge(api_client):
    """
    Test SlackEventView returns the correct challenge token for URL verification.
    """
    url = reverse("dlp:slack_event")
    payload = {"type": "url_verification", "challenge": "challenge_token"}

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 200
    assert response.json()["challenge"] == "challenge_token"


# Tests for PatternListAPIView
@pytest.mark.django_db
def test_pattern_list_view(api_client, pattern):
    """
    Test PatternListAPIView retrieves all patterns successfully.
    """
    url = reverse("dlp:pattern-list")
    response = api_client.get(url)

    assert response.status_code == 200
    patterns = Pattern.objects.all()
    serializer = PatternSerializer(patterns, many=True)
    assert response.json() == serializer.data


# Tests for DetectedMessageCreateAPIView
@pytest.mark.django_db
def test_detected_message_create_view(api_client, pattern):
    """
    Test DetectedMessageCreateAPIView creates a detected message successfully.
    """
    url = reverse("dlp:detected-message-create")
    payload = {"content": "Test content", "pattern": pattern.id}

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 201
    assert DetectedMessage.objects.count() == 1
    assert response.json()["content"] == "Test content"
    assert response.json()["pattern"] == str(pattern.id)


@pytest.mark.django_db
def test_detected_message_create_view_invalid_data(api_client):
    """
    Test DetectedMessageCreateAPIView returns a 400 response for invalid data.
    """
    url = reverse("dlp:detected-message-create")
    payload = {"content": ""}  # Missing required field "pattern"

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 400
