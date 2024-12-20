import json
import logging

import asyncio

from manager import Manager
from tasks import TASKS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class DummySQSQueue(Manager):
    async def _get_messages(self):
        """Simulate fetching messages from a queue."""
        await asyncio.sleep(1)
        return [
            {
                "Body": json.dumps(
                    {"task": "process_file", "args": ("Sample content",), "kwargs": {}}
                )
            },
            {
                "Body": json.dumps(
                    {
                        "task": "process_message",
                        "args": ("Hello, world!",),
                        "kwargs": {},
                    }
                )
            },
        ]


if __name__ == "__main__":
    queue_name = "dummy-queue"
    manager = DummySQSQueue(queue_name=queue_name, tasks=TASKS)

    asyncio.run(manager.main())
