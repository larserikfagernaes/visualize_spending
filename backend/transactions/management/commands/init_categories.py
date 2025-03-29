"""
Management command to initialize default categories.
"""
import logging
from django.core.management.base import BaseCommand
from transactions.services.category_service import initialize_default_categories

logger = logging.getLogger('transactions')

class Command(BaseCommand):
    help = 'Initialize default transaction categories'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Initializing default categories...'))
        
        try:
            created_count = initialize_default_categories()
            
            if created_count > 0:
                self.stdout.write(self.style.SUCCESS(f"Successfully created {created_count} categories!"))
            else:
                self.stdout.write(self.style.SUCCESS("All default categories already exist. No new categories created."))
        
        except Exception as e:
            logger.error(f"Error initializing categories: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Category initialization failed: {str(e)}"))
            return 