from django.apps import AppConfig


class RestaurantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restaurants'

    def ready(self):
        # Import signal handlers to wire automatic notifications
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Never break app startup due to signals import
            pass
