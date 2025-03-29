"""
Management command to update internal transfers.
"""
import logging
from django.core.management.base import BaseCommand
from transactions.services.transaction_service import update_all_internal_transfers

logger = logging.getLogger('transactions')

class Command(BaseCommand):
    help = 'Update transactions to identify internal transfers'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Analyzing transactions for internal transfers...'))
        
        try:
            result = update_all_internal_transfers()
            
            self.stdout.write(self.style.SUCCESS(f"Transfer analysis completed successfully!"))
            self.stdout.write(f"Newly marked internal transfers: {result['updated_transactions']}")
            self.stdout.write(f"Already marked internal transfers: {result['already_marked']}")
            self.stdout.write(f"Total transactions processed: {result['total_processed']}")
        
        except Exception as e:
            logger.error(f"Error running transfer update command: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Transfer analysis failed: {str(e)}"))
            return 