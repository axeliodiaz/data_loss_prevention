from django.contrib import admin
from django.utils.html import format_html

from apps.dlp.models import Pattern, DetectedMessage


@admin.register(DetectedMessage)
class DetectedMessageAdmin(admin.ModelAdmin):
    list_display = ("content", "pattern_link", "created", "modified")
    search_fields = (
        "content",
        "pattern__name",
    )
    ordering = ("-created",)
    list_per_page = 10
    list_filter = ("pattern", "created")

    @admin.display(description="Pattern Link")
    def pattern_link(self, obj):
        """
        Return a clickable link to the related Pattern object in the admin interface.
        """
        if obj.pattern:
            return format_html(
                '<a href="{}">{}</a>',
                obj.pattern.get_admin_url(),
                obj.pattern.name,
            )
        return "-"


admin.site.register(Pattern)
