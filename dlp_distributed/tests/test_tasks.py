import pytest
from unittest.mock import patch
from dlp_distributed.tasks import (
    fetch_patterns,
    send_detected_message,
    process_file,
    process_message,
)

BASE_URL = "http://127.0.0.1:8000/dlp"

BASE_URL = "http://127.0.0.1:8000/dlp"


@pytest.mark.asyncio
@patch("apps.dlp.tasks.fetch_patterns")
@patch("apps.dlp.tasks.send_detected_message")
async def test_process_file(mock_send_detected_message, mock_fetch_patterns):
    """
    Test that process_file fetches patterns, detects matches, and sends them to the API.
    """
    mock_fetch_patterns.return_value = [
        {
            "id": "1",
            "name": "Email",
            "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        },
    ]

    await process_file("This is a test email: test@example.com")

    mock_fetch_patterns.assert_called_once()
    mock_send_detected_message.assert_called_once_with(
        "This is a test email: test@example.com", "1"
    )


@pytest.mark.asyncio
@patch("apps.dlp.tasks.fetch_patterns")
@patch("apps.dlp.tasks.send_detected_message")
async def test_process_message(mock_send_detected_message, mock_fetch_patterns):
    """
    Test that process_message fetches patterns, detects matches, and sends them to the API.
    """
    mock_fetch_patterns.return_value = [
        {"id": "1", "name": "Phone", "regex": r"\b\d{10}\b"},
    ]

    await process_message("Call me at 1234567890")

    mock_fetch_patterns.assert_called_once()
    mock_send_detected_message.assert_called_once_with("Call me at 1234567890", "1")


@pytest.mark.asyncio
@patch("apps.dlp.tasks.requests.get")
async def test_fetch_patterns(mock_get):
    """
    Test that fetch_patterns retrieves patterns from the API.
    """
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {
            "id": "1",
            "name": "Email",
            "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        },
    ]

    patterns = await fetch_patterns()

    assert len(patterns) == 1
    assert patterns[0]["name"] == "Email"
    assert (
        patterns[0]["regex"] == r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    )


@pytest.mark.asyncio
@patch("apps.dlp.tasks.requests.post")
async def test_send_detected_message_success(mock_post):
    """
    Test that send_detected_message sends data to the API successfully.
    """
    mock_post.return_value.status_code = 201

    content = "This is a test message"
    pattern_id = "1"

    # Llamar a la función asíncrona
    await send_detected_message(content=content, pattern_id=pattern_id)

    mock_post.assert_called_once_with(
        f"{BASE_URL}/detected-messages/",
        json={"content": content, "pattern": pattern_id},
    )


@pytest.mark.asyncio
@patch("apps.dlp.tasks.requests.post")
async def test_send_detected_message_failure(mock_post):
    """
    Test that send_detected_message handles API errors gracefully.
    """
    mock_post.return_value.status_code = 400
    mock_post.return_value.text = "Bad Request"

    content = "This is a test message"
    pattern_id = "1"

    await send_detected_message(content=content, pattern_id=pattern_id)

    mock_post.assert_called_once_with(
        f"{BASE_URL}/detected-messages/",
        json={"content": content, "pattern": pattern_id},
    )
