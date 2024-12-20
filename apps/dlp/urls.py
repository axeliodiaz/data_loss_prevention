from django.urls import path
from apps.dlp.views import (
    SlackEventView,
    PatternListAPIView,
    DetectedMessageCreateAPIView,
)

urlpatterns = [
    path("slack/events/", SlackEventView.as_view(), name="slack_event"),
    path("patterns/", PatternListAPIView.as_view(), name="pattern-list"),
    path(
        "detected-messages/",
        DetectedMessageCreateAPIView.as_view(),
        name="detected-message-create",
    ),
]
