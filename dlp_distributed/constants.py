import os

AWS_REGION_NAME = os.environ.get("AWS_REGION_NAME", "us-east-1")
AWS_SQS_ENDPOINT_URL = os.environ.get("AWS_SQS_ENDPOINT_URL", "http://sqs:9324")
AWS_SQS_QUEUE_URL = os.environ.get(
    "AWS_SQS_QUEUE_URL", "http://elasticmq:9324/000000000000/dlp-tasks"
)
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "fake_access_key")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "fake_secret_key")
BASE_URL = os.getenv("BASE_URL", "")
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
