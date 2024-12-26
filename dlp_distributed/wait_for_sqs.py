import boto3
import os
import time
from botocore.exceptions import ClientError, EndpointConnectionError


def wait_for_sqs():
    queue_url = os.getenv("AWS_SQS_QUEUE_URL", "http://sqs:9324/000000000000/dlp-tasks")
    endpoint_url = os.getenv("AWS_SQS_ENDPOINT_URL", "http://sqs:9324")
    region_name = os.getenv("AWS_REGION_NAME", "us-east-1")
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "test")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
    max_retries = int(os.getenv("SQS_MAX_RETRIES", 10))
    retry_interval = int(os.getenv("SQS_RETRY_INTERVAL", 5))

    sqs = boto3.client(
        "sqs",
        endpoint_url=endpoint_url,
        region_name=region_name,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    retries = 0
    print(f"Waiting for SQS queue {queue_url} to be ready...")

    while retries < max_retries:
        try:
            sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])
            print(f"SQS queue {queue_url} is ready.")
            return
        except ClientError as e:
            print(f"Attempt {retries + 1}/{max_retries}: Queue not available. {e}")
        except EndpointConnectionError as e:
            print(
                f"Attempt {retries + 1}/{max_retries}: Unable to connect to endpoint. {e}"
            )
        retries += 1
        time.sleep(retry_interval)

    raise RuntimeError(
        f"SQS queue {queue_url} is not available after {max_retries} retries."
    )


if __name__ == "__main__":
    try:
        wait_for_sqs()
    except RuntimeError as e:
        print(e)
        exit(1)
