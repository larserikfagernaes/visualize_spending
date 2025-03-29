import os
import sys
import json
import django

# Set up Django environment
# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import Transaction
from transactions.get_transactions import get_current_directory, get_details_for_transaction

def update_transaction_raw_data():
    """
    Updates existing transactions with raw_data from the transaction cache.
    This is a one-time operation to populate raw_data for transactions that 
    were created before this field was added.
    """
    # Get transactions without raw_data
    transactions = Transaction.objects.filter(raw_data__isnull=True)
    transaction_count = transactions.count()
    print(f"Found {transaction_count} transactions without raw_data")
    
    # Get transaction cache
    cache_file = os.path.join(get_current_directory(), "transaction_cache.json")
    cache_dir = os.path.join(get_current_directory(), "cache")
    
    # Check if cache directories exist
    if not os.path.exists(cache_file):
        print(f"Cache file {cache_file} not found")
        return
    
    # Load transaction cache
    with open(cache_file) as file:
        transaction_cache = json.load(file)
    
    print(f"Loaded {len(transaction_cache)} transactions from cache")
    
    # Initialize counters
    updated_count = 0
    not_found_count = 0
    
    # Process transactions
    for i, transaction in enumerate(transactions):
        if i % 50 == 0 and i > 0:
            print(f"Processed {i}/{transaction_count} transactions. Updated: {updated_count}, Not found: {not_found_count}")
        
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
    print(f"\nSummary:")
    print(f"Processed {transaction_count} transactions")
    print(f"Updated {updated_count} transactions with raw_data")
    print(f"Could not find data for {not_found_count} transactions")

if __name__ == "__main__":
    update_transaction_raw_data() 