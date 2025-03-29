"""
Management command to populate bank accounts from existing transaction data.
"""
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from transactions.models import Transaction, BankAccount

logger = logging.getLogger('transactions')

class Command(BaseCommand):
    help = 'Populate bank accounts from existing transaction data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--update-transactions',
            action='store_true',
            help='Update transaction references to bank accounts',
        )
    
    def handle(self, *args, **options):
        update_transactions = options.get('update_transactions', False)
        
        self.stdout.write(self.style.WARNING('Starting bank account population...'))
        
        try:
            # Get unique bank account IDs from transactions
            bank_account_ids = Transaction.objects.values_list('legacy_bank_account_id', flat=True).distinct()
            bank_account_ids = [ba_id for ba_id in bank_account_ids if ba_id and ba_id.strip()]
            
            self.stdout.write(f"Found {len(bank_account_ids)} unique bank account IDs")
            
            # Create bank accounts
            created_count = 0
            
            with transaction.atomic():
                for bank_account_id in bank_account_ids:
                    # Check if a bank account with this name already exists
                    bank_account, created = BankAccount.objects.get_or_create(
                        name=bank_account_id,
                        defaults={
                            'account_number': None,
                            'bank_name': None,
                            'account_type': None,
                            'is_active': True
                        }
                    )
                    
                    if created:
                        created_count += 1
                    
                    # Update transactions to reference this bank account
                    if update_transactions:
                        affected_count = Transaction.objects.filter(
                            legacy_bank_account_id=bank_account_id,
                            bank_account__isnull=True
                        ).update(bank_account=bank_account)
                        
                        if affected_count:
                            self.stdout.write(f"Updated {affected_count} transactions for bank account: {bank_account_id}")
            
            self.stdout.write(self.style.SUCCESS(f"Successfully created {created_count} bank accounts!"))
            
            if update_transactions:
                # Count transactions with bank account references
                total_transactions = Transaction.objects.count()
                linked_transactions = Transaction.objects.filter(bank_account__isnull=False).count()
                percentage = (linked_transactions / total_transactions) * 100 if total_transactions > 0 else 0
                
                self.stdout.write(f"Transactions with bank account references: {linked_transactions}/{total_transactions} ({percentage:.1f}%)")
        
        except Exception as e:
            logger.error(f"Error populating bank accounts: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Bank account population failed: {str(e)}"))
            return 