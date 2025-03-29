import os
import json
from django.core.management.base import BaseCommand
from django.db.models import Q
from transactions.models import Transaction
from transactions.get_transactions import get_current_directory


class Command(BaseCommand):
    help = 'Fix tripletex_id fields in transactions to match cache keys'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of transactions to process',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        dry_run = options.get('dry_run', False)
        
        # Get all transactions
        transactions = Transaction.objects.all()
        transaction_count = transactions.count()
        
        if limit:
            transactions = transactions[:limit]
            self.stdout.write(self.style.SUCCESS(f"Limiting to {limit} transactions"))
        
        self.stdout.write(self.style.SUCCESS(f"Found {transaction_count} transactions to examine"))
        
        # Load both transaction caches
        main_cache_file = os.path.join(get_current_directory(), "transaction_cache.json")
        alt_cache_file = os.path.join(get_current_directory(), "cache", "transaction_cache.json")
        
        cache_data = {}
        
        # Load main cache
        if os.path.exists(main_cache_file):
            try:
                with open(main_cache_file) as file:
                    main_cache = json.load(file)
                self.stdout.write(self.style.SUCCESS(f"Loaded {len(main_cache)} entries from main cache"))
                cache_data.update(main_cache)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error loading main cache: {e}"))
        
        # Load alternative cache
        if os.path.exists(alt_cache_file):
            try:
                with open(alt_cache_file) as file:
                    alt_cache = json.load(file)
                self.stdout.write(self.style.SUCCESS(f"Loaded {len(alt_cache)} entries from alternate cache"))
                cache_data.update(alt_cache)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error loading alternate cache: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Total cache entries: {len(cache_data)}"))
        
        # Initialize counters
        updated_count = 0
        not_found_count = 0
        already_correct_count = 0
        
        # Process transactions
        for i, transaction in enumerate(transactions):
            if i % 50 == 0 and i > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processed {i}/{transactions.count()} transactions. "
                        f"Updated: {updated_count}, Not found: {not_found_count}, Already correct: {already_correct_count}"
                    )
                )
            
            # Skip if no tripletex_id
            if not transaction.tripletex_id:
                not_found_count += 1
                continue
            
            # Check if transaction.tripletex_id already exists in cache
            if transaction.tripletex_id in cache_data:
                already_correct_count += 1
                continue
            
            # Try to find a matching key in the cache
            found_match = False
            
            # Check for suffix match (last 5 digits)
            if transaction.tripletex_id.isdigit():
                suffix = transaction.tripletex_id[-5:]
                
                for cache_key in cache_data.keys():
                    if cache_key.isdigit() and cache_key.endswith(suffix):
                        # Check if amount matches approximately (within 0.1)
                        cache_amount = None
                        try:
                            cache_amount = float(cache_data[cache_key]["value"]["amountCurrency"])
                        except (KeyError, TypeError, ValueError):
                            continue
                        
                        transaction_amount = float(transaction.amount)
                        
                        # If amounts are very close, it's likely the same transaction
                        if abs(cache_amount - transaction_amount) < 0.1:
                            self.stdout.write(
                                f"Found match for transaction {transaction.id}: "
                                f"Old ID: {transaction.tripletex_id}, New ID: {cache_key}, "
                                f"Amount: {transaction_amount}"
                            )
                            
                            if not dry_run:
                                transaction.tripletex_id = cache_key
                                transaction.save(update_fields=['tripletex_id'])
                            
                            updated_count += 1
                            found_match = True
                            break
            
            if not found_match:
                not_found_count += 1
        
        # Print summary
        self.stdout.write(self.style.SUCCESS("\nSummary:"))
        self.stdout.write(self.style.SUCCESS(f"Processed {transactions.count()} transactions"))
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated_count}, Not found: {not_found_count}, Already correct: {already_correct_count}"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("This was a dry run. No changes were made."))
            self.stdout.write(self.style.WARNING("Run without --dry-run to apply the changes.")) 