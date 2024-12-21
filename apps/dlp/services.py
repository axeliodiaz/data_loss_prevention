import logging
import re
from typing import List

import requests

from apps.dlp.constants import SLACK_BLOCKING_FILE
from apps.dlp.models import DetectedMessage, Pattern
from data_loss_prevention.settings import SLACK_BOT_TOKEN, SLACK_USER_TOKEN

logger = logging.getLogger(__name__)

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


client = WebClient(token=SLACK_USER_TOKEN)


def scan_message(message: str):
    """
    Scans a message for matches against a list of patterns.

    Args:
        message (str): The message to scan.
        patterns (list): List of objects with `regex` attributes.

    Returns:
        list: List of matching patterns.
    """
    if not isinstance(message, (str, bytes)):
        logger.error("Invalid message type passed to scan_message: %s", type(message))
        return []

    matches = []
    patterns = Pattern.objects.all()
    for pattern in patterns:
        if re.search(pattern.regex, message):
            matches.append(pattern)
    return matches


def get_file_info(file_id: str) -> str | None:
    """
    Fetch file information from Slack using slack-sdk.

    Args:
        file_id (str): The ID of the file to fetch.

    Returns:
        str: The text contained in the file, or None if an error occurs.
    """
    try:
        response = client.files_info(file=file_id)
    except SlackApiError as e:
        logger.debug(f"Slack API Error: {e.response['error']}")
        return None

    if response["ok"]:
        headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        file_response = requests.get(
            response["file"]["url_private_download"], headers=headers
        )

        if file_response.status_code == 200:
            return file_response.text
        else:
            logger.debug(f"Failed to download file: {file_response.status_code}")
            return None
    else:
        logger.debug(f"Error: {response['error']}")
        return None


def process_file(file_id) -> tuple[str | None, list]:
    """
    Get the file from Slack to be analyzed.

    Args:
        file_id (str): The ID of the file to fetch from Slack.

    Returns:
        tuple: The file content (str or None) and the list of matches (list).
    """
    matches = []
    file_content = get_file_info(file_id=file_id)

    if file_content:
        # Analyze the file
        matches = scan_message(file_content)

    return file_content, matches


def create_detected_messages(
    message: str, patterns: List[Pattern]
) -> List[DetectedMessage]:
    """
    Create DetectedMessage objects for each detected pattern individually.

    Args:
        message (str): The content of the detected message.
        patterns (List[Pattern]): List of matching Pattern instances.

    Returns:
        List[DetectedMessage]: A list of created DetectedMessage instances.
    """
    detected_messages = []
    for pattern in patterns:
        detected_message = DetectedMessage.objects.create(
            content=message, pattern=pattern
        )
        detected_messages.append(detected_message)

    logger.info(f"Detected message: {message}")
    return detected_messages


def replace_message(channel_id, ts, new_message):
    """
    Replaces a message in Slack with a new one.

    Args:
        channel_id (str): The ID of the Slack channel.
        ts (str): The timestamp of the original message.
        new_message (str): The replacement message.

    Returns:
        dict: The response from Slack API.
    """
    try:
        response = client.chat_update(
            channel=channel_id,
            ts=ts,
            text=new_message,
        )
    except SlackApiError as e:
        logger.error(f"Error replacing message: {e.response['error']}")
        return None

    logger.info(f"Message replaced: {response}")
    return response


def delete_file_and_notify(
    file_id,
    channel_id,
    message=SLACK_BLOCKING_FILE,
):
    """
    Delete a file and notify the channel about its removal.

    Args:
        file_id (str): The ID of the file to delete.
        channel_id (str): The ID of the Slack channel where the file was shared.
        message (str): The message to post after deleting the file.
    """
    try:
        # Delete the file
        response = client.files_delete(file=file_id)

        if response["ok"]:
            logger.info(f"File {file_id} deleted successfully.")

            # Send a notification message to the channel
            try:
                notify_response = client.chat_postMessage(
                    channel=channel_id, text=message
                )
                if notify_response["ok"]:
                    logger.info(f"Notification message sent to channel {channel_id}.")
                else:
                    logger.error(
                        f"Failed to send notification: {notify_response['error']}"
                    )
            except SlackApiError as notify_error:
                logger.error(
                    f"Slack API Error while notifying: {notify_error.response['error']}"
                )
        else:
            logger.error(f"Failed to delete file: {response['error']}")
    except SlackApiError as e:
        logger.error(f"Slack API Error: {e.response['error']}")
