import asyncio
from manager import SQSManager

if __name__ == "__main__":
    # Instantiate the SQSManager and start the event loop
    manager = SQSManager()
    asyncio.run(manager.main())
