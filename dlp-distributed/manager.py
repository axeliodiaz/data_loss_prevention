import asyncio
import json


class Manager:
    def __init__(self, queue_name: str, tasks: dict):
        self.loop = asyncio.get_event_loop()
        self.queue = queue_name
        self.tasks = tasks
        self.active_tasks = set()  # Conjunto para rastrear las tareas activas

    async def _get_messages(self):
        """Simulate reading and popping messages from SQS queue."""
        raise NotImplementedError("You need to implement _get_messages.")

    async def main(self):
        """Main loop to process messages."""
        try:
            while True:
                messages = await self._get_messages()
                for message in messages:
                    body = json.loads(message["Body"])

                    task_name = body.get("task")
                    args = body.get("args", ())
                    kwargs = body.get("kwargs", {})

                    task = self.tasks.get(task_name)
                    if task:
                        # Crear y rastrear la tarea
                        task_coro = task(*args, **kwargs)
                        task_obj = self.loop.create_task(task_coro)
                        self.active_tasks.add(task_obj)
                        task_obj.add_done_callback(self.active_tasks.discard)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            # Esperar a que todas las tareas activas terminen antes de cerrar
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
