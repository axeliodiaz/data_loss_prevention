from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json


class SlackEventView(APIView):
    def post(self, request, *args, **kwargs):
        _data = request.data
        return Response({"status": "received"}, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        return Response(
            {"error": "method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
