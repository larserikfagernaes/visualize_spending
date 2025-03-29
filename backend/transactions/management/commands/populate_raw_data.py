import os
import json
from django.core.management.base import BaseCommand
from django.db.models import Q
from transactions.models import Transaction
from transactions.get_transactions import get_current_directory


class Command(BaseCommand):
    help = 'Populate raw_data field for all transactions without it'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of transactions to process',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if raw_data already exists',
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        force_update = options.get('force', False)
        
        # Get transactions without raw_data
        if force_update:
            transactions = Transaction.objects.all()
            self.stdout.write(self.style.WARNING(f"Force updating ALL transactions"))
        else:
            transactions = Transaction.objects.filter(Q(raw_data__isnull=True))
            self.stdout.write(self.style.SUCCESS(f"Found {transactions.count()} transactions without raw_data"))
        
        if limit:
            transactions = transactions[:limit]
            self.stdout.write(self.style.SUCCESS(f"Limiting to {limit} transactions"))
        
        # Get transaction cache
        cache_file = os.path.join(get_current_directory(), "transaction_cache.json")
        
        # Check if cache file exists
        if not os.path.exists(cache_file):
            self.stdout.write(self.style.ERROR(f"Cache file {cache_file} not found"))
            return
        
        # Load transaction cache
        with open(cache_file) as file:
            transaction_cache = json.load(file)
        
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(transaction_cache)} transactions from cache"))
        
        # Initialize counters
        updated_count = 0
        not_found_count = 0
        
        # Process transactions
        for i, transaction in enumerate(transactions):
            if i % 50 == 0 and i > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processed {i}/{transactions.count()} transactions. "
                        f"Updated: {updated_count}, Not found: {not_found_count}"
                    )
                )
            
            # Skip if no tripletex_id
            if not transaction.tripletex_id:
                not_found_count += 1
                continue
            
            # Check if transaction is in cache
            if transaction.tripletex_id in transaction_cache:
                detailed_data = transaction_cache[transaction.tripletex_id]
                
                # Create raw_data
                raw_data = {
                    "transaction": {
                        "id": transaction.tripletex_id,
                        "description": transaction.description,
                        "amount": float(transaction.amount)
                    },
                    "detailed_data": detailed_data,
                    "processed_data": {
                        "bank_account_name": transaction.bank_account_id,
                        "amount": float(transaction.amount),
                        "description": transaction.description,
                        "is_forbidden": transaction.is_forbidden,
                        "is_internal_transfer": transaction.is_internal_transfer,
                        "is_wage_transfer": transaction.is_wage_transfer,
                        "is_tax_transfer": transaction.is_tax_transfer,
                        "should_process": transaction.should_process,
                        "account_id": transaction.account_id
                    },
                    "statement": {
                        "fromDate": transaction.date.strftime("%Y-%m-%d")
                    }
                }
                
                # Update transaction
                transaction.raw_data = raw_data
                transaction.save()
                updated_count += 1
            else:
                not_found_count += 1
        
        # Print summary
        self.stdout.write(self.style.SUCCESS("\nSummary:"))
        self.stdout.write(self.style.SUCCESS(f"Processed {transactions.count()} transactions"))
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated_count}, Not found: {not_found_count}")) 