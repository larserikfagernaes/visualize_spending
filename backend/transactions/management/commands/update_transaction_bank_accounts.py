from django.core.management.base import BaseCommand
from django.db.models import Count
from transactions.models import Transaction, BankAccount
import os
import json

class Command(BaseCommand):
    help = 'Update existing transactions with correct bank account references based on account_id'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Simulate the update without saving changes')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode - no changes will be saved"))
        
        self.stdout.write("Updating transactions with bank account references...")
        
        # Get all bank accounts
        bank_accounts = BankAccount.objects.all()
        self.stdout.write("Found {} bank accounts in the database".format(bank_accounts.count()))
        
        total_updated = 0
        
        # Update transactions for each bank account
        for bank_account in bank_accounts:
            account_number = bank_account.account_number
            
            # Skip if account number is empty
            if not account_number:
                continue
                
            # Find transactions with matching account_id but no bank_account
            transactions_to_update = Transaction.objects.filter(
                account_id=account_number,
                bank_account__isnull=True
            )
            
            count = transactions_to_update.count()
            
            if count > 0:
                self.stdout.write("Found {} transactions with account_id {} that need bank_account update".format(
                    count, account_number
                ))
                
                if not dry_run:
                    # Update all matching transactions
                    transactions_to_update.update(bank_account=bank_account)
                    self.stdout.write(self.style.SUCCESS("Updated {} transactions with bank account: {}".format(
                        count, bank_account.name
                    )))
                else:
                    self.stdout.write(self.style.WARNING("Would update {} transactions with bank account: {} (dry run)".format(
                        count, bank_account.name
                    )))
                
                total_updated += count
        
        # Final summary
        if dry_run:
            self.stdout.write(self.style.SUCCESS("\nDry run completed. Would update {} transactions with bank account references".format(total_updated)))
        else:
            self.stdout.write(self.style.SUCCESS("\nUpdated {} transactions with bank account references".format(total_updated))) 