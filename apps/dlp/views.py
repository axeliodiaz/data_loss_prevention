import logging

from django.http import HttpResponseNotAllowed
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dlp.constants import (
    EVENT_CALLBACK,
    EVENT_TYPE_MESSAGE,
    SLACK_BLOCKING_MESSAGE,
)
from apps.dlp.models import Pattern
from apps.dlp.serializers import DetectedMessageSerializer
from apps.dlp.serializers import PatternSerializer
from apps.dlp.services import (
    scan_message,
    create_detected_messages,
    process_file,
    replace_message,
    delete_file_and_notify,
)

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

            if event.get("type") == EVENT_TYPE_MESSAGE:
                message = event.get("text")

                logger.info(f"Message received: {message}")
                channel_id = event.get("channel", "")
                ts = event.get("ts", "")

                if "files" in event:
                    for file in event["files"]:
                        file_id = file["id"]
                        file_content, matches = process_file(file_id)
                        if matches:
                            # Create DetectedMessage objects in bulk
                            create_detected_messages(
                                message=file_content, patterns=matches
                            )
                            # Replace the message on Slack
                            delete_file_and_notify(
                                channel_id=channel_id,
                                file_id=file_id,
                            )
                else:
                    if message is None:
                        logger.warning("Received an event with no message text.")
                        return
                    matches = scan_message(message=message)
                    if matches:
                        # Create DetectedMessage objects in bulk
                        create_detected_messages(message=message, patterns=matches)
                        # Replace the message on Slack
                        replace_message(
                            channel_id=channel_id,
                            ts=ts,
                            new_message=SLACK_BLOCKING_MESSAGE,
                        )
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


class PatternListAPIView(APIView):
    """
    API endpoint to retrieve all patterns.
    """

    def get(self, request):
        patterns = Pattern.objects.all()
        serializer = PatternSerializer(patterns, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DetectedMessageCreateAPIView(APIView):
    """
    API endpoint to save detected messages.
    """

    def post(self, request):
        serializer = DetectedMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
