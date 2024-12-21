# Check Point Engineer Assigment

This assignment is an example of the daily work at Check Point HEC Team, it pretends to evaluate your skills 
but also your ability to addapt to a specific set of tools.

We expect you to share a GitHub repo with your implementation to be reviewed for us, once the review is done 
we kindly ask you to delete or make your repo private so we can keep using the same assignment in the future.

Create a system that secures the organization communication channels but listening to files and messages 
flowing in and scanning them using a set of security tools.

At its first version, the system should only use slack as its communication channel input and a 
Data Loss Prevention tool that will be developed in house, but we wrapped and used like anyother external 
security tool.

<p align="center">
  <img
       src="https://gist.github.com/user-attachments/assets/ba146955-9f0f-4378-b1be-acb2515476bf"
       alt="check_point_arch"
       style="height:600px;"
  />
</p>

## Asignment

1. Open a free Slack account https://slack.com/pricing/free
2. Use Slack events api https://api.slack.com/events-api to listen to messages. It is very important you implement a webhoook to listen to the events from Slack, this will be evaluated.
3. Create a simple Data Loss Prevention tool that given a file, open its content and try to look for patterns (for example: a credit card number), using a list of regular expressions, make it possible to manage those patterns using Django admin.
4. Use Django admin to also show messages that were caught by the DLP tool, show the message, its content and the pattern that caught it.
6. Create a container using the piece of code below to implement distributed tasks to search for leaks in files and messages. It is important the code in this container is asynchronus.
7. Expose API services in Django to return the patterns and save the found matches, consume from the DLP container.
8. Write unit tests where consider appropriate.
9. Write a README about how to run your project.
10. BONUS: add an action flow, so when DLP is giving a negative response, saying that the message contains a leak, the system should switch the message on slack with a message saying that the original message was blocked.

## Asynchronus Distributed Tasks

Use Python 3.x to implement the in house DLP, the idea is to use the next code to implement the DLP container, 
note that it still requires to implement getting the messages from SQS **in an async way**:

```python
import asyncio
import json


class Manager:

    def __init__(self, queue_name: str, tasks: dict):
        self.loop = asyncio.get_event_loop()
        self.queue = queue_name
        self.tasks = tasks
    
    async def _get_messages(self):
        """Read and pop messages from SQS queue
        """
        raise NotImplementedError

    async def main(self):
        """For a given task:
        >>> async def say(something):
                pass

        Messages from queue are expected to have the format:
        >>> message = dict(task='say', args=('something',), kwargs={})
        >>> message = dict(task='say', args=(), kwargs={'something': 'something else'})
        """

        while True:
            messages = await self._get_messages()
            for message in messages:
                body = json.loads(message['Body'])

                task_name = body.get('task')
                args = body.get('args', ())
                kwargs = body.get('kwargs', {})

                task = self.tasks.get(task_name)
                self.loop.create_task(task(*args, **kwargs))
            await asyncio.sleep(1)
```

## Tools

Do not use AWS, make use of images for the databases.

* Python 3: https://www.python.org/
* Git: https://git-scm.com/
* Docker: https://www.docker.com/
* Docker Compose: https://docs.docker.com/compose
* Django: https://www.djangoproject.com/
* MySQL: https://www.mysql.com/
* SQS: https://aws.amazon.com/sqs/