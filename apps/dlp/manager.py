import boto3
import asyncio
import json


class Manager:
    def __init__(self, queue_name: str, tasks: dict):
        self.loop = asyncio.get_event_loop()
        self.queue_name = queue_name
        self.tasks = tasks

        self.sqs = boto3.client(
            "sqs",
            endpoint_url="http://sqs:9324",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

    async def _get_messages(self):
        """Read and pop messages from SQS queue."""
        response = self.sqs.receive_message(
            QueueUrl=self.queue_name,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=10,
        )
        return response.get("Messages", [])

    async def main(self):
        """Main loop to fetch messages and execute tasks."""
        while True:
            messages = await self._get_messages()
            for message in messages:
                body = json.loads(message["Body"])

                task_name = body.get("task")
                args = body.get("args", ())
                kwargs = body.get("kwargs", {})

                task = self.tasks.get(task_name)
                if task:
                    self.loop.create_task(task(*args, **kwargs))
                else:
                    print(f"Task '{task_name}' not found.")

                self.sqs.delete_message(
                    QueueUrl=self.queue_name,
                    ReceiptHandle=message["ReceiptHandle"],
                )
            await asyncio.sleep(1)
