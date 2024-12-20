import logging
import requests
import re

BASE_URL = "http://django-backend-url/api/dlp"

logger = logging.getLogger(__name__)


async def fetch_patterns():
    """
    Fetch patterns from the backend API.
    """
    try:
        response = requests.get(f"{BASE_URL}/patterns/")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch patterns: {e}")
        return []


async def send_detected_message(content: str, pattern_id: str):
    """
    Send detected message to the backend API.
    """
    payload = {"content": content, "pattern": pattern_id}
    try:
        response = requests.post(f"{BASE_URL}/detected-messages/", json=payload)
        response.raise_for_status()
        logger.info("Detected message sent successfully.")
    except requests.RequestException as e:
        logger.error(f"Failed to send detected message: {e}")


async def process_file(file_content: str):
    """
    Process a file, detect patterns, and save matches.
    """
    logger.info(f"Processing file: {file_content}")

    patterns = await fetch_patterns()

    matches = []
    for pattern in patterns:
        if re.search(pattern["regex"], file_content):
            logger.info(f"Match found: {pattern['name']}")
            matches.append(pattern)

    # Enviar coincidencias detectadas al backend
    for match in matches:
        await send_detected_message(content=file_content, pattern_id=match["id"])


async def process_message(message: str):
    """
    Process a message, detect patterns, and save matches.
    """
    logger.info(f"Processing message: {message}")

    patterns = await fetch_patterns()

    matches = []
    for pattern in patterns:
        if re.search(pattern["regex"], message):
            logger.info(f"Match found: {pattern['name']}")
            matches.append(pattern)

    for match in matches:
        await send_detected_message(content=message, pattern_id=match["id"])


TASKS = {
    "process_file": process_file,
    "process_message": process_message,
}