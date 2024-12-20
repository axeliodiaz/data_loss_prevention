from django.db import models
from django.urls import reverse
from model_utils.models import UUIDModel, SoftDeletableModel, TimeStampedModel


class Pattern(UUIDModel, SoftDeletableModel):
    name = models.CharField(max_length=100)
    regex = models.TextField()

    def get_admin_url(self):
        """
        Return the URL to the admin page for this Pattern object.
        """
        return reverse("admin:dlp_pattern_change", args=[self.id])

    def __str__(self):
        return self.name


class DetectedMessage(UUIDModel, TimeStampedModel):
    content = models.TextField()
    pattern = models.ForeignKey(Pattern, on_delete=models.CASCADE)

    def __str__(self):
        return f"Message: {self.content[:20]} - Pattern: {self.pattern.name}"
