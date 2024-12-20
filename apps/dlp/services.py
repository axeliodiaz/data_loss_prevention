import logging
import re
from typing import List

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from apps.dlp.models import DetectedMessage, Pattern
from data_loss_prevention.settings import SLACK_BOT_TOKEN

logger = logging.getLogger(__name__)


client = WebClient(token=SLACK_BOT_TOKEN)


def scan_message(message: str):
    """
    Scans a message for matches against a list of patterns.

    Args:
        message (str): The message to scan.
        patterns (list): List of objects with `regex` attributes.

    Returns:
        list: List of matching patterns.
    """
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


def process_file(file_id) -> list:
    """Get the file from Slack to be analized."""
    matches = []
    file_content = get_file_info(file_id=file_id)

    if file_content:
        # Analize the file
        matches = scan_message(file_content)

    return matches


def create_detected_messages(
    message: str, patterns: List[Pattern]
) -> List[DetectedMessage]:
    """
    Create DetectedMessage objects for each detected pattern using bulk_create.

    Args:
        message (str): The content of the detected message.
        patterns (List[Pattern]): List of matching Pattern instances.

    Returns:
        List[DetectedMessage]: A list of created DetectedMessage instances.
    """
    detected_messages = [
        DetectedMessage(content=message, pattern=pattern) for pattern in patterns
    ]
    DetectedMessage.objects.bulk_create(detected_messages)

    logger.info(f"Detected message: {message}")
    return detected_messages
