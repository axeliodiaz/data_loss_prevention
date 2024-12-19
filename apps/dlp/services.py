import re

from typing import List
from apps.dlp.models import DetectedMessage, Pattern


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
