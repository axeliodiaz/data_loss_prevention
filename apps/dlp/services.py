import logging
import re

from typing import List

from django.contrib.sites import requests

from apps.dlp.models import DetectedMessage, Pattern
from data_loss_prevention.settings import SLACK_BOT_TOKEN


logger = logging.getLogger(__name__)


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


def process_file(self, file_id):
    """Get the file from Slack to be analized."""
    response = requests.get(
        "https://slack.com/api/files.info",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        params={"file": file_id},
    )

    file_info = response.json()

    if file_info.get("ok"):
        file_url = file_info["file"]["url_private"]

        # Download the file
        file_content = requests.get(
            file_url, headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        ).content

        # Analize the file
        scan_file(file_content)

    else:
        logger.debug(f"Error getting info from file: {file_info}")


def scan_file(file_content: bytes) -> list:
    """
    Scans the content of a file for sensitive patterns by reusing `scan_message`.

    Args:
        file_content (bytes): The file content as bytes.

    Returns:
        list: List of matching patterns found in the file.
    """
    # Convert file content to string
    try:
        text_content = file_content.decode("utf-8")
    except UnicodeDecodeError:
        logger.debug("Could not decode the file content as text.")
        return []

    # Reuse scan_message to search for matches
    matches = scan_message(text_content)
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
    return detected_messages
