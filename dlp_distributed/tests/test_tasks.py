import os
from unittest.mock import AsyncMock, patch
from urllib.parse import urljoin

import aiohttp
import pytest
from slack_sdk.errors import SlackApiError

from tasks import (
    fetch_patterns,
    send_detected_message,
    process_file,
    process_message,
    replace_message,
    delete_file_and_notify,
    SLACK_BLOCKING_MESSAGE,
    SLACK_BLOCKING_FILE,
    logger,
)

SLACK_TOKEN = os.getenv("SLACK_USER_TOKEN")
BASE_URL = os.getenv("BASE_URL", "")

detected_messages_url = urljoin(BASE_URL, "/api/detected-messages/")
pattern_url = urljoin(BASE_URL, "/api/patterns/")


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
class TestFetchPatterns:
    @patch.object(logger, "info")
    async def test_success(self, mock_logger_info, mock_get):
        """
        Test that fetch_patterns retrieves patterns successfully.
        """
        # Mock the asynchronous response object
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = [{"id": 1, "regex": r"\d+"}]
        mock_get.return_value.__aenter__.return_value = mock_response

        # Call the function being tested
        result = await fetch_patterns()

        # Verify the response
        assert result == [{"id": 1, "regex": r"\d+"}]
        mock_logger_info.assert_called_once_with("Found fetch patterns.")
        mock_get.assert_called_once_with(f"{BASE_URL}/api/patterns/")

    @patch.object(logger, "error")
    async def test_failure(self, mock_logger_error, mock_get):
        """
        Test that fetch_patterns logs an error if the response status is not 200.
        """
        # Mock the asynchronous response object
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response

        # Call the function being tested
        result = await fetch_patterns()

        # Verify the response
        assert result == []
        mock_logger_error.assert_called_once_with(
            "Failed to fetch patterns. Status: 500"
        )
        mock_get.assert_called_once_with(f"{BASE_URL}/api/patterns/")

    @patch.object(logger, "error")
    async def test_exception(self, mock_logger_error, mock_get):
        """
        Test that fetch_patterns logs an error if an exception occurs.
        """
        # Mock an exception being raised
        mock_get.side_effect = Exception("Network error")

        # Call the function being tested
        result = await fetch_patterns()

        # Verify the response
        assert result == []
        mock_logger_error.assert_called_once_with(
            "Failed to fetch patterns: Network error"
        )
        mock_get.assert_called_once_with(f"{BASE_URL}/api/patterns/")


@pytest.mark.asyncio
@patch("aiohttp.client.ClientSession.post")
class TestSendDetectedMessage:
    @patch.object(logger, "info")
    async def test_success(self, mock_logger_info, mock_session_post):
        """
        Test that send_detected_message sends a detected message successfully.
        """
        # Mock the asynchronous response object
        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None
        mock_session_post.return_value = mock_response

        # Call the function being tested
        await send_detected_message(content="Test content", pattern_id="1")

        # Verify that the post method was called with the expected arguments
        mock_session_post.assert_called_once_with(
            detected_messages_url,
            json={"content": "Test content", "pattern": "1"},
        )
        mock_logger_info.assert_called_once_with("Detected message sent successfully.")

    @patch.object(logger, "error")
    async def test_failure(self, mock_logger_error, mock_session_post):
        """
        Test that send_detected_message raises an exception when sending fails.
        """
        # Mock the asynchronous response object to simulate an error
        mock_session_post.side_effect = aiohttp.ClientError("Failed to send message")

        # Verify that the function raises the expected exception
        with pytest.raises(aiohttp.ClientError, match="Failed to send message"):
            await send_detected_message(content="Test content", pattern_id="1")

        # Verify that the post method was called with the expected arguments
        mock_session_post.assert_called_once_with(
            detected_messages_url,
            json={"content": "Test content", "pattern": "1"},
        )
        mock_logger_error.assert_called_once_with(
            "Failed to send detected message: Failed to send message"
        )


@pytest.mark.asyncio
@patch("slack_sdk.web.async_client.AsyncWebClient.chat_update")
class TestReplaceMessage:

    @patch.object(logger, "info")
    async def test_success(self, mock_logger_info, mock_chat_update):
        """
        Test that replace_message successfully replaces a Slack message.
        """
        # Mock the Slack response
        mock_response = AsyncMock()
        mock_chat_update.return_value = mock_response

        channel_id = "C123456"
        ts = "1234567890.123456"
        new_message = "Updated message content"

        # Call the function being tested
        response = await replace_message(
            channel_id=channel_id,
            ts=ts,
            new_message=new_message,
        )

        # Verify the response
        assert response == mock_response
        mock_chat_update.assert_called_once_with(
            channel=channel_id,
            ts=ts,
            text=new_message,
        )
        mock_logger_info.assert_any_call(
            f"Attempting to replace message in channel {channel_id} at {ts}. Token: {SLACK_TOKEN}"
        )
        mock_logger_info.assert_any_call(
            f"Message replaced successfully. Response: {mock_response}"
        )

    @patch.object(logger, "error")
    async def test_failure(self, mock_logger_error, mock_chat_update):
        """
        Test that replace_message logs an error when Slack API fails.
        """
        channel_id = "C123456"
        ts = "1234567890.123456"
        new_message = "Updated message content"
        error_message = "channel_not_found"

        # Mock a Slack API error
        mock_chat_update.side_effect = SlackApiError(
            message="Error replacing message", response={"error": error_message}
        )

        # Call the function being tested
        response = await replace_message(
            channel_id=channel_id,
            ts=ts,
            new_message=new_message,
        )

        # Verify the response
        assert response is None
        mock_chat_update.assert_called_once_with(
            channel=channel_id,
            ts=ts,
            text=new_message,
        )
        mock_logger_error.assert_called_once_with(
            f"Error replacing message: {error_message}"
        )


@pytest.mark.asyncio
@patch("slack_sdk.web.async_client.AsyncWebClient.files_delete")
@patch("slack_sdk.web.async_client.AsyncWebClient.chat_postMessage")
class TestDeleteFileAndNotify:
    @patch.object(logger, "info")
    async def test_success(
        self, mock_logger_info, mock_chat_postMessage, mock_files_delete
    ):
        """
        Test that delete_file_and_notify successfully deletes a file and sends a notification.
        """
        channel_id = "C123456"
        file_id = "F123456"

        # Mock Slack API responses
        mock_files_delete.return_value = {"ok": True}
        mock_chat_postMessage.return_value = {"ok": True}

        # Call the function being tested
        await delete_file_and_notify(file_id=file_id, channel_id=channel_id)

        # Verify API calls
        mock_files_delete.assert_called_once_with(file=file_id)
        mock_chat_postMessage.assert_called_once_with(
            channel=channel_id,
            text=SLACK_BLOCKING_FILE,
        )

        # Verify log messages
        mock_logger_info.assert_any_call(
            "Attempting to delete file F123456 in channel C123456."
        )
        mock_logger_info.assert_any_call(
            "File F123456 deleted successfully. Notification sent to channel C123456."
        )

    @patch.object(logger, "error")
    async def test_file_delete_failure(
        self, mock_logger_error, mock_chat_postMessage, mock_files_delete
    ):
        """
        Test that delete_file_and_notify logs an error when file deletion fails.
        """
        channel_id = "C123456"
        file_id = "F123456"
        error_message = "file_not_found"

        # Mock Slack API response for file delete failure
        mock_files_delete.return_value = {"ok": False, "error": error_message}

        # Call the function being tested
        await delete_file_and_notify(file_id=file_id, channel_id=channel_id)

        # Verify API calls
        mock_files_delete.assert_called_once_with(file=file_id)
        mock_chat_postMessage.assert_not_called()  # Notification should not be sent

        # Verify log messages
        mock_logger_error.assert_called_once_with(
            f"Failed to delete file F123456: {error_message}"
        )

    @patch.object(logger, "error")
    async def test_notification_failure(
        self, mock_logger_error, mock_chat_postMessage, mock_files_delete
    ):
        """
        Test that delete_file_and_notify logs an error when notification fails.
        """
        channel_id = "C123456"
        file_id = "F123456"
        error_message = "channel_not_found"

        # Mock Slack API responses
        mock_files_delete.return_value = {"ok": True}
        mock_chat_postMessage.return_value = {"ok": False, "error": error_message}

        # Call the function being tested
        await delete_file_and_notify(file_id=file_id, channel_id=channel_id)

        # Verify API calls
        mock_files_delete.assert_called_once_with(file=file_id)
        mock_chat_postMessage.assert_called_once_with(
            channel=channel_id,
            text=SLACK_BLOCKING_FILE,
        )

        # Verify log messages
        mock_logger_error.assert_called_once_with(
            f"Failed to send notification to channel C123456: {error_message}"
        )

    @patch.object(logger, "error")
    async def test_slack_api_error(
        self, mock_logger_error, mock_chat_postMessage, mock_files_delete
    ):
        """
        Test that delete_file_and_notify handles SlackApiError correctly.
        """
        channel_id = "C123456"
        file_id = "F123456"
        error_message = "invalid_auth"

        # Mock Slack API to raise an error
        mock_files_delete.side_effect = SlackApiError(
            "Error deleting file", {"error": error_message}
        )

        # Call the function being tested
        await delete_file_and_notify(file_id=file_id, channel_id=channel_id)

        # Verify API calls
        mock_files_delete.assert_called_once_with(file=file_id)
        mock_chat_postMessage.assert_not_called()  # Notification should not be sent

        # Verify log messages
        mock_logger_error.assert_called_once_with(
            f"Slack API Error during file delete/notify: {error_message}"
        )


@pytest.mark.asyncio
@patch("slack_sdk.web.async_client.AsyncWebClient.chat_update")
@patch("aiohttp.ClientSession.get")
@patch("aiohttp.ClientSession.post")
class TestProcessMessage:
    @patch.object(logger, "info")
    async def test_success_with_matches(
        self,
        mock_logger_info,
        mock_session_post,
        mock_session_get,
        mock_slack_update,
    ):
        """
        Test that process_message detects patterns and replaces the message on Slack.
        """
        # Test variables
        message = "Test message with 123"
        channel_id = "C123456"
        ts = "1234567890.123456"
        detected_pattern = {"id": "1", "regex": r"\d+"}

        # Mock fetch_patterns response
        mock_response_get = AsyncMock()
        mock_response_get.status = 200
        mock_response_get.json.return_value = [detected_pattern]
        mock_session_get.return_value.__aenter__.return_value = mock_response_get

        # Mock send_detected_message response
        mock_response_post = AsyncMock()
        mock_response_post.raise_for_status.return_value = None
        mock_session_post.return_value.__aenter__.return_value = mock_response_post

        # Mock replace_message response
        mock_slack_update.return_value = {"ok": True}

        # Call the function being tested
        await process_message(
            message=message,
            channel_id=channel_id,
            ts=ts,
        )

        # Verify that the GET request for fetch_patterns was called
        mock_session_get.assert_called_once_with(f"{BASE_URL}/api/patterns/")

        # Verify that the POST request for send_detected_message was called
        mock_session_post.assert_called_once_with(
            detected_messages_url,
            json={"content": message, "pattern": detected_pattern["id"]},
        )

        # Verify that the Slack message update was called
        mock_slack_update.assert_called_once_with(
            channel=channel_id,
            ts=ts,
            text=SLACK_BLOCKING_MESSAGE,
        )

        # Verify logger calls
        mock_logger_info.assert_any_call(f"Processing message: {message}")
        mock_logger_info.assert_any_call("Message processed with 1 matches found.")

    @patch.object(logger, "info")
    async def test_success_no_matches(
        self,
        mock_logger_info,
        mock_session_post,
        mock_session_get,
        mock_slack_update,
    ):
        """
        Test that process_message logs no matches when there are no patterns detected.
        """
        # Test variables
        message = "Short msg"
        channel_id = "C123456"
        ts = "1234567890.123456"
        unmatched_pattern = {"id": "1", "regex": r"[a-z]{10}"}

        # Mock fetch_patterns response with no matching patterns
        mock_response_get = AsyncMock()
        mock_response_get.status = 200
        mock_response_get.json.return_value = [unmatched_pattern]
        mock_session_get.return_value.__aenter__.return_value = mock_response_get

        # Call the function being tested
        await process_message(
            message=message,
            channel_id=channel_id,
            ts=ts,
        )

        # Verify that no POST or Slack update calls were made
        mock_session_post.assert_not_called()
        mock_slack_update.assert_not_called()

        # Verify logger calls
        mock_logger_info.assert_any_call(f"Processing message: {message}")
        mock_logger_info.assert_any_call("No matches found in the message.")

    @patch.object(logger, "error")
    async def test_failure_fetch_patterns(
        self,
        mock_logger_error,
        mock_session_post,
        mock_session_get,
        mock_slack_update,
    ):
        """
        Test that process_message handles fetch_patterns failure gracefully.
        """
        # Test variables
        message = "Test message"
        channel_id = "C123456"
        ts = "1234567890.123456"
        error_message = "Network error"

        # Mock fetch_patterns to raise an exception
        mock_session_get.side_effect = Exception(error_message)

        # Call the function being tested
        await process_message(
            message=message,
            channel_id=channel_id,
            ts=ts,
        )

        # Verify that no POST or Slack update calls were made
        mock_session_post.assert_not_called()
        mock_slack_update.assert_not_called()

        # Verify logger calls
        mock_logger_error.assert_called_once_with(
            f"Failed to fetch patterns: {error_message}"
        )


@pytest.mark.asyncio
@patch("slack_sdk.web.async_client.AsyncWebClient.files_info")
@patch("aiohttp.ClientSession.get")
@patch("aiohttp.ClientSession.post")
@patch("slack_sdk.web.async_client.AsyncWebClient.chat_postMessage")
@patch("slack_sdk.web.async_client.AsyncWebClient.files_delete")
class TestProcessFile:
    @patch("re.search")
    @patch.object(logger, "info")
    async def test_success_with_matches(
        self,
        mock_logger_info,
        mock_re_search,
        mock_files_delete,
        mock_chat_postMessage,
        mock_session_post,
        mock_session_get,
        mock_files_info,
    ):
        file_id = "F123456"
        channel_id = "C123456"
        file_content = "Sensitive information with 123"
        detected_pattern = {"id": "1", "regex": r"\d+"}
        blocked_file_message = "File was deleted for containing sensitive information."
        headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}

        # Mock files_info response
        mock_files_info.return_value = {
            "file": {"url_private_download": "https://example.com/file"}
        }

        # Mock file content download
        mock_response_get_file = AsyncMock()
        mock_response_get_file.status = 200
        mock_response_get_file.text.return_value = file_content
        mock_session_get.return_value.__aenter__.return_value = mock_response_get_file

        # Mock fetch_patterns response
        mock_response_get_patterns = AsyncMock()
        mock_response_get_patterns.status = 200
        mock_response_get_patterns.json.return_value = [detected_pattern]
        mock_session_get.return_value.__aenter__.side_effect = [
            mock_response_get_file,
            mock_response_get_patterns,
        ]

        # Mock re.search to return a match
        mock_re_search.return_value = True

        # Mock send_detected_message response
        mock_response_post = AsyncMock()
        mock_response_post.raise_for_status.return_value = None
        mock_session_post.return_value.__aenter__.return_value = mock_response_post

        # Mock files_delete and chat_postMessage responses
        mock_files_delete.return_value = {"ok": True}
        mock_chat_postMessage.return_value = {"ok": True}

        # Call the function being tested
        await process_file(file_id=file_id, channel_id=channel_id)

        # Verify API calls
        mock_files_info.assert_called_once_with(file=file_id)
        mock_session_get.assert_any_call("https://example.com/file", headers=headers)
        mock_session_post.assert_called_once_with(
            detected_messages_url,
            json={"content": file_content, "pattern": detected_pattern["id"]},
        )
        mock_files_delete.assert_called_once_with(file=file_id)
        mock_chat_postMessage.assert_called_once_with(
            channel=channel_id, text=blocked_file_message
        )

        # Verify re.search was called with the expected arguments
        mock_re_search.assert_called_once_with(detected_pattern["regex"], file_content)

        # Verify logger calls
        mock_logger_info.assert_any_call(f"Processing file content")
        mock_logger_info.assert_any_call("File processed with 1 matches found.")
        mock_logger_info.assert_any_call(
            f"File {file_id} deleted successfully. Notification sent to channel {channel_id}."
        )

    @patch.object(logger, "info")
    async def test_no_matches(
        self,
        mock_logger_info,
        mock_files_delete,
        mock_chat_postMessage,
        mock_session_post,
        mock_session_get,
        mock_files_info,
    ):
        file_id = "F123456"
        channel_id = "C123456"
        file_content = "Non-sensitive information"
        unmatched_pattern = {"id": "1", "regex": r"\d+"}
        headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}

        # Mock files_info response
        mock_files_info.return_value = {
            "file": {"url_private_download": "https://example.com/file"}
        }

        # Mock file content download
        mock_response_get_file = AsyncMock()
        mock_response_get_file.status = 200
        mock_response_get_file.text.return_value = file_content
        mock_session_get.return_value.__aenter__.return_value = mock_response_get_file

        # Mock fetch_patterns response with no matches
        mock_response_get_patterns = AsyncMock()
        mock_response_get_patterns.status = 200
        mock_response_get_patterns.json.return_value = [unmatched_pattern]
        mock_session_get.return_value.__aenter__.side_effect = [
            mock_response_get_file,
            mock_response_get_patterns,
        ]

        # Call the function being tested
        await process_file(file_id=file_id, channel_id=channel_id)

        # Verify that no POST, delete, or notification calls were made
        mock_session_post.assert_not_called()
        mock_files_delete.assert_not_called()
        mock_chat_postMessage.assert_not_called()

        # Verify logger calls
        mock_logger_info.assert_any_call(f"Processing file content")
        mock_logger_info.assert_any_call("No matches found in the file.")

    @patch.object(logger, "error")
    async def test_failed_to_download_file(
        self,
        mock_logger_error,
        mock_files_delete,
        mock_chat_postMessage,
        mock_session_post,
        mock_session_get,
        mock_files_info,
    ):
        file_id = "F123456"
        channel_id = "C123456"
        headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}

        # Mock files_info response
        mock_files_info.return_value = {
            "file": {"url_private_download": "https://example.com/file"}
        }

        # Mock file content download with non-200 status
        mock_response_get_file = AsyncMock()
        mock_response_get_file.status = 404  # Simulating file not found
        mock_session_get.return_value.__aenter__.return_value = mock_response_get_file

        # Call the function being tested
        await process_file(file_id=file_id, channel_id=channel_id)

        # Verify logger calls
        mock_logger_error.assert_called_once_with("Failed to download file: 404")

        # Verify that no further API calls were made
        mock_session_post.assert_not_called()
        mock_files_delete.assert_not_called()
        mock_chat_postMessage.assert_not_called()

    @patch.object(logger, "error")
    async def test_slack_api_error(
        self,
        mock_logger_error,
        mock_files_delete,
        mock_chat_postMessage,
        mock_session_post,
        mock_session_get,
        mock_files_info,
    ):
        file_id = "F123456"
        channel_id = "C123456"
        error_message = "invalid_auth"

        # Mock Slack API error during files_info
        mock_files_info.side_effect = SlackApiError(
            message="Slack API error", response={"error": error_message}
        )

        # Call the function being tested
        await process_file(file_id=file_id, channel_id=channel_id)

        # Verify logger calls
        mock_logger_error.assert_called_once_with(f"Slack API error: {error_message}")

        # Verify that no further API calls were made
        mock_session_get.assert_not_called()
        mock_session_post.assert_not_called()
        mock_files_delete.assert_not_called()
        mock_chat_postMessage.assert_not_called()
