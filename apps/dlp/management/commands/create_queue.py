from django.core.management.base import BaseCommand
import boto3
from django.conf import settings


class Command(BaseCommand):
    help = "Create SQS queue if it does not exist"

    def handle(self, *args, **kwargs):
        sqs = boto3.client(
            "sqs",
            endpoint_url=settings.AWS_SQS_ENDPOINT_URL,
            region_name=settings.AWS_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        queue_name = settings.AWS_SQS_QUEUE_NAME
        try:
            response = sqs.create_queue(QueueName=queue_name)
            self.stdout.write(f"Queue '{queue_name}' created successfully.")
        except sqs.exceptions.QueueAlreadyExists:
            self.stdout.write(f"Queue '{queue_name}' already exists.")
        except Exception as e:
            self.stderr.write(f"Failed to create queue: {e}")
