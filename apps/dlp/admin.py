from django.contrib import admin

from apps.dlp.models import Pattern, DetectedMessage

admin.site.register(Pattern)
admin.site.register(DetectedMessage)
