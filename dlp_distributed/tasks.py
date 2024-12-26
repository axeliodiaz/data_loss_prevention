import logging
import os
import re
from urllib.parse import urljoin

import aiohttp
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

SLACK_BLOCKING_MESSAGE = "Message was blocked due to containing sensitive information."
SLACK_BLOCKING_FILE = "File was deleted for containing sensitive information."

logger = logging.getLogger(__name__)

SLACK_TOKEN = os.getenv("SLACK_USER_TOKEN")
BASE_URL = os.getenv("BASE_URL", "")

# Construct URLs for backend API endpoints
detected_messages_url = urljoin(BASE_URL, "/api/detected-messages/")
pattern_url = urljoin(BASE_URL, "/api/patterns/")

slack_client = AsyncWebClient(token=SLACK_TOKEN)


async def fetch_patterns():
    headers = {"Host": "backend"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"{BASE_URL}/api/patterns/") as response:
                if response.status == 200:
                    logger.info("Found fetch patterns.")
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch patterns. Status: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Failed to fetch patterns: {e}")
        return []


async def send_detected_message(content: str, pattern_id: str):
    """
    Send detected message to the backend API.
    """
    payload = {"content": content, "pattern": pattern_id}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(detected_messages_url, json=payload) as response:
                response.raise_for_status()
        except aiohttp.ClientError as e:
            logger.error(f"Failed to send detected message: {e}")
            raise e
        logger.info("Detected message sent successfully.")


async def process_file(file_id: str, channel_id: str):
    """
    Process a file, detect patterns, and notify Slack if needed.

    Args:
        file_id (str): The ID of the Slack file to process.
        channel_id (str): The ID of the Slack channel.
    """
    try:
        # Fetch file info from Slack
        file_info = await slack_client.files_info(file=file_id)
        file_url = file_info["file"]["url_private_download"]

        headers = {"Authorization": f"Bearer {os.getenv('SLACK_USER_TOKEN')}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url, headers=headers) as file_response:
                if file_response.status == 200:
                    file_content = await file_response.text()
                    logger.info(f"Processing file content")

                    # Fetch patterns and scan the file
                    patterns = await fetch_patterns()
                    matches = [
                        pattern
                        for pattern in patterns
                        if re.search(pattern["regex"], file_content)
                    ]

                    if matches:
                        # Notify detected patterns
                        for match in matches:
                            await send_detected_message(
                                content=file_content, pattern_id=match["id"]
                            )
                        logger.info(
                            f"File processed with {len(matches)} matches found."
                        )

                        # Delete file and notify channel
                        await delete_file_and_notify(file_id, channel_id)
                    else:
                        logger.info("No matches found in the file.")
                else:
                    logger.error(f"Failed to download file: {file_response.status}")
    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")


async def process_message(
    message: str, channel_id: str | None = None, ts: str | None = None
):
    """
    Process a message, detect patterns, and notify Slack if needed.

    Args:
        message (str): The message text to process.
        channel_id (str, optional): The ID of the Slack channel where the message was sent.
        ts (str, optional): The timestamp of the Slack message.
    """
    logger.info(f"Processing message: {message}")
    if channel_id:
        logger.info(f"Channel ID: {channel_id}")
    if ts:
        logger.info(f"Message timestamp: {ts}")

    # Fetch patterns from the API
    patterns = await fetch_patterns()
    matches = [pattern for pattern in patterns if re.search(pattern["regex"], message)]

    if matches:
        # Notify detected patterns
        for match in matches:
            await send_detected_message(content=message, pattern_id=match["id"])

        logger.info(f"Message processed with {len(matches)} matches found.")

        # Replace the message in Slack
        if channel_id and ts:
            await replace_message(channel_id, ts, SLACK_BLOCKING_MESSAGE)
    else:
        logger.info("No matches found in the message.")


async def replace_message(channel_id: str, ts: str, new_message: str):
    """
    Replaces a message in Slack with a new one.

    Args:
        channel_id (str): The ID of the Slack channel.
        ts (str): The timestamp of the original message.
        new_message (str): The replacement message.
    """
    logger.info(
        f"Attempting to replace message in channel {channel_id} at {ts}. Token: {SLACK_TOKEN}"
    )
    try:
        response = await slack_client.chat_update(
            channel=channel_id,
            ts=ts,
            text=new_message,
        )
        logger.info(f"Message replaced successfully. Response: {response}")
        return response
    except SlackApiError as e:
        logger.error(f"Error replacing message: {e.response['error']}")


async def delete_file_and_notify(file_id: str, channel_id: str):
    """
    Asynchronously delete a file and notify the channel about its removal.

    Args:
        file_id (str): The ID of the file to delete.
        channel_id (str): The ID of the Slack channel to notify.
    """
    logger.info(f"Attempting to delete file {file_id} in channel {channel_id}.")
    try:
        response = await slack_client.files_delete(file=file_id)
        if response.get("ok"):
            notify_response = await slack_client.chat_postMessage(
                channel=channel_id,
                text=SLACK_BLOCKING_FILE,
            )
            if not notify_response.get("ok"):
                logger.error(
                    f"Failed to send notification to channel {channel_id}: {notify_response.get('error')}"
                )
        else:
            logger.error(f"Failed to delete file {file_id}: {response.get('error')}")
    except SlackApiError as e:
        logger.error(
            f"Slack API Error during file delete/notify: {e.response['error']}"
        )

    logger.info(
        f"File {file_id} deleted successfully. Notification sent to channel {channel_id}."
    )


# Task dictionary for distributed task processing
TASKS = {
    "process_file": process_file,
    "process_message": process_message,
}
