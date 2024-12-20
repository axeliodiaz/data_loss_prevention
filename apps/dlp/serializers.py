from rest_framework import serializers
from apps.dlp.models import Pattern, DetectedMessage


class PatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pattern
        fields = ("id", "name", "regex")


class DetectedMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectedMessage
        fields = ("id", "content", "pattern", "created", "modified")
