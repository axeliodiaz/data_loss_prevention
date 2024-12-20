from django.contrib import admin

from apps.dlp.models import Pattern, DetectedMessage


@admin.register(DetectedMessage)
class DetectedMessageAdmin(admin.ModelAdmin):
    list_display = ("content", "pattern", "created", "modified")
    search_fields = (
        "content",
        "pattern__name",
    )
    ordering = ("-created",)
    list_filter = ("pattern", "created")


admin.site.register(Pattern)
