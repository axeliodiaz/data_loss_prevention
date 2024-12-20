import boto3

sqs = boto3.client(
    "sqs",
    endpoint_url="http://localhost:9324",
    region_name="us-east-1",
    aws_access_key_id="fake_access_key",
    aws_secret_access_key="fake_secret_key",
)

queue_name = "dlp-queue"
response = sqs.create_queue(QueueName=queue_name)

print(f"Queue URL: {response['QueueUrl']}")
