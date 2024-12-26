import pytest
from unittest.mock import AsyncMock, patch
from manager import SQSManager
from constants import AWS_SQS_QUEUE_URL


@pytest.mark.asyncio
class TestSQSManager:
    @patch("aiobotocore.session.AioSession.create_client")
    async def test_get_messages(self, mock_create_client):
        """
        Test that _get_messages retrieves messages from the SQS queue.
        """
        mock_client = AsyncMock()
        mock_create_client.return_value.__aenter__.return_value = mock_client
        mock_client.receive_message.return_value = {
            "Messages": [{"Body": '{"task": "test_task"}', "ReceiptHandle": "abc123"}]
        }

        manager = SQSManager()
        messages = await manager._get_messages()

        assert messages == [
            {"Body": '{"task": "test_task"}', "ReceiptHandle": "abc123"}
        ]
        mock_client.receive_message.assert_called_once_with(
            QueueUrl=AWS_SQS_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=10,
        )

    @patch("aiobotocore.session.AioSession.create_client")
    async def test_delete_message(self, mock_create_client):
        """
        Test that _delete_message deletes a message from the SQS queue.
        """
        mock_client = AsyncMock()
        mock_create_client.return_value.__aenter__.return_value = mock_client

        receipt_handle = "abc123"
        manager = SQSManager()
        await manager._delete_message(receipt_handle)

        mock_client.delete_message.assert_called_once_with(
            QueueUrl=AWS_SQS_QUEUE_URL,
            ReceiptHandle=receipt_handle,
        )
