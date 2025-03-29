"""
Management command to import transactions from Tripletex.
"""
import logging
from django.core.management.base import BaseCommand
from transactions.services.transaction_service import import_transactions_from_tripletex

logger = logging.getLogger('transactions')

class Command(BaseCommand):
    help = 'Import transactions from Tripletex API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force import even if transactions already exist',
        )
    
    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.WARNING('Starting transaction import...'))
        
        try:
            result = import_transactions_from_tripletex()
            
            self.stdout.write(self.style.SUCCESS(f"Import completed successfully!"))
            self.stdout.write(f"New transactions: {result['new_transactions']}")
            self.stdout.write(f"Updated transactions: {result['updated_transactions']}")
            self.stdout.write(f"Errors: {result['errors']}")
            
            if result['errors'] > 0:
                self.stdout.write(self.style.WARNING('Some errors occurred during import. Check the logs for details.'))
        
        except Exception as e:
            logger.error(f"Error running import command: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Import failed: {str(e)}"))
            return 