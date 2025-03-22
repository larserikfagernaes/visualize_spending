import requests
import json
from requests.auth import HTTPBasicAuth
import datetime
import os
import time
from dateutil.relativedelta import relativedelta
import argparse
import django
import sys

# Set up Django environment
# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

# Import models after Django setup
from transactions.models import Transaction, Category, BankStatement

# Todos: 
# - Add automatic rolling of files_to_combine_with, now this has to be done manually

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def get_current_directory():
    """
    Returns the absolute directory path of the current file.
    This is useful for referencing files relative to this script.
    """
    return os.path.dirname(os.path.abspath(__file__))


# Now environment variables like TRIPLETEX_COMPANY_ID and TRIPLETEX_AUTH_TOKEN
# can be accessed using os.getenv()


# Set up Tripletex API credentials
# These should be set in your environment or directly here for testing
TRIPLETEX_COMPANY_ID = os.getenv("3T_AUTH_USER")  # Default is 0 for the main company
TRIPLETEX_AUTH_TOKEN = os.getenv("3T_SESSION_TOKEN")  # Your session token

# Check if credentials are available
if not TRIPLETEX_AUTH_TOKEN:
    raise ValueError("TRIPLETEX_AUTH_TOKEN environment variable is not set. Please set it before running this script.")

def get_date_list():
    # Define the start and end dates
    start_date = datetime.datetime(2023, 2, 1)
    end_date = datetime.datetime.today()

    # Generate the date range
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime('%m/%d/%Y'))
        current_date += relativedelta(months=1)

    # Append today's date
    dates.append(end_date.strftime('%m/%d/%Y'))
    return dates

def get_details_for_transaction(trans_id):
    cache_file = os.path.join(get_current_directory(), "transaction_cache.json")

    # Check if cache file exists
    if os.path.exists(cache_file):
        with open(cache_file) as file:
            cache_data = json.load(file)
        if trans_id in cache_data:
            return cache_data[trans_id]
        else:
            time.sleep(1)
            print("--not in cache--")

    url = "https://tripletex.no/v2/bank/statement/transaction/{}".format(trans_id)
    
    payload={}
    # Use the correct authentication format
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
    
    response = requests.request("GET", url, data=payload, auth=auth)
    transaction_data = response.json()

    # Create cache_data dictionary if it doesn't exist
    if not os.path.exists(cache_file):
        cache_data = {}
    
    cache_data[trans_id] = transaction_data

    with open(cache_file, 'w') as file:
        json.dump(cache_data, file)
    
    return transaction_data


def convert_bank_id_to_string(bank_id):
    with open(os.path.join(get_current_directory(), 'bank_account_map.json')) as file:
        bank_account_map = json.load(file)
    for account in bank_account_map:
        if account["bank_id"] == bank_id:
            return account["bank_name"]
    return "Unknown"

def get_all_bank_statements(force_refresh=False, cache_days=1):
    """
    Fetch all bank statements from Tripletex using pagination to handle the 1000 transaction limit
    
    Args:
        force_refresh (bool): If True, ignore cache and fetch fresh data
        cache_days (int): Number of days to consider cache valid
        
    Returns:
        dict: Dictionary containing bank statements data
    """
    # Define cache directory
    cache_dir = os.path.join(get_current_directory(), "cache")
    # Create cache directory if it doesn't exist
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
     
    url = "https://tripletex.no/v2/bank/statement"
    
    payload = {}
    headers = {
        'accept': 'application/json',
    }
    
    # Use the correct authentication format
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
    
    # Initialize variables for pagination
    from_index = 0
    count = 1000
    totalt_statements_to_get = 10000
    all_statements = []
    has_more = True
    
    print("Fetching bank statements from Tripletex...")
    print(f"Using company ID: {TRIPLETEX_COMPANY_ID}")
    
    # Loop until we've fetched all statements
    while has_more:
        print(f"Fetching statements {from_index} to {from_index + count}...")
        
        # Add pagination parameters
        params = {
            'from': from_index,
            'count': count
        }
        
        # Create a cache key based on the request parameters
        cache_key = f"bank_statements_{from_index}_{count}.json"
        cache_file = os.path.join(cache_dir, cache_key)
        
        # Check if we can use cached data for this request
        use_cache = False
        if not force_refresh and os.path.exists(cache_file):
            # Check if cache is still valid
            cache_timestamp = os.path.getmtime(cache_file)
            cache_datetime = datetime.datetime.fromtimestamp(cache_timestamp)
            cache_age = datetime.datetime.now() - cache_datetime
            
            if cache_age.days < cache_days:
                print(f"Using cached data for range {from_index}-{from_index+count} (age: {cache_age.seconds // 3600} hours, {(cache_age.seconds % 3600) // 60} minutes)")
                try:
                    with open(cache_file, 'r') as file:
                        data = json.load(file)
                    use_cache = True
                except Exception as e:
                    print(f"Error reading cache file: {str(e)}. Will fetch fresh data.")
            else:
                print(f"Cache for range {from_index}-{from_index+count} is {cache_age.days} days old. Fetching fresh data...")
        
        if not use_cache:
            # Make the API request
            response = requests.request(
                "GET", 
                url, 
                headers=headers, 
                params=params,
                data=payload, 
                auth=auth
            )
            
            if response.status_code != 200:
                print(f"Error fetching bank statements: {response.status_code}")
                print(response.text)
                break
            
            # Parse the response
            data = response.json()
            
            # Save to cache file
            try:
                with open(cache_file, 'w') as file:
                    json.dump(data, file)
                print(f"Cached data for range {from_index}-{from_index+count}")
            except Exception as e:
                print(f"Error saving cache file: {str(e)}")
        
        # Add the values to our list
        statements = data.get("values", [])
        all_statements.extend(statements)
        
        # Check if there are more statements to fetch
        total_count = data.get("fullResultSize", 0)
        current_count = len(all_statements)
        
        print(f"Fetched {current_count} of {total_count} statements")
        if (len(all_statements) > totalt_statements_to_get):
            break
        if current_count >= total_count or not statements:
            has_more = False
        else:
            from_index += count
            # Add a small delay to avoid rate limiting
            time.sleep(0.1)
    
    print(f"Successfully fetched {len(all_statements)} bank statements")
    
    # Create result dictionary
    result = {"values": all_statements}
    
    return result

def save_transactions_to_database(data):
    """
    Save processed transactions to the database
    
    Args:
        data (dict): Dictionary containing bank statements data with processed transactions
    
    Returns:
        tuple: (transactions_saved, transactions_skipped, transactions_updated)
    """
    transactions_saved = 0
    transactions_skipped = 0
    transactions_updated = 0
    
    # Get or create a default category for uncategorized transactions
    default_category, _ = Category.objects.get_or_create(
        name="Uncategorized",
        defaults={"description": "Default category for uncategorized transactions"}
    )
    
    print(f"Processing {len(data['values'])} bank statements for database import...")
    
    for statement in data["values"]:
        # First save the bank statement
        bank_statement = BankStatement(
            description=statement.get("description", ""),
            amount=statement.get("amount", 0),
            date=datetime.datetime.strptime(statement.get("fromDate"), "%Y-%m-%d"),
            category=default_category,
            source_file="tripletex_import"
        )
        bank_statement.save()
        
        # Process each transaction in the statement
        for transaction in statement.get("transactions", []):
            # Skip if there's no processed_data
            if "processed_data" not in transaction:
                transactions_skipped += 1
                continue
                
            processed_data = transaction["processed_data"]
            
            # Check if this transaction already exists in the database
            tripletex_id = str(transaction["id"])
            existing_transaction = None
            
            try:
                existing_transaction = Transaction.objects.get(tripletex_id=tripletex_id)
                # Update the existing transaction
                existing_transaction.description = processed_data.get("description", "")
                existing_transaction.amount = processed_data.get("amount", 0)
                existing_transaction.date = datetime.datetime.strptime(statement.get("fromDate"), "%Y-%m-%d")
                existing_transaction.bank_account_id = processed_data.get("bank_account_name", "Unknown")
                existing_transaction.account_id = processed_data.get("account_id")
                existing_transaction.is_internal_transfer = processed_data.get("is_internal_transfer", False)
                existing_transaction.is_wage_transfer = processed_data.get("is_wage_transfer", False)
                existing_transaction.is_tax_transfer = processed_data.get("is_tax_transfer", False)
                existing_transaction.is_forbidden = processed_data.get("is_forbidden", False)
                existing_transaction.should_process = processed_data.get("should_process", False)
                
                # Don't update category if it was already set to something other than the default
                if existing_transaction.category_id is None:
                    existing_transaction.category = default_category
                
                existing_transaction.save()
                transactions_updated += 1
                print(f"Transaction with tripletex_id {tripletex_id} updated.")
            except Transaction.DoesNotExist:
                # Create a new transaction
                new_transaction = Transaction(
                    tripletex_id=tripletex_id,
                    description=processed_data.get("description", ""),
                    amount=processed_data.get("amount", 0),
                    date=datetime.datetime.strptime(statement.get("fromDate"), "%Y-%m-%d"),
                    bank_account_id=processed_data.get("bank_account_name", "Unknown"),
                    account_id=processed_data.get("account_id"),
                    is_internal_transfer=processed_data.get("is_internal_transfer", False),
                    is_wage_transfer=processed_data.get("is_wage_transfer", False),
                    is_tax_transfer=processed_data.get("is_tax_transfer", False),
                    is_forbidden=processed_data.get("is_forbidden", False),
                    should_process=processed_data.get("should_process", False),
                    category=default_category
                )
                new_transaction.save()
                transactions_saved += 1
            
            if (transactions_saved + transactions_updated) % 100 == 0 and (transactions_saved + transactions_updated) > 0:
                print(f"Processed {transactions_saved + transactions_updated} transactions ({transactions_saved} new, {transactions_updated} updated)...")
    
    print(f"Database import complete. Saved {transactions_saved} new transactions. Updated {transactions_updated} existing transactions. Skipped {transactions_skipped} transactions.")
    return transactions_saved, transactions_skipped, transactions_updated

# Main execution
if __name__ == "__main__":
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Fetch and process bank transactions from Tripletex')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh of bank statements data')
    parser.add_argument('--cache-days', type=int, default=1, help='Number of days to consider cache valid')
    parser.add_argument('--save-to-db', action='store_true', help='Save processed transactions to the database')
    args = parser.parse_args()
    
    print(f"Starting bank transaction processing...")
    print(f"Force refresh: {args.force_refresh}")
    print(f"Cache validity: {args.cache_days} days")
    print(f"Save to database: {args.save_to_db}")
    
    # Ensure cache directory exists
    cache_dir = os.path.join(get_current_directory(), "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    # Get all bank statements with caching
    data = get_all_bank_statements(force_refresh=args.force_refresh, cache_days=args.cache_days)
    
    # Initialize cache for transaction details
    cache_transaction_file = os.path.join(get_current_directory(), "cache", "transaction_cache.json")
    if not os.path.exists(cache_transaction_file):
        with open(cache_transaction_file, 'w') as file:
            json.dump({}, file)
    
    with open(cache_transaction_file) as file:
        cache_data_transaction_data = json.load(file)
    
    # Process the bank statements
    forbidden_descriptions = ["oppgave til: 4213.42.3953542134239535", "stefan schweng"]
    start_time = time.time()
    
    print(f"Processing {len(data['values'])} bank statements...")
    
    for i, value in enumerate(data["values"]):
        bank_account_name = "Unknown"
        transaction_sum = 0
        processed_transactions = []
        
        if i % 100 == 0 and i > 0:
            elapsed_time = time.time() - start_time
            print(f"Processed {i}/{len(data['values'])} statements ({i/len(data['values'])*100:.1f}%) - Elapsed time: {elapsed_time:.1f}s")
        
        for transaction in value["transactions"]:
            if str(transaction["id"]) in cache_data_transaction_data:
                transaction_data = cache_data_transaction_data[str(transaction["id"])]
            else: 
                print(f"Fetching transaction details for index {i}")
                transaction_data = get_details_for_transaction(str(transaction["id"]))
            
            # Add the detailed transaction data to the transaction object
            transaction["detailed_data"] = transaction_data
            
            bank_account_name = convert_bank_id_to_string(transaction_data["value"]["account"]["id"])
            account_id = transaction_data["value"]["account"]["id"]
            transaction_amount = transaction_data["value"]["amountCurrency"]
            transaction_description = transaction_data["value"]["description"]
            transaction_posting = transaction_data["value"]["groupedPostings"]
    
            forbidden_desc = any(forbidden_key in transaction_description.lower() for forbidden_key in forbidden_descriptions) 
            internal_transfer = any(posting["description"] == "Intern overføring" for posting in transaction_posting)
            wage_transfer = any(posting["postingMatchType"] == "WAGE" for posting in transaction_posting)
            tax_transfer = any(posting["postingMatchType"] == "TAX" for posting in transaction_posting)
            
            # Add processed flags to the transaction
            transaction["processed_data"] = {
                "bank_account_name": bank_account_name,
                "amount": transaction_amount,
                "description": transaction_description,
                "is_forbidden": forbidden_desc,
                "is_internal_transfer": internal_transfer,
                "is_wage_transfer": wage_transfer,
                "is_tax_transfer": tax_transfer,
                "should_process": transaction_amount < 0 and not internal_transfer and not wage_transfer and not tax_transfer and not forbidden_desc,
                "account_id": account_id
            }
    
            if transaction_amount < 0 and not internal_transfer and not wage_transfer and not tax_transfer and not forbidden_desc: 
                transaction_sum += abs(transaction_amount)
                processed_transactions.append(transaction)
        
        # Add summary data to the statement
        value["processed_data"] = {
            "bank_account_name": bank_account_name,
            "account_id": account_id if 'account_id' in locals() else None,
            "transaction_sum": transaction_sum,
            "transaction_date": datetime.datetime.strptime(value["fromDate"], "%Y-%m-%d"),
            "processed_transactions_count": len(processed_transactions)
        }
    
    print(f"Completed processing in {time.time() - start_time:.1f} seconds")
    
    # Output summary
    print("\nSummary by bank account:")
    bank_accounts = {}
    for statement in data["values"]:
        bank_name = statement["processed_data"]["bank_account_name"]
        if bank_name not in bank_accounts:
            bank_accounts[bank_name] = {"count": 0, "amount": 0}
        
        bank_accounts[bank_name]["count"] += 1
        bank_accounts[bank_name]["amount"] += statement["processed_data"]["transaction_sum"]
    
    for account, info in bank_accounts.items():
        print(f"{account}: {info['count']} statements, total amount: {info['amount']:.2f}")
    
    # Save transactions to database if requested
    if args.save_to_db:
        transactions_saved, transactions_skipped, transactions_updated = save_transactions_to_database(data)
        print(f"\nDatabase Summary:")
        print(f"Transactions saved: {transactions_saved}")
        print(f"Transactions updated: {transactions_updated}")
        print(f"Transactions skipped: {transactions_skipped}")
    else:
        print("\nSkipping database import. Use --save-to-db flag to save transactions.")
 