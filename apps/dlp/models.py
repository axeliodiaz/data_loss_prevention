from django.db import models
from model_utils.models import UUIDModel, SoftDeletableModel, TimeStampedModel


class Pattern(UUIDModel, SoftDeletableModel):
    name = models.CharField(max_length=100)
    regex = models.TextField()

    def __str__(self):
        return self.name


class DetectedMessage(UUIDModel, TimeStampedModel):
    content = models.TextField()
    pattern = models.ForeignKey(Pattern, on_delete=models.CASCADE)

    def __str__(self):
        return f"Message: {self.content[:20]} - Pattern: {self.pattern.name}"
