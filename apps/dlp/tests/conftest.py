import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.dlp.models import Pattern


@pytest.fixture
def pattern_credit_card():
    """Fixture for creating a credit card pattern."""
    return Pattern.objects.create(name="Credit Card", regex=r"\d{4}-\d{4}-\d{4}-\d{4}")


@pytest.fixture
def pattern_email():
    """Fixture for creating an email pattern."""
    return Pattern.objects.create(
        name="Email", regex=r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    )


@pytest.fixture
def pattern_phone():
    return Pattern.objects.create(
        name="Phone",
        regex=r"\b\+?[1-9]\d{0,2}[-.\s]?\(?\d{2,3}\)?[-.\s]\d{3}[-.\s]\d{4}\b",
    )


@pytest.fixture
def create_patterns(pattern_email, pattern_credit_card, pattern_phone):
    """
    Fixture to create test patterns in the database.
    """
    return pattern_email, pattern_credit_card, pattern_phone


@pytest.fixture
def client():
    """Fixture for the API client."""
    return APIClient()


@pytest.fixture
def slack_event_url():
    """Fixture for the Slack event URL."""
    return reverse("dlp:slack_event")  # Ensure the URL name matches


@pytest.fixture
def mock_logger_info(mocker):
    """Mock the logger.info method for SlackEventView."""
    return mocker.patch("apps.dlp.views.logger.info")


@pytest.fixture
def mock_logger_debug(mocker):
    """Mock the logger.debug method for SlackEventView."""
    return mocker.patch("apps.dlp.views.logger.debug")
