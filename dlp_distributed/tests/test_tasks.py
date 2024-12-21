import urllib
import pytest
from django.conf import settings
from django.urls import reverse

from dlp_distributed.tasks import (
    fetch_patterns,
    send_detected_message,
    process_file,
    process_message,
)

detected_messages_url = urllib.parse.urljoin(
    settings.BASE_URL, reverse("dlp:detected-message-create")
)
pattern_url = urllib.parse.urljoin(settings.BASE_URL, reverse("dlp:pattern-list"))


@pytest.mark.asyncio
async def test_fetch_patterns(mocker):
    """
    Test that fetch_patterns retrieves patterns from the API.
    """
    mock_get = mocker.patch("aiohttp.ClientSession.get")
    mock_response = mocker.Mock()
    mock_response.status = 200
    mock_response.json = mocker.AsyncMock(
        return_value=[
            {
                "id": "1",
                "name": "Email",
                "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            }
        ]
    )
    mock_get.return_value.__aenter__.return_value = mock_response

    patterns = await fetch_patterns()

    assert len(patterns) == 1
    assert patterns[0]["name"] == "Email"
    assert (
        patterns[0]["regex"] == r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    )


@pytest.mark.asyncio
async def test_send_detected_message(mocker):
    """
    Test that send_detected_message sends data to the backend API.
    """
    mock_post = mocker.patch("aiohttp.ClientSession.post")
    mock_response = mocker.Mock()
    mock_response.status = 201
    mock_post.return_value.__aenter__.return_value = mock_response

    content = "This is a test message"
    pattern_id = "1"
    await send_detected_message(content=content, pattern_id=pattern_id)

    mock_post.assert_called_once_with(
        detected_messages_url,
        json={"content": content, "pattern": pattern_id},
    )


@pytest.mark.asyncio
async def test_send_detected_message_failure(mocker):
    """
    Test that send_detected_message handles API errors gracefully.
    """
    mock_post = mocker.patch("aiohttp.ClientSession.post")
    mock_response = mocker.Mock()
    mock_response.status = 400
    mock_response.text = "Bad Request"
    mock_post.return_value.__aenter__.return_value = mock_response

    content = "This is a test message"
    pattern_id = "1"
    await send_detected_message(content=content, pattern_id=pattern_id)

    mock_post.assert_called_once_with(
        detected_messages_url,
        json={"content": content, "pattern": pattern_id},
    )


@pytest.mark.asyncio
async def test_process_file(mocker):
    """
    Test that process_file fetches patterns, detects matches, and sends them to the API.
    """
    mock_fetch_patterns = mocker.patch(
        "dlp_distributed.tasks.fetch_patterns",
        return_value=[
            {
                "id": "1",
                "name": "Email",
                "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            }
        ],
    )
    mock_send_detected_message = mocker.patch(
        "dlp_distributed.tasks.send_detected_message"
    )

    await process_file("This is a test email: test@example.com")

    mock_fetch_patterns.assert_called_once()
    mock_send_detected_message.assert_called_once_with(
        content="This is a test email: test@example.com", pattern_id="1"
    )


@pytest.mark.asyncio
async def test_process_message(mocker):
    """
    Test that process_message fetches patterns, detects matches, and sends them to the API.
    """
    mock_fetch_patterns = mocker.patch(
        "dlp_distributed.tasks.fetch_patterns",
        return_value=[
            {"id": "1", "name": "Phone", "regex": r"\b\d{10}\b"},
        ],
    )
    mock_send_detected_message = mocker.patch(
        "dlp_distributed.tasks.send_detected_message"
    )

    await process_message("Call me at 1234567890")

    mock_fetch_patterns.assert_called_once()
    mock_send_detected_message.assert_called_once_with(
        content="Call me at 1234567890", pattern_id="1"
    )
