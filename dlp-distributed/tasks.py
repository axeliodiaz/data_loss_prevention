import logging

logger = logging.getLogger(__name__)


async def process_file(file_content: str):
    logger.info(f"Processing file: {file_content}")


async def process_message(message: str):
    logger.info(f"Processing message: {message}")


# Mapa de tareas
TASKS = {
    "process_file": process_file,
    "process_message": process_message,
}
