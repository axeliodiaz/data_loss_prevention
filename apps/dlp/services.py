import json
import logging

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


def send_to_sqs(task_name, args=None, kwargs=None):
    """Send a task to SQS."""
    try:
        sqs = boto3.client(
            "sqs",
            endpoint_url=settings.AWS_SQS_ENDPOINT_URL,
            region_name=settings.AWS_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        queue_url = settings.AWS_SQS_QUEUE_URL
        message = {
            "task": task_name,
            "args": args or [],
            "kwargs": kwargs or {},
        }

        logger.info(f"Sending message to SQS: {message}")

        response = sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
        logger.info(f"Message sent to SQS successfully. Response: {response}")
    except Exception as e:
        logger.error(f"Failed to send message to SQS. Error: {e}")
