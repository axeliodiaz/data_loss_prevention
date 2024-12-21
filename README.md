# Data Loss Prevention Project

This project implements a Data Loss Prevention (DLP) system to analyze messages and files for detecting sensitive patterns like emails, credit card numbers, and phone numbers.

## Project Structure

```plaintext
.
├── Dockerfile
├── README.md
├── apps
│   ├── __init__.py
│   └── dlp
│       ├── __init__.py
│       ├── admin.py
│       ├── apps.py
│       ├── constants.py
│       ├── fixtures
│       │   └── initial_patterns.json
│       ├── manager.py
│       ├── migrations
│       │   ├── 0001_initial.py
│       │   └── __init__.py
│       ├── models.py
│       ├── serializers.py
│       ├── services.py
│       ├── tests
│       │   ├── __init__.py
│       │   ├── conftest.py
│       │   ├── test_services.py
│       │   └── test_views.py
│       ├── urls.py
│       └── views.py
├── create_queue.py
├── data_loss_prevention
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── dlp_distributed
│   ├── Dockerfile
│   ├── __init__.py
│   ├── main.py
│   ├── manager.py
│   ├── requirements.txt
│   ├── tasks.py
│   └── tests
│       ├── __init__.py
│       └── test_tasks.py
├── docker-compose.yml
├── manage.py
├── pytest.ini
└── requirements
    ├── base.txt
    └── local.txt
```

## Prerequisites

- Docker and Docker Compose installed.

## Setup Instructions

1. Clone the Repository
```bash
git clone <repo_url>
cd <repo_name>
```

2. Set Up Environment Variables
Create a `.env` file in the root directory with the following variables:

```dotenv
SECRET_KEY=<django_secret_key>
DEBUG=True
DB_NAME=dlp_project
DB_USER=admin
DB_PASSWORD=password
DB_HOST=db
DB_PORT=3306
SLACK_BOT_TOKEN=<your_slack_bot_token>
SLACK_USER_TOKEN=<your_slack_user_token>
AWS_SQS_ENDPOINT_URL=http://elasticmq:9324
AWS_REGION_NAME=us-east-1
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
BASE_URL=http://127.0.0.1:8000
```

## Running the Project

1. Build and Run the Services

Use Docker Compose to build and start the services:

```bash
docker-compose up --build
```

This will:
- Start the MySQL database.
- Start the Django backend.
- Start the ElasticMQ service for local SQS emulation.

2. Access the Application

- Django Admin: `http://127.0.0.1:8000/admin`
- API Base URL: `http://127.0.0.1:8000/api/`

3. Create SQS Queue
Run the script create_queue.py to create the required queue (dlp_tasks):
```bash
docker exec -it django_backend python create_queue.py
```
This script will connect to ElasticMQ (or AWS SQS in production) and create the queue.

## Post-Setup

1. Apply Database Migrations

Run the following command to apply migrations:
```bash
docker exec -it django_backend python manage.py migrate
```

2. Create a Superuser

Create a superuser for the admin panel:
```bash
docker exec -it django_backend python manage.py createsuperuser
```

3. Populate Patterns

Load initial patterns into the database:
### Load Initial Patterns

```bash
docker exec -it django_backend python manage.py loaddata apps/dlp/fixtures/initial_patterns.json
```

## Testing

1. Run Backend Tests

Run the backend tests inside the Django container:
```bash
docker exec -it django_backend pytest 
```

This will include `dlp` tests and `dlp_distributed` tests.

## Important Routes
```
/api/detected-messages/	apps.dlp.views.DetectedMessageCreateAPIView	dlp:detected-message-create
/api/patterns/	apps.dlp.views.PatternListAPIView	dlp:pattern-list
/api/slack/events/	apps.dlp.views.SlackEventView	dlp:slack_event
```

## Dockerfile Overview
The Dockerfile is used to build the entire project:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements/base.txt requirements/local.txt ./requirements/
RUN pip install --no-cache-dir -r requirements/local.txt
COPY . /app
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## Slack Integration Features

### Message and File Management

The DLP system integrates with Slack to detect and block messages or files that contain sensitive information. The following features are implemented:

1. **Message Replacement**:
   - When a message containing sensitive information is detected, the system replaces it with a blocking message:
     ```
     Message was blocked due to containing sensitive information.
     ```

   - **Functionality**:
     - The function `replace_message` is used to update messages in Slack.
     - Requires the `chat:write` permission for the bot token or `chat:write:user` for user tokens.

2. **File Deletion and Notification**:
   - Files containing sensitive information are deleted, and a notification message is posted in the Slack channel.
     - Example notification:
       ```
       File containing sensitive information has been removed.
       ```

   - **Functionality**:
     - The function `delete_file_and_notify` handles file deletion and posting the notification.
     - Requires the `files:write` permission for the user token.

### Required Permissions

To enable these features, ensure that your bot or user token has the following permissions:
- `chat:write`
- `files:write`
- `channels:history`
- `groups:history`
- `im:history`
- `mpim:history`

### How It Works

1. **Message Replacement Flow**:
   - Messages are scanned using predefined patterns.
   - If sensitive information is detected:
     - A `DetectedMessage` object is created for logging purposes.
     - The message is replaced using the `replace_message` function.

2. **File Deletion Flow**:
   - Files uploaded to Slack are scanned for sensitive content.
   - If sensitive information is detected:
     - The file is deleted using the `delete_file_and_notify` function.
     - A notification message is posted in the same Slack channel.

### Configuration

Update your environment variables to include:
- `SLACK_BOT_TOKEN`: Token for the bot with appropriate permissions.
- `SLACK_USER_TOKEN`: User token (required for file deletion).
- `SLACK_BLOCKING_MESSAGE`: Default blocking message for messages with sensitive content.
- `SLACK_BLOCKING_FILE`: Default blocking message for deleted files.

### Usage

#### Replace a Message
The `replace_message` function can be used as follows:
```python
from apps.dlp.services import replace_message

replace_message(
    channel_id="C123456",
    ts="1626181234.000200",
    new_message="Message was blocked due to containing sensitive information.",
)
```

#### Delete a File and Notify
The `delete_file_and_notify function can be used as follows:
```python
from apps.dlp.services import delete_file_and_notify

delete_file_and_notify(
    file_id="file123",
    channel_id="C123456",
    message="A file containing sensitive information has been removed.",
)
```

##	Notes
1.	Message Queue:
ElasticMQ is used for local SQS emulation. Ensure it is running and accessible at http://elasticmq:9324.
2. Slack Integration:
Configure Slack events API and provide the bot token in .env.
3.	Testing:
Ensure all containers are running before executing tests.