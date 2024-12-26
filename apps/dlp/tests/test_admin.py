import pytest
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from apps.dlp.admin import DetectedMessageAdmin
from apps.dlp.models import DetectedMessage, Pattern


@pytest.mark.django_db
def test_admin_pattern_link(detected_message):
    """
    Test the pattern_link method in DetectedMessageAdmin.
    """
    admin_instance = DetectedMessageAdmin(DetectedMessage, AdminSite())
    result = admin_instance.pattern_link(detected_message)
    assert result == (
        f'<a href="{detected_message.pattern.get_admin_url()}">'
        f"{detected_message.pattern.name}</a>"
    )
