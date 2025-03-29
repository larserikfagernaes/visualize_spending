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
from transactions.models import Transaction, Category, BankStatement, BankAccount, Supplier, Account

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


def get_details_for_transaction(trans_id):
    cache_file = os.path.join(get_current_directory(), "cache", "transaction_cache.json")

    # Check if cache file exists
    if os.path.exists(cache_file):
        with open(cache_file) as file:
            cache_data = json.load(file)
        if trans_id in cache_data:
            return cache_data[trans_id]
        else:
            time.sleep(0.2)
            print("--not in cache--")

    url = "https://tripletex.no/v2/bank/statement/transaction/{}".format(trans_id)
    
    payload={}
    # Use the correct authentication format
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
    
    response = requests.request("GET", url, data=payload, auth=auth)
    transaction_data = response.json()
    
    cache_data[trans_id] = transaction_data

    with open(cache_file, 'w') as file:
        json.dump(cache_data, file)
    
    return transaction_data

def get_supplier_info(supplier_id):
    """
    Fetch supplier information from Tripletex API
    
    Args:
        supplier_id: The ID of the supplier in Tripletex
        
    Returns:
        dict: Supplier data from the API
    """
    # Check if we have the data cached
    cache_dir = os.path.join(get_current_directory(), "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    cache_file = os.path.join(cache_dir, f"supplier_{supplier_id}.json")
    
    # Check if cache file exists and is recent (less than 7 days old)
    if os.path.exists(cache_file):
        file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))
        if file_age.days < 7:  # Cache is valid for 7 days
            with open(cache_file) as file:
                try:
                    supplier_data = json.load(file)
                    return supplier_data
                except json.JSONDecodeError:
                    # If the file is corrupted, fetch fresh data
                    pass
    
    # Fetch from API if not in cache or cache is too old
    url = f"https://tripletex.no/v2/supplier/{supplier_id}"
    
    # Use the correct authentication format
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
    
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        supplier_data = response.json()
        
        # Cache the data
        with open(cache_file, 'w') as file:
            json.dump(supplier_data, file)
        
        return supplier_data
    except Exception as e:
        print(f"Error fetching supplier data for ID {supplier_id}: {str(e)}")
        return None

def get_account_info(account_id):
    """
    Fetch account information from Tripletex API
    
    Args:
        account_id: The ID of the ledger account in Tripletex
        
    Returns:
        dict: Account data from the API
    """
    # Check if we have the data cached
    cache_dir = os.path.join(get_current_directory(), "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    cache_file = os.path.join(cache_dir, f"account_{account_id}.json")
    
    # Check if cache file exists and is recent (less than 7 days old)
    if os.path.exists(cache_file):
        file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))
        if file_age.days < 7:  # Cache is valid for 7 days
            with open(cache_file) as file:
                try:
                    account_data = json.load(file)
                    return account_data
                except json.JSONDecodeError:
                    # If the file is corrupted, fetch fresh data
                    pass
    
    # Fetch from API if not in cache or cache is too old
    url = f"https://tripletex.no/v2/ledger/account/{account_id}"
    
    # Use the correct authentication format
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
    
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        account_data = response.json()
        
        # Cache the data
        with open(cache_file, 'w') as file:
            json.dump(account_data, file)
        
        return account_data
    except Exception as e:
        print(f"Error fetching account data for ID {account_id}: {str(e)}")
        return None

def get_or_create_supplier(supplier_id):
    """
    Get or create a Supplier object based on the supplier ID from Tripletex
    
    Args:
        supplier_id: The supplier ID from Tripletex
        
    Returns:
        Supplier: The supplier object, or None if it couldn't be found or created
    """
    if not supplier_id:
        return None
    
    # First try to find an existing supplier
    try:
        supplier = Supplier.objects.get(tripletex_id=str(supplier_id))
        return supplier
    except Supplier.DoesNotExist:
        # If not found, fetch data from Tripletex API
        supplier_data = get_supplier_info(supplier_id)
        
        if supplier_data and 'value' in supplier_data:
            value = supplier_data['value']
            
            # Handle deliveryAddress which may be None
            address = ""
            if value.get('deliveryAddress') and isinstance(value.get('deliveryAddress'), dict):
                address = value.get('deliveryAddress', {}).get('addressLine1', '')
            
            # Create a new supplier
            supplier = Supplier.objects.create(
                tripletex_id=str(supplier_id),
                name=value.get('name', ''),
                organization_number=value.get('organizationNumber', ''),
                email=value.get('email', ''),
                phone_number=value.get('phoneNumber', ''),
                address=address,
                url=value.get('url', '')
            )
            print(f"Created new supplier: {supplier.name} (ID: {supplier_id})")
            return supplier
        
        return None

def get_or_create_account(account_id):
    """
    Get or create an Account object based on the account ID from Tripletex
    
    Args:
        account_id: The account ID from Tripletex
        
    Returns:
        Account: The account object, or None if it couldn't be found or created
    """
    if not account_id:
        return None
    
    # First try to find an existing account
    try:
        account = Account.objects.get(tripletex_id=str(account_id))
        return account
    except Account.DoesNotExist:
        # If not found, fetch data from Tripletex API
        account_data = get_account_info(account_id)
        
        if account_data and 'value' in account_data:
            value = account_data['value']
            
            # Create a new account
            account = Account.objects.create(
                tripletex_id=str(account_id),
                account_number=value.get('number', ''),
                name=value.get('name', ''),
                description=value.get('description', ''),
                account_type=value.get('type', ''),
                url=value.get('url', ''),
                is_active=value.get('active', True)
            )
            print(f"Created new account: {account.name} (ID: {account_id})")
            return account
        
        return None

def convert_bank_id_to_string(bank_id):
    """
    Convert a bank ID to its corresponding name from bank_account_map.json
    
    Args:
        bank_id: The bank account ID to look up
        
    Returns:
        str: The bank account name, or "Unknown" if not found
    """
    with open(os.path.join(get_current_directory(), 'bank_account_map.json')) as file:
        bank_account_map = json.load(file)
    
    # Convert bank_id to string for comparison
    bank_id_str = str(bank_id)
    
    for account in bank_account_map:
        if str(account["bank_id"]) == bank_id_str:
            return account["bank_name"]
    
    return "Unknown"

def get_bank_account_by_id(bank_id):
    """
    Get or create a BankAccount object based on the bank ID
    
    Args:
        bank_id: The bank account ID
        
    Returns:
        BankAccount: The bank account object, or None if it couldn't be found or created
    """
    # Convert bank_id to string
    bank_id_str = str(bank_id)
    
    try:
        # First try to find an existing bank account
        bank_account = BankAccount.objects.get(account_number=bank_id_str)
        return bank_account
    except BankAccount.DoesNotExist:
        # If not found, try to get the name from bank_account_map.json
        bank_name = convert_bank_id_to_string(bank_id)
        
        if bank_name != "Unknown":
            # Create a new bank account
            bank_account = BankAccount.objects.create(
                name=bank_name,
                account_number=bank_id_str,
                bank_name="Bank",
                account_type="Checking",
                is_active=True
            )
            print("Created new bank account: {} (ID: {})".format(bank_name, bank_id))
            return bank_account
    
    return None

def get_all_bank_statements(force_refresh=False, cache_days=30):
    """
    Fetch all bank statements from Tripletex using pagination to handle the 1000 transaction limit.
    Only uses cache if it contains at least 1000 transactions.
    
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
    
    # Get today's date and the cutoff date for latest statements
    today = datetime.datetime.now()
    latest_cutoff = today - datetime.timedelta(days=7)  # Consider last 7 days as "latest"
    
    while has_more:
        print(f"Fetching statements {from_index} to {from_index + count}...")
        
        params = {
            'from': from_index,
            'count': count
        }
        
        cache_key = f"bank_statements_{from_index}_{count}.json"
        cache_file = os.path.join(cache_dir, cache_key)
        
        # Check if we should use cached data
        use_cache = False
        if not force_refresh and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as file:
                    cached_data = json.load(file)
                    # Only use cache if it contains at least 1000 transactions
                    if cached_data.get("values") and len(cached_data["values"]) >= 1000:
                        cache_timestamp = os.path.getmtime(cache_file)
                        cache_datetime = datetime.datetime.fromtimestamp(cache_timestamp)
                        cache_age = datetime.datetime.now() - cache_datetime
                        
                        if cache_age.days < cache_days:
                            print(f"Using cached data for range {from_index}-{from_index+count} (age: {cache_age.seconds // 3600} hours)")
                            data = cached_data
                            use_cache = True
                        else:
                            print(f"Cache for range {from_index}-{from_index+count} is too old. Fetching fresh data...")
                    else:
                        print(f"Cache contains less than 1000 transactions. Fetching fresh data...")
            except Exception as e:
                print(f"Error reading cache file: {str(e)}. Will fetch fresh data.")
        
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
            
            data = response.json()
            
            # Only cache if we got at least 1000 transactions
            if len(data.get("values", [])) >= 1000:
                try:
                    with open(cache_file, 'w') as file:
                        json.dump(data, file)
                    print(f"Cached data for range {from_index}-{from_index+count}")
                except Exception as e:
                    print(f"Error saving cache file: {str(e)}")
            else:
                print(f"Not caching data with less than 1000 transactions from range {from_index}-{from_index+count}")
        
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
            
            # Get the bank account for this transaction
            account_id = processed_data.get("account_id")
            bank_account = None
            
            if account_id:
                # Try to get an existing bank account
                bank_account = get_bank_account_by_id(account_id)
            
            # Check if this transaction already exists in the database
            tripletex_id = str(transaction["id"])
            existing_transaction = None
            
            # Initialize supplier and ledger_account as None
            supplier = None
            ledger_account = None
            
            # If transaction has detailed_data and matchType is ONE_TRANSACTION_TO_ONE_POSTING,
            # extract supplier and account information
            if "detailed_data" in transaction and "value" in transaction["detailed_data"]:
                detailed_data = transaction["detailed_data"]["value"]
                
                if detailed_data.get("matchType") == "ONE_TRANSACTION_TO_ONE_POSTING":
                    # Process grouped postings to extract supplier and account data
                    grouped_postings = detailed_data.get("groupedPostings", [])
                    
                    if grouped_postings and len(grouped_postings) > 0:
                        # Use the first posting as the source of supplier and account info
                        first_posting = grouped_postings[0]
                        
                        # Get supplier data if available
                        if first_posting.get("supplier") and first_posting["supplier"].get("id"):
                            supplier_id = first_posting["supplier"]["id"]
                            supplier = get_or_create_supplier(supplier_id)
                        
                        # Get account data if available
                        if first_posting.get("account") and first_posting["account"].get("id"):
                            account_id = first_posting["account"]["id"]
                            ledger_account = get_or_create_account(account_id)
            
            try:
                existing_transaction = Transaction.objects.get(tripletex_id=tripletex_id)
                # Update the existing transaction
                existing_transaction.description = processed_data.get("description", "")
                existing_transaction.amount = processed_data.get("amount", 0)
                existing_transaction.date = datetime.datetime.strptime(statement.get("fromDate"), "%Y-%m-%d")
                existing_transaction.legacy_bank_account_id = processed_data.get("bank_account_name", "Unknown")
                existing_transaction.account_id = processed_data.get("account_id")
                existing_transaction.is_internal_transfer = processed_data.get("is_internal_transfer", False)
                existing_transaction.is_wage_transfer = processed_data.get("is_wage_transfer", False)
                existing_transaction.is_tax_transfer = processed_data.get("is_tax_transfer", False)
                existing_transaction.is_forbidden = processed_data.get("is_forbidden", False)
                existing_transaction.should_process = processed_data.get("should_process", False)
                
                # Set bank account if we have one
                if bank_account:
                    existing_transaction.bank_account = bank_account
                
                # Set supplier and ledger_account if available
                if supplier:
                    existing_transaction.supplier = supplier
                
                if ledger_account:
                    existing_transaction.ledger_account = ledger_account
                
                # Store complete transaction data as JSON
                raw_data = {
                    "transaction": transaction,
                    "detailed_data": transaction.get("detailed_data", {}),
                    "processed_data": processed_data,
                    "statement": {
                        "id": statement.get("id"),
                        "number": statement.get("number"),
                        "fromDate": statement.get("fromDate"),
                        "toDate": statement.get("toDate"),
                        "description": statement.get("description"),
                        "amount": statement.get("amount")
                    }
                }
                existing_transaction.raw_data = raw_data
                
                # Don't update category if it was already set to something other than the default
                if existing_transaction.category_id is None:
                    existing_transaction.category = default_category
                
                existing_transaction.save()
                transactions_updated += 1
                print(f"Transaction with tripletex_id {tripletex_id} updated.")
            except Transaction.DoesNotExist:
                # Create a new transaction
                # Store complete transaction data as JSON
                raw_data = {
                    "transaction": transaction,
                    "detailed_data": transaction.get("detailed_data", {}),
                    "processed_data": processed_data,
                    "statement": {
                        "id": statement.get("id"),
                        "number": statement.get("number"),
                        "fromDate": statement.get("fromDate"),
                        "toDate": statement.get("toDate"),
                        "description": statement.get("description"),
                        "amount": statement.get("amount")
                    }
                }
                
                new_transaction = Transaction(
                    tripletex_id=tripletex_id,
                    description=processed_data.get("description", ""),
                    amount=processed_data.get("amount", 0),
                    date=datetime.datetime.strptime(statement.get("fromDate"), "%Y-%m-%d"),
                    legacy_bank_account_id=processed_data.get("bank_account_name", "Unknown"),
                    account_id=processed_data.get("account_id"),
                    is_internal_transfer=processed_data.get("is_internal_transfer", False),
                    is_wage_transfer=processed_data.get("is_wage_transfer", False),
                    is_tax_transfer=processed_data.get("is_tax_transfer", False),
                    is_forbidden=processed_data.get("is_forbidden", False),
                    should_process=processed_data.get("should_process", False),
                    category=default_category,
                    raw_data=raw_data,
                    bank_account=bank_account,  # Set the bank account
                    supplier=supplier,  # Set the supplier
                    ledger_account=ledger_account  # Set the ledger account
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
            
            # Enhanced check for internal transfers - check both postings and description
            internal_transfer = (
                any(posting["description"] == "Intern overføring" for posting in transaction_posting) or
                "OPPGAVE Fra: Aviant AS" in transaction_description or
                "OVERFØRT Fra: AVIANT AS" in transaction_description or
                "Overføring mellom egne kontoer" in transaction_description or
                "Overføring til egen konto" in transaction_description or
                "Overføring fra egen konto" in transaction_description or
                "OPPGAVE KontoreguleringAviant AS" in transaction_description or
                "OPPGAVE Til: 4213.42.39535Aviant AS" in transaction_description
            )
            
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
 