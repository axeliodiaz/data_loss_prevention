import logging

from django.http import HttpResponseNotAllowed
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.dlp.constants import EVENT_CALLBACK, EVENT_TYPE_MESSAGE, EVENT_TYPE_FILE
from apps.dlp.services import scan_message, create_detected_messages, process_file

logger = logging.getLogger(__name__)


class SlackEventView(APIView, HttpResponseNotAllowed):
    def get_slack_challenge(self, data):
        """Extract the Slack challenge token from the payload."""
        return data.get("challenge")

    def check_event_callback(self, data):
        """Handle Slack event callbacks."""
        event_type = data.pop("type", None)

        if event_type and event_type == EVENT_CALLBACK:
            event = data.get("event", {})
            message = event.get("text")

            if event.get("type") == EVENT_TYPE_FILE:
                file_id = event.get("file_id")
                process_file(file_id)

            if event.get("type") == EVENT_TYPE_MESSAGE:
                logger.info(f"Message received: {message}")
                matches = scan_message(message=message)

                if matches:
                    # Create DetectedMessage objects in bulk
                    create_detected_messages(message=message, patterns=matches)
            else:
                logger.debug(f"Unhandled event type: {event.get('type')}")
        return data

    def post(self, request, *args, **kwargs):
        """Handle POST requests from Slack."""
        response_data = {"status": "received"}
        data = request.data
        _event_callback = self.check_event_callback(data=data)
        challenge_data = self.get_slack_challenge(data)
        if challenge_data:
            logger.info("Slack challenge detected in the payload.")
            response_data["challenge"] = challenge_data
        return Response(data=response_data, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        """Disallow GET requests."""
        return HttpResponseNotAllowed(permitted_methods="POST")
