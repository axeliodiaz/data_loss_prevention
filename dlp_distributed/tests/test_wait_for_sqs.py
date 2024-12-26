import os
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from wait_for_sqs import wait_for_sqs


# Fixture to mock environment variables
@pytest.fixture
def mock_env():
    env_vars = {
        "AWS_SQS_QUEUE_URL": "http://sqs:9324/000000000000/dlp-tasks",
        "AWS_SQS_ENDPOINT_URL": "http://sqs:9324",
        "AWS_REGION_NAME": "us-east-1",
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "SQS_MAX_RETRIES": "3",
        "SQS_RETRY_INTERVAL": "1",
    }
    with patch.dict(os.environ, env_vars):
        yield


@patch("boto3.client")
@patch("time.sleep", return_value=None)  # Avoid actual delays
class TestWaitForSQS:
    def test_successful_connection(self, mock_sleep, mock_boto_client, mock_env):
        """
        Test when SQS queue becomes ready on the first attempt.
        """
        # Mock SQS client and get_queue_attributes response
        mock_sqs = MagicMock()
        mock_boto_client.return_value = mock_sqs

        # Call the function
        wait_for_sqs()

        # Ensure SQS client is created and the queue is queried
        mock_boto_client.assert_called_once_with(
            "sqs",
            endpoint_url="http://sqs:9324",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        mock_sqs.get_queue_attributes.assert_called_once_with(
            QueueUrl="http://sqs:9324/000000000000/dlp-tasks", AttributeNames=["All"]
        )
        mock_sleep.assert_not_called()  # No retries needed

    def test_retry_and_success(self, mock_sleep, mock_boto_client, mock_env):
        """
        Test when SQS queue becomes ready after a few retries.
        """
        # Mock SQS client and simulate failure before success
        mock_sqs = MagicMock()
        mock_sqs.get_queue_attributes.side_effect = [
            ClientError({"Error": {"Code": "QueueNotFound"}}, "GetQueueAttributes"),
            ClientError({"Error": {"Code": "QueueNotFound"}}, "GetQueueAttributes"),
            None,  # Success on the third attempt
        ]
        mock_boto_client.return_value = mock_sqs

        # Call the function
        wait_for_sqs()

        # Ensure the function retried and succeeded
        assert mock_sqs.get_queue_attributes.call_count == 3
        mock_sleep.assert_called_with(1)

    def test_exceed_max_retries(self, mock_sleep, mock_boto_client, mock_env):
        """
        Test when SQS queue is not available after the maximum number of retries.
        """
        # Mock SQS client to always raise ClientError
        mock_sqs = MagicMock()
        mock_sqs.get_queue_attributes.side_effect = ClientError(
            {"Error": {"Code": "QueueNotFound"}}, "GetQueueAttributes"
        )
        mock_boto_client.return_value = mock_sqs

        # Call the function and expect a RuntimeError
        with pytest.raises(
            RuntimeError,
            match="SQS queue http://sqs:9324/000000000000/dlp-tasks is not available after 3 retries.",
        ):
            wait_for_sqs()

        # Ensure the function retried the maximum number of times
        assert mock_sqs.get_queue_attributes.call_count == 3
        mock_sleep.assert_called_with(1)

    def test_endpoint_connection_error(self, mock_sleep, mock_boto_client, mock_env):
        """
        Test when an EndpointConnectionError occurs.
        """
        # Mock SQS client to raise EndpointConnectionError
        mock_sqs = MagicMock()
        mock_sqs.get_queue_attributes.side_effect = EndpointConnectionError(
            endpoint_url="http://sqs:9324"
        )
        mock_boto_client.return_value = mock_sqs

        # Call the function and expect a RuntimeError
        with pytest.raises(
            RuntimeError,
            match="SQS queue http://sqs:9324/000000000000/dlp-tasks is not available after 3 retries.",
        ):
            wait_for_sqs()

        # Ensure the function retried the maximum number of times
        assert mock_sqs.get_queue_attributes.call_count == 3
        mock_sleep.assert_called_with(1)
