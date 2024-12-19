from django.urls import path
from apps.dlp.views import SlackEventView

urlpatterns = [
    path('slack/events/', SlackEventView.as_view(), name='slack_event'),
]