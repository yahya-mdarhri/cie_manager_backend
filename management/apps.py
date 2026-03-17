import sys
from django.apps import AppConfig


class ManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "management"

    def ready(self):
        # Avoid during migrations
        if "migrate" in sys.argv or "makemigrations" in sys.argv:
            return
        import management.signals