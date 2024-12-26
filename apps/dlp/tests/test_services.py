import json
import pytest
from unittest.mock import patch, MagicMock
from apps.dlp.services import send_to_sqs


@pytest.fixture
def sqs_client_mock():
    """
    Fixture to mock boto3 SQS client.
    """
    with patch("apps.dlp.services.boto3.client") as mock_client:
        yield mock_client


@patch("apps.dlp.services.logger")
def test_send_to_sqs_success(mock_logger, sqs_client_mock):
    """
    Test send_to_sqs successfully sends a message to SQS.
    """
    # Configure the mocked SQS client
    mock_sqs = sqs_client_mock.return_value
    mock_sqs.send_message.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "MessageId": "12345",
    }

    task_name = "process_message"
    args = ["arg1", "arg2"]
    kwargs = {"key1": "value1"}

    # Adjust URL to match the actual test environment
    queue_url = "http://elasticmq:9324/000000000000/dlp-tasks"

    # Call the function
    send_to_sqs(task_name=task_name, args=args, kwargs=kwargs)

    # Assertions for logger
    mock_logger.info.assert_any_call(
        f"Sending message to SQS: {{'task': '{task_name}', 'args': {args}, 'kwargs': {kwargs}}}"
    )
    mock_logger.info.assert_any_call(
        "Message sent to SQS successfully. Response: {'ResponseMetadata': {'HTTPStatusCode': 200}, 'MessageId': '12345'}"
    )

    # Assertions for SQS client
    sqs_client_mock.assert_called_once_with(
        "sqs",
        endpoint_url="http://sqs:9324",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    mock_sqs.send_message.assert_called_once_with(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "task": task_name,
                "args": args,
                "kwargs": kwargs,
            }
        ),
    )


@patch("apps.dlp.services.logger")
def test_send_to_sqs_failure(mock_logger, sqs_client_mock):
    """
    Test send_to_sqs handles an error during the SQS operation.
    """
    # Simulate an exception in SQS client
    mock_sqs = sqs_client_mock.return_value
    mock_sqs.send_message.side_effect = Exception("SQS error")

    task_name = "process_file"
    args = []
    kwargs = {"file_id": "F123456"}

    # Adjust URL to match the actual test environment
    queue_url = "http://elasticmq:9324/000000000000/dlp-tasks"

    # Call the function
    send_to_sqs(task_name=task_name, args=args, kwargs=kwargs)

    # Assertions for logger
    mock_logger.info.assert_any_call(
        f"Sending message to SQS: {{'task': '{task_name}', 'args': {args}, 'kwargs': {kwargs}}}"
    )
    mock_logger.error.assert_any_call("Failed to send message to SQS. Error: SQS error")

    # Assertions for SQS client
    sqs_client_mock.assert_called_once_with(
        "sqs",
        endpoint_url="http://sqs:9324",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    mock_sqs.send_message.assert_called_once_with(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "task": task_name,
                "args": args,
                "kwargs": kwargs,
            }
        ),
    )
