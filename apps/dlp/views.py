import logging
from django.http import HttpResponseNotAllowed
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


logger = logging.getLogger(__name__)


class SlackEventView(APIView, HttpResponseNotAllowed):
    def get_slack_challenge(self, data):
        return data.get("challenge")

    def check_event_callback(self, data):
        type = data.pop("type", None)
        if type and type == "event_callback":
            event = data.get("event", {})
            message = "asdasd"
            print(message)
            if event.get("type") == "message":
                logger.info(f"Message received: {event.get('text')}")
            else:
                logger.debug(f"Unhandled event type: {event.get('type')}")
        return data

    def post(self, request, *args, **kwargs):
        response_data = {"status": "received"}
        data = request.data
        _event_callback = self.check_event_callback(data=data)
        challenge_data = self.get_slack_challenge(data)
        if challenge_data:
            logger.info("Slack challenge detected in the payload.")
            response_data["challenge"] = challenge_data
        return Response(data=response_data, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(permitted_methods="POST")
