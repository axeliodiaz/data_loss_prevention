import asyncio
import json
import logging

from aiobotocore.session import AioSession
from slack_sdk.errors import SlackApiError

from constants import (
    AWS_SQS_QUEUE_URL,
    AWS_REGION_NAME,
    AWS_SQS_ENDPOINT_URL,
)
from tasks import process_message, process_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQSManager:
    def __init__(self):
        """
        Initialize the SQSManager with a session and queue URL.
        """
        self.session = AioSession()
        self.queue_url = AWS_SQS_QUEUE_URL

    async def _get_messages(self):
        """
        Fetch messages from the SQS queue.

        Returns:
            list: A list of messages retrieved from the queue.
        """
        async with self.session.create_client(
            "sqs",
            region_name=AWS_REGION_NAME,
            endpoint_url=AWS_SQS_ENDPOINT_URL,
        ) as client:
            response = await client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=10,
            )
            return response.get("Messages", [])

    async def _delete_message(self, receipt_handle):
        """
        Delete a message from the SQS queue.

        Args:
            receipt_handle (str): The receipt handle of the message to delete.
        """
        async with self.session.create_client(
            "sqs",
            region_name=AWS_REGION_NAME,
            endpoint_url=AWS_SQS_ENDPOINT_URL,
        ) as client:
            try:
                await client.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=receipt_handle,
                )
            except SlackApiError as e:
                logger.error(f"Slack API Error: {e.response['error']}")
            else:
                logger.info(f"Deleted message with ReceiptHandle: {receipt_handle}")

    async def _process_message(self, message):
        """
        Process a single message from the SQS queue.

        Args:
            message (dict): The message to process.
        """
        body = json.loads(message["Body"])
        task_name = body.get("task")
        kwargs = body.get("kwargs", {})

        logger.info(f"Processing task: {task_name} with kwargs: {kwargs}")

        try:
            if task_name == "process_file":
                await process_file(**kwargs)
            elif task_name == "process_message":
                await process_message(**kwargs)
            else:
                logger.error(f"Unknown task: {task_name}")

            await self._delete_message(message["ReceiptHandle"])
        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    async def main(self):
        """
        Main loop to continuously process messages from the queue.
        """
        logger.info("Starting SQS task manager...")
        try:
            while True:
                messages = await self._get_messages()
                if messages:
                    tasks = [self._process_message(msg) for msg in messages]
                    await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("SQS task manager shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
