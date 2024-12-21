import logging
import urllib.parse
import re
import aiohttp

from django.conf import settings
from django.urls import reverse

# Construct URLs for backend API endpoints
detected_messages_url = urllib.parse.urljoin(
    settings.BASE_URL, reverse("dlp:detected-message-create")
)
pattern_url = urllib.parse.urljoin(settings.BASE_URL, reverse("dlp:pattern-list"))

logger = logging.getLogger(__name__)


async def fetch_patterns():
    """
    Fetch patterns from the backend API.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(pattern_url) as response:
                response.raise_for_status()
                patterns = await response.json()
                logger.info(f"Fetched {len(patterns)} patterns.")
                return patterns
        except aiohttp.ClientError as e:
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
                logger.info("Detected message sent successfully.")
        except aiohttp.ClientError as e:
            logger.error(f"Failed to send detected message: {e}")


async def process_file(file_content: str):
    """
    Process a file, detect patterns, and save matches.

    Args:
        file_content (str): The content of the file to process.
    """
    logger.info(f"Processing file: {file_content}")

    # Fetch patterns from the API
    patterns = await fetch_patterns()

    matches = []
    for pattern in patterns:
        if re.search(pattern["regex"], file_content):
            logger.info(f"Match found: {pattern['name']}")
            matches.append(pattern)

    # Send detected matches to the backend
    for match in matches:
        await send_detected_message(content=file_content, pattern_id=match["id"])

    if matches:
        logger.info(f"File processing completed with {len(matches)} matches found.")
    else:
        logger.info("No matches found in the file.")


async def process_message(message: str):
    """
    Process a message, detect patterns, and save matches.

    Args:
        message (str): The message text to process.
    """
    logger.info(f"Processing message: {message}")

    # Fetch patterns from the API
    patterns = await fetch_patterns()

    matches = []
    for pattern in patterns:
        if re.search(pattern["regex"], message):
            logger.info(f"Match found: {pattern['name']}")
            matches.append(pattern)

    # Send detected matches to the backend
    for match in matches:
        await send_detected_message(content=message, pattern_id=match["id"])

    if matches:
        logger.info(f"Message processing completed with {len(matches)} matches found.")
    else:
        logger.info("No matches found in the message.")


# Task dictionary for distributed task processing
TASKS = {
    "process_file": process_file,
    "process_message": process_message,
}
