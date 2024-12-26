import os
import django
import boto3
from django.conf import settings

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data_loss_prevention.settings")
django.setup()


def create_queue(queue_name):
    sqs = boto3.client(
        "sqs",
        endpoint_url=settings.AWS_SQS_ENDPOINT_URL,
        region_name=settings.AWS_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    response = sqs.create_queue(QueueName=queue_name)
    print(f"Queue {queue_name} created: {response['QueueUrl']}")


if __name__ == "__main__":
    create_queue(settings.AWS_SQS_QUEUE_NAME)
