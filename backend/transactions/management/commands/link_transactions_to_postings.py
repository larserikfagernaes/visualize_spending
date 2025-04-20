import os
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from transactions.models import Transaction, LedgerPosting
from transactions.get_transactions import get_or_create_supplier, get_or_create_account

# Setup logger
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Links transactions to ledger postings based on date range, amount, and description matches.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date-from',
            type=str,
            help='Start date for processing transactions (YYYY-MM-DD). Defaults to 180 days ago.'
        )
        parser.add_argument(
            '--date-to',
            type=str,
            help='End date for processing transactions (YYYY-MM-DD). Defaults to today.'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of transactions to process in each batch. Default is 1000.'
        )
        parser.add_argument(
            '--max-transactions',
            type=int,
            help='Maximum number of transactions to process. By default, processes all transactions.'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing links between transactions and ledger postings.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the linking process without saving changes to the database.'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update of supplier and account links even if already set.'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Show additional debug information.'
        )
        parser.add_argument(
            '--date-range',
            type=int,
            default=4,
            help='Number of days to search before and after the transaction date. Default is 4.'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        update_existing = options.get('update_existing', False)
        force = options.get('force', False)
        batch_size = options.get('batch_size', 1000)
        max_transactions = options.get('max_transactions')
        debug = options.get('debug', False)
        date_range = options.get('date_range', 4)
        
        # Set default dates if not provided - 180 days ago to today
        date_from_str = options.get('date_from')
        date_to_str = options.get('date_to')
        
        if not date_from_str:
            date_from = (datetime.now() - timedelta(days=180)).date()
            date_from_str = date_from.strftime('%Y-%m-%d')
        else:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
        
        if not date_to_str:
            date_to = datetime.now().date()
            date_to_str = date_to.strftime('%Y-%m-%d')
        else:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
        
        self.stdout.write(f"Processing transactions from {date_from_str} to {date_to_str}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE: No changes will be saved"))
        
        # Get transactions for the date range
        transactions_query = Transaction.objects.filter(
            date__gte=date_from,
            date__lte=date_to
        ).order_by('date')
        
        total_transactions = transactions_query.count()
        self.stdout.write(f"Found {total_transactions} transactions in the specified date range")
        
        # Limit to max_transactions if specified
        if max_transactions and max_transactions < total_transactions:
            self.stdout.write(f"Limiting to {max_transactions} transactions as requested")
            total_to_process = max_transactions
        else:
            total_to_process = total_transactions
        
        # Process in batches
        stats = {
            'total_transactions': total_to_process,
            'processed': 0,
            'linked': 0,
            'already_linked': 0,
            'no_match': 0,
            'suppliers_linked': 0,
            'accounts_linked': 0,
            'errors': 0,
        }
        
        # Process transactions in batches
        offset = 0
        while offset < total_to_process:
            # Calculate the end of the current batch
            end = min(offset + batch_size, total_to_process)
            batch_size_actual = end - offset
            
            self.stdout.write(f"Processing batch {offset+1} to {end} of {total_to_process}")
            
            # Get the current batch of transactions
            batch = transactions_query[offset:end]
            
            # Process each transaction in the batch
            for trans in batch:
                stats['processed'] += 1
                
                # Skip if transaction already has a linked posting (unless forced update)
                has_existing_links = False
                if trans.raw_data and isinstance(trans.raw_data, dict) and trans.raw_data.get('linked_postings') and not update_existing and not force:
                    has_existing_links = True
                    stats['already_linked'] += 1
                    if debug:
                        self.stdout.write(f"Transaction {trans.tripletex_id} already has linked postings: {trans.raw_data.get('linked_postings')}")
                    continue
                
                # Calculate date range for searching ledger postings
                date_from_range = trans.date - timedelta(days=date_range)
                date_to_range = trans.date + timedelta(days=date_range)
                
                # Look for ledger postings with matching amount within date range
                potential_postings = LedgerPosting.objects.filter(
                    date__gte=date_from_range,
                    date__lte=date_to_range,
                    amount=trans.amount
                )
                
                # Debug info
                if debug:
                    self.stdout.write(f"Transaction {trans.tripletex_id}: {trans.date} - {trans.description[:50]} (Amount: {trans.amount})")
                    self.stdout.write(f"  Searching for postings from {date_from_range} to {date_to_range}")
                    self.stdout.write(f"  Found {potential_postings.count()} potential matching postings")
                
                if potential_postings.exists():
                    # Find the best matching posting (for now, just take the first one)
                    # In the future, this could be improved to score matches based on description similarity
                    best_posting = potential_postings.first()
                    
                    if debug:
                        posting_desc = best_posting.description[:50] + "..." if best_posting.description and len(best_posting.description) > 50 else (best_posting.description or "No description")
                        self.stdout.write(f"  Best match: Posting {best_posting.posting_id}: {best_posting.date} - {posting_desc}")
                    
                    changes_made = False
                    
                    # Update supplier information if available
                    if best_posting.supplier and (force or not trans.supplier):
                        if debug:
                            self.stdout.write(f"  Supplier available: {best_posting.supplier}")
                        
                        if not dry_run:
                            trans.supplier = best_posting.supplier
                            changes_made = True
                            stats['suppliers_linked'] += 1
                            self.stdout.write(f"Linked transaction {trans.id} with supplier {best_posting.supplier}")
                    
                    # Update account information if available
                    if best_posting.account and (force or not trans.ledger_account):
                        if debug:
                            self.stdout.write(f"  Account available: {best_posting.account}")
                        
                        if not dry_run:
                            trans.ledger_account = best_posting.account
                            changes_made = True
                            stats['accounts_linked'] += 1
                            self.stdout.write(f"Linked transaction {trans.id} with account {best_posting.account}")
                    
                    # Mark transaction as linked
                    if not dry_run:
                        # Initialize raw_data if it doesn't exist
                        if trans.raw_data is None:
                            trans.raw_data = {}
                        elif not isinstance(trans.raw_data, dict):
                            # Handle case where raw_data is not a dictionary
                            self.stdout.write(self.style.WARNING(f"Transaction {trans.id} has raw_data that is not a dictionary. Converting to dictionary."))
                            trans.raw_data = {}
                            
                        if 'linked_postings' not in trans.raw_data:
                            trans.raw_data['linked_postings'] = []
                        
                        # Add posting ID to linked_postings if not already there
                        if best_posting.posting_id not in trans.raw_data['linked_postings']:
                            trans.raw_data['linked_postings'].append(best_posting.posting_id)
                            changes_made = True
                        
                        if changes_made:
                            trans.save()
                            stats['linked'] += 1
                            if debug:
                                self.stdout.write(self.style.SUCCESS(f"  Successfully linked transaction {trans.id} to posting {best_posting.posting_id}"))
                        elif debug:
                            self.stdout.write(f"  No changes needed for transaction {trans.id}")
                    elif debug:
                        self.stdout.write(f"  Dry run - would link transaction {trans.id} to posting {best_posting.posting_id}")
                        if force or not trans.supplier:
                            self.stdout.write(f"  Would link supplier: {best_posting.supplier}")
                        if force or not trans.ledger_account:
                            self.stdout.write(f"  Would link account: {best_posting.account}")
                        stats['linked'] += 1
                else:
                    stats['no_match'] += 1
                    if debug and (stats['no_match'] <= 10 or stats['no_match'] % 100 == 0):  # Limit logging
                        self.stdout.write(f"No matching postings found for transaction {trans.id}")
                
                # Print progress for every 10% or every 100 transactions, whichever is less frequent
                progress_interval = max(100, int(total_to_process * 0.1))
                if stats['processed'] % progress_interval == 0 or stats['processed'] == total_to_process:
                    percentage = (stats['processed'] / total_to_process) * 100
                    self.stdout.write(f"Processed {stats['processed']} of {total_to_process} transactions ({percentage:.1f}%)")
            
            # Update offset for the next batch
            offset += batch_size_actual
            
            # Print batch summary
            self.stdout.write(f"Batch summary: {stats['linked']} linked, {stats['already_linked']} already linked, {stats['no_match']} no matches")
        
        # Report final results
        self.stdout.write(self.style.SUCCESS("Linking process completed!"))
        self.stdout.write(f"Total transactions processed: {stats['processed']}/{stats['total_transactions']}")
        self.stdout.write(f"Transactions linked: {stats['linked']}")
        self.stdout.write(f"Already linked: {stats['already_linked']}")
        self.stdout.write(f"No matches found: {stats['no_match']}")
        self.stdout.write(f"Suppliers linked: {stats['suppliers_linked']}")
        self.stdout.write(f"Accounts linked: {stats['accounts_linked']}")
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"Errors encountered: {stats['errors']}")) 