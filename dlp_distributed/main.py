import asyncio
from manager import Manager
from tasks import process_message, process_file

TASKS = {
    "process_message": process_message,
    "process_file": process_file,
}


async def main():
    manager = Manager(queue_name="dlp_tasks", tasks=TASKS)
    await manager.main()


if __name__ == "__main__":
    asyncio.run(main())
