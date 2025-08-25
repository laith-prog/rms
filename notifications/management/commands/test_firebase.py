from django.core.management.base import BaseCommand
from firebase_service import firebase_service


class Command(BaseCommand):
    help = 'Test Firebase connection'

    def handle(self, *args, **options):
        if firebase_service.is_initialized():
            self.stdout.write(
                self.style.SUCCESS('SUCCESS: Firebase is properly initialized and ready to send notifications!')
            )
        else:
            self.stdout.write(
                self.style.ERROR('ERROR: Firebase is not initialized. Please check your service account configuration.')
            )
            self.stdout.write(
                self.style.WARNING('Make sure you have set either:')
            )
            self.stdout.write('  1. FIREBASE_SERVICE_ACCOUNT_KEY environment variable with the JSON content')
            self.stdout.write('  2. FIREBASE_SERVICE_ACCOUNT_PATH environment variable with the path to your JSON file')