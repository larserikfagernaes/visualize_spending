import os
import requests
import logging
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta, date
from decimal import Decimal
from dotenv import load_dotenv

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date
from requests.auth import HTTPBasicAuth
from django.db import transaction

from transactions.models import LedgerPosting, Supplier, Account
from django.conf import settings

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Auth credentials (using the same environment variable names as in link_transactions.py)
TRIPLETEX_COMPANY_ID = os.getenv("3T_AUTH_USER", "")
TRIPLETEX_AUTH_TOKEN = os.getenv("3T_SESSION_TOKEN", "")

TRIPLETEX_BASE_URL = "https://tripletex.no/v2"
CACHE_DIR = Path("cache/tripletex/ledger_postings")

class Command(BaseCommand):
    help = 'Fetches ledger postings from the Tripletex API and saves them to the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date-from',
            type=str,
            help='Start date for fetching postings (YYYY-MM-DD). Defaults to January 1, 2022.'
        )
        parser.add_argument(
            '--date-to',
            type=str,
            help='End date for fetching postings (YYYY-MM-DD). Defaults to today.'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of postings to fetch per API request. Default is 1000.'
        )
        parser.add_argument(
            '--chunk-months',
            type=int,
            default=1,
            help='Size of date chunks in months when fetching large date ranges. Default is 3.'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing ledger posting records if they have changed in Tripletex.'
        )
        parser.add_argument(
            '--force-refresh',
            action='store_true',
            help='Ignore cached data and fetch fresh data from the API.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Skip API calls and just create the database model (for testing).'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if not dry_run and (not TRIPLETEX_COMPANY_ID or not TRIPLETEX_AUTH_TOKEN):
            self.stdout.write(self.style.ERROR("3T_AUTH_USER and 3T_SESSION_TOKEN environment variables must be set."))
            self.stdout.write(self.style.ERROR("You can use --dry-run to skip API calls and just create the database model."))
            return
            
        if not dry_run:
            self.stdout.write(f"Using auth credentials: TRIPLETEX_COMPANY_ID={TRIPLETEX_COMPANY_ID}")

        date_from_str = options['date_from']
        date_to_str = options['date_to']
        batch_size = options['batch_size']
        chunk_months = options['chunk_months']
        update_existing = options['update_existing']
        force_refresh = options['force_refresh']

        # Set default dates if not provided - January 2022 to today
        if not date_from_str:
            date_from_str = "2022-01-01"  # Start from January 2022
        if not date_to_str:
            date_to_str = datetime.now().date().strftime("%Y-%m-%d")
            
        # Parse dates
        date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()

        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # If dry run, create a sample posting and exit
        if dry_run:
            self.stdout.write("Dry run mode: Creating a sample LedgerPosting record without API call")
            sample_posting = {
                'id': 999999,
                'date': date.today().isoformat(),
                'description': 'Sample ledger posting (dry run)',
                'amount': 1000.0,
                'supplier': None,
                'account': None,
                'voucher': {'id': 888888, 'number': 'SAMPLE', 'type': 'MANUAL'}
            }
            self.save_postings_to_db([sample_posting], update_existing)
            return

        self.stdout.write(f"Fetching ledger postings from {date_from_str} to {date_to_str} with batch size {batch_size}")
        
        # Split date range into chunks if it spans multiple months
        date_chunks = self.get_date_chunks(date_from, date_to, chunk_months)
        
        all_postings = []
        total_api_calls = 0
        total_from_cache = 0
        
        # Process each date chunk
        for chunk_start, chunk_end in date_chunks:
            chunk_start_str = chunk_start.strftime("%Y-%m-%d")
            chunk_end_str = chunk_end.strftime("%Y-%m-%d")
            
            self.stdout.write(f"Processing date chunk: {chunk_start_str} to {chunk_end_str}")
            
            # Fetch all postings for this date chunk
            chunk_postings, api_calls, from_cache = self.fetch_all_postings_for_date_range(
                chunk_start_str, 
                chunk_end_str, 
                batch_size, 
                force_refresh
            )
            
            all_postings.extend(chunk_postings)
            total_api_calls += api_calls
            total_from_cache += from_cache
            
            self.stdout.write(f"Fetched {len(chunk_postings)} postings for chunk {chunk_start_str} to {chunk_end_str}")

        self.stdout.write(self.style.SUCCESS(f"Successfully fetched {len(all_postings)} ledger postings in total."))
        self.stdout.write(f"API calls: {total_api_calls}, Cache hits: {total_from_cache}")
        
        self.save_postings_to_db(all_postings, update_existing)

    def get_date_chunks(self, start_date, end_date, months_per_chunk=1):
        """
        Split a date range into smaller chunks of specified months.
        Optimized for monthly processing.
        
        Args:
            start_date: Start date (date object)
            end_date: End date (date object)
            months_per_chunk: Number of months per chunk
            
        Returns:
            List of (chunk_start, chunk_end) date tuples
        """
        chunks = []
        current_start = start_date
        
        # When processing one month at a time, use a simpler approach
        if months_per_chunk == 1:
            # Start on the first of the month if not already
            if current_start.day != 1:
                # Move to the first day of the next month
                if current_start.month == 12:
                    current_start = date(current_start.year + 1, 1, 1)
                else:
                    current_start = date(current_start.year, current_start.month + 1, 1)
            
            # Process one month at a time
            while current_start <= end_date:
                # Calculate the last day of the current month
                if current_start.month == 12:
                    next_month_year = current_start.year + 1
                    next_month = 1
                else:
                    next_month_year = current_start.year
                    next_month = current_start.month + 1
                
                # Last day of current month is one day before the first day of next month
                chunk_end = date(next_month_year, next_month, 1) - timedelta(days=1)
                
                # Ensure chunk_end doesn't exceed end_date
                if chunk_end > end_date:
                    chunk_end = end_date
                
                chunks.append((current_start, chunk_end))
                
                # Move to the first day of the next month
                current_start = date(next_month_year, next_month, 1)
            
            return chunks
        
        # Original logic for multi-month chunks
        while current_start <= end_date:
            # Calculate chunk end date (current_start + months_per_chunk)
            if current_start.month + months_per_chunk <= 12:
                # Same year
                chunk_end_month = current_start.month + months_per_chunk
                chunk_end_year = current_start.year
            else:
                # Next year
                chunk_end_month = (current_start.month + months_per_chunk) % 12
                if chunk_end_month == 0:
                    chunk_end_month = 12
                chunk_end_year = current_start.year + ((current_start.month + months_per_chunk - 1) // 12)
            
            # Create chunk end date (last day of the month)
            if chunk_end_month in [4, 6, 9, 11]:
                chunk_end_day = 30
            elif chunk_end_month == 2:
                # Leap year check
                if (chunk_end_year % 4 == 0 and chunk_end_year % 100 != 0) or (chunk_end_year % 400 == 0):
                    chunk_end_day = 29
                else:
                    chunk_end_day = 28
            else:
                chunk_end_day = 31
            
            chunk_end = date(chunk_end_year, chunk_end_month, chunk_end_day)
            
            # Ensure chunk_end doesn't exceed end_date
            if chunk_end > end_date:
                chunk_end = end_date
            
            chunks.append((current_start, chunk_end))
            
            # Set next chunk start date
            current_start = chunk_end + timedelta(days=1)
        
        return chunks

    def fetch_all_postings_for_date_range(self, date_from, date_to, batch_size, force_refresh):
        """
        Fetch all postings for a specific date range, handling pagination properly.
        If we hit the batch size limit, split the date range into smaller chunks.
        
        Args:
            date_from: Start date string (YYYY-MM-DD)
            date_to: End date string (YYYY-MM-DD)
            batch_size: Number of records per request
            force_refresh: Whether to ignore cached data
            
        Returns:
            Tuple of (all_postings, api_calls_count, cache_hits_count)
        """
        auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
        all_postings = []
        api_calls = 0
        cache_hits = 0

        # Convert date strings to date objects for manipulation
        start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        current_start = start_date
        
        while current_start <= end_date:
            current_end = end_date
            current_from = 0
            date_chunk_postings = []
            
            while True:
                params = {
                    "dateFrom": current_start.strftime("%Y-%m-%d"),
                    "dateTo": current_end.strftime("%Y-%m-%d"),
                    "from": current_from,
                    "count": batch_size,
                    "fields": "id,date,description,amount,supplier,account,voucher" 
                }
                
                # Generate a cache key based on the request parameters
                params_str = json.dumps(params, sort_keys=True)
                cache_key = hashlib.md5(params_str.encode()).hexdigest()
                cache_file = CACHE_DIR / f"{cache_key}.json"
                
                data = None
                # Try to load from cache if not forcing refresh
                if not force_refresh and cache_file.exists():
                    try:
                        self.stdout.write(f"Using cached data for {params['dateFrom']} to {params['dateTo']}, index {current_from}")
                        with open(cache_file, 'r') as f:
                            data = json.load(f)
                        cache_hits += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Failed to load cache: {e}. Fetching from API."))
                        data = None
                
                # Fetch from API if not in cache
                if data is None:
                    url = f"{TRIPLETEX_BASE_URL}/ledger/posting"
                    try:
                        self.stdout.write(f"Fetching from API for {params['dateFrom']} to {params['dateTo']}, index {current_from}")
                        response = requests.get(url, params=params, auth=auth)
                        api_calls += 1
                        
                        # More detailed error handling
                        if response.status_code != 200:
                            error_msg = f"API request failed with status code {response.status_code}"
                            try:
                                error_details = response.json()
                                error_msg += f": {error_details}"
                            except:
                                error_msg += f": {response.text}"
                            
                            self.stdout.write(self.style.ERROR(error_msg))
                            raise CommandError(error_msg)
                            
                        data = response.json()
                        
                        # Save to cache
                        with open(cache_file, 'w') as f:
                            json.dump(data, f)
                        self.stdout.write(f"Cached response to {cache_file}")
                            
                    except requests.exceptions.RequestException as e:
                        raise CommandError(f"API request failed: {e}")
                
                postings = data.get('values', [])
                total_count = data.get('count', 0)
                
                if not postings:
                    self.stdout.write("No more postings found for this date range")
                    break
                    
                date_chunk_postings.extend(postings)
                self.stdout.write(f"Processed {len(postings)} postings (chunk total: {len(date_chunk_postings)} / {total_count})")

                # If we got exactly batch_size records and it's not the last page
                if len(postings) == batch_size and current_from == 0:
                    # We might be hitting a limit - split the date range
                    days_in_range = (current_end - current_start).days
                    if days_in_range > 1:
                        # Split the date range in half
                        mid_date = current_start + timedelta(days=days_in_range // 2)
                        self.stdout.write(self.style.WARNING(
                            f"Got {batch_size} records for {days_in_range} days. "
                            f"Splitting date range at {mid_date}"
                        ))
                        # Process the first half now
                        current_end = mid_date
                        # Reset postings for this smaller chunk
                        date_chunk_postings = []
                        current_from = 0
                        continue

                # Check if we've fetched all records for this date range
                if current_from + len(postings) >= total_count:
                    self.stdout.write("Reached end of available records for this date range")
                    break
                
                # Update the 'from' parameter for the next page
                current_from += len(postings)
            
            # Add the postings from this date chunk to our total
            all_postings.extend(date_chunk_postings)
            
            # If we split the date range, move to the second half
            if current_end < end_date:
                current_start = current_end + timedelta(days=1)
            else:
                # Move to the next month
                if current_start.month == 12:
                    current_start = date(current_start.year + 1, 1, 1)
                else:
                    current_start = date(current_start.year, current_start.month + 1, 1)

        return all_postings, api_calls, cache_hits

    def save_postings_to_db(self, postings, update_existing):
        self.stdout.write("Saving postings to database...")
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        with transaction.atomic(): # Use a transaction for efficiency and safety
            for posting_data in postings:
                posting_id = posting_data.get('id')
                if not posting_id:
                    logger.warning(f"Skipping posting due to missing ID: {posting_data}")
                    error_count += 1
                    continue

                posting_date_str = posting_data.get('date')
                posting_date = parse_date(posting_date_str) if posting_date_str else None
                if not posting_date:
                     logger.warning(f"Skipping posting {posting_id} due to invalid date: {posting_date_str}")
                     error_count += 1
                     continue
                     
                supplier_data = posting_data.get('supplier')
                account_data = posting_data.get('account')
                voucher_data = posting_data.get('voucher')

                supplier_instance = None
                if supplier_data and supplier_data.get('id'):
                    supplier_instance, _ = Supplier.objects.get_or_create(
                        tripletex_id=supplier_data['id'],
                        defaults={'url': supplier_data.get('url')}
                    )

                account_instance = None
                if account_data and account_data.get('id'):
                    account_instance, _ = Account.objects.get_or_create(
                        tripletex_id=account_data['id'],
                        defaults={'url': account_data.get('url')}
                    )
                
                defaults = {
                    'date': posting_date,
                    'description': posting_data.get('description'),
                    'amount': Decimal(str(posting_data.get('amount', 0.0))), # Ensure Decimal conversion
                    'supplier': supplier_instance,
                    'account': account_instance,
                    'voucher_id': voucher_data.get('id') if voucher_data else None,
                    'voucher_number': voucher_data.get('number') if voucher_data else None,
                    'voucher_type': voucher_data.get('type') if voucher_data else None,
                    'raw_data': posting_data
                }

                try:
                    obj, created = LedgerPosting.objects.update_or_create(
                        posting_id=posting_id,
                        defaults=defaults
                    )

                    if created:
                        created_count += 1
                    elif update_existing:
                        # update_or_create handles the update, we just count it
                        updated_count += 1
                    else:
                         # Existed but not updating
                         skipped_count += 1
                except Exception as e:
                    logger.error(f"Error saving posting {posting_id}: {e}")
                    error_count += 1

        self.stdout.write(self.style.SUCCESS(f"Database update complete."))
        self.stdout.write(f"  Created: {created_count}")
        if update_existing:
             self.stdout.write(f"  Updated: {updated_count}")
        else:
            self.stdout.write(f"  Skipped (already exist): {skipped_count}")
        if error_count > 0:
             self.stdout.write(self.style.ERROR(f"  Errors: {error_count}")) 