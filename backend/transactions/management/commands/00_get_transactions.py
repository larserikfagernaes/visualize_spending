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
from django.core.management.base import BaseCommand

# Set up Django environment
# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

# Import models after Django setup
from transactions.models import Transaction, Category, BankStatement, BankAccount, Supplier, Account, TransactionAccount, LedgerPosting, CloseGroup, CloseGroupPosting

# Todos: 
# - Add automatic rolling of files_to_combine_with, now this has to be done manually

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def get_cache_directory():
    """
    Returns the path to the cache directory relative to the root of the server folder.
    This ensures a consistent cache location across the codebase.
    """
    # Get the path to the backend directory (server root)
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../'))
    # Create path to transactions/cache directory
    cache_dir = os.path.join(backend_dir, 'transactions', 'cache')
    
    # Create the directory if it doesn't exist
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        
    return cache_dir

def get_current_directory():
    """
    Returns the absolute directory path of the current file.
    This is useful for referencing files relative to this script.
    """
    return os.path.dirname(os.path.abspath(__file__))


# Now environment variables like TRIPLETEX_COMPANY_ID and TRIPLETEX_AUTH_TOKEN
# can be accessed using os.getenv()


from dotenv import load_dotenv
load_dotenv("/Users/larserik/Aviant/programming/visualise_spending/.env")

# Set up Tripletex API credentials
# These should be set in your environment or directly here for testing
TRIPLETEX_COMPANY_ID = os.getenv("3T_AUTH_USER")  # Default is 0 for the main company
TRIPLETEX_AUTH_TOKEN = os.getenv("3T_SESSION_TOKEN")  # Your session token

# Check if credentials are available
if not TRIPLETEX_AUTH_TOKEN:
    raise ValueError("TRIPLETEX_AUTH_TOKEN environment variable is not set. Please set it before running this script.")


def get_details_for_transaction(trans_id):
    cache_file = os.path.join(get_cache_directory(), "transaction_cache.json")

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



def process_voucher_accounts(voucher_id, processed_vouchers=None, debug=False):
    """
    Process a list of grouped postings from a transaction to extract account-related data.
    
    Args:
        voucher_id: The voucher ID to process
        processed_vouchers (list, optional): List of already processed voucher IDs
        debug (bool, optional): Enable debug mode for verbose output
        
    Returns:
        list: List of account objects with added posting information
    """
    if processed_vouchers is None:
        processed_vouchers = []
    processed_vouchers.append(voucher_id)

    account_postings_to_return = []

    voucher_data = get_voucher_details(voucher_id)
    
    if not voucher_data or not voucher_data.get("value") or not voucher_data["value"].get("postings"):
        return account_postings_to_return

    for posting in voucher_data["value"]["postings"]:
        if not posting.get("account") or not posting["account"].get("id"):
            continue
            
        account = get_or_create_account(posting["account"]["id"])
        if not account:
            continue
            
        # Add posting attributes to the account object
        account.posting_id = str(posting.get("id", ""))
        account.amount = posting.get("amountDefault", 0)
        account.is_debit = posting.get("amountDefault", 0) < 0
        account.voucher_id = str(voucher_id)
        account.description = posting.get("description", "")
        account.closeGroup = posting.get("closeGroup")
        
        if account.account_number not in [a.account_number for a in account_postings_to_return]:
            account_postings_to_return.append(account)
        
        if posting.get("closeGroup"):
            close_group = get_close_group_info(posting["closeGroup"]["id"])
            if close_group and close_group.get("value") and close_group["value"].get("postings"):
                for close_posting in close_group["value"]["postings"]:
                    posting_details = fetch_posting_details_direct(close_posting["id"])
                    if posting_details and posting_details.get("voucher") and posting_details["voucher"].get("id"):
                        new_voucher_id = posting_details["voucher"]["id"]
                        if new_voucher_id not in processed_vouchers:
                            new_account_postings = process_voucher_accounts(new_voucher_id, processed_vouchers=processed_vouchers, debug=debug)
                            for new_account in new_account_postings:
                                if new_account.account_number not in [a.account_number for a in account_postings_to_return]:
                                    account_postings_to_return.append(new_account)
    
    return account_postings_to_return

def debug_transaction_path(transaction_id):
    """
    Debug the processing path for a specific transaction.
    This function fetches the transaction details, processes the postings,
    and displays the accounts that would be created.
    
    Args:
        transaction_id (int): Tripletex ID of the transaction to debug
    """
    print(f"Debug mode: Analyzing transaction {transaction_id}")
    
    # Check if transaction exists in database first
    try:
        transaction = Transaction.objects.get(tripletex_id=str(transaction_id))
        print(f"Transaction found in database: {transaction.description} ({transaction.date})")
        print(f"Amount: {transaction.amount}")
        
        if transaction.ledger_account:
            print(f"Linked ledger account: {transaction.ledger_account.tripletex_id} - {transaction.ledger_account.name}")
        else:
            print("No ledger account linked")
            
        # Get related accounts through TransactionAccount
        related_accounts = transaction.accounts.all()
        print(f"\nRelated accounts: {related_accounts.count()}")
        for account in related_accounts:
            print(f"Account {account.tripletex_id}: {account.name} - {account.account_number}")
            
    except Transaction.DoesNotExist:
        print("Transaction not in database. Fetching directly from Tripletex...")
    
    # Fetch transaction details from Tripletex
    transaction_data = get_details_for_transaction(str(transaction_id))
    
    if not transaction_data or not transaction_data.get("value"):
        print(f"Could not fetch details for transaction {transaction_id}")
        return
    
    # Extract data from the response
    value = transaction_data["value"]
    
    print("\nTripletex Transaction Data:")
    print(f"Description: {value.get('description')}")
    print(f"Amount: {value.get('amountCurrency')}")
    print(f"Date: {value.get('date')}")
    
    # Get postings from the transaction
    grouped_postings = value.get("groupedPostings", [])
    
    if not grouped_postings:
        print("No grouped postings found for this transaction")
        return
    
    print(f"\nFound {len(grouped_postings)} grouped postings")
    
    for i, posting in enumerate(grouped_postings):
        print(f"\nPosting {i+1}:")
        print(f"Description: {posting.get('description')}")
        print(f"Amount: {posting.get('amountDefault')}")
        
        if posting.get("account") and posting["account"].get("id"):
            account_id = posting["account"]["id"]
            print(f"Account ID: {account_id}")
            
            # Check if the account matches our target account (66775225)
            if str(account_id) == "66775225":
                print("*** THIS POSTING IS LINKED TO ACCOUNT 66775225 (Driftsmateriale) ***")
                
            # Get account details if possible
            account = Account.objects.filter(tripletex_id=str(account_id)).first()
            if account:
                print(f"Account in DB: {account.name} ({account.account_number})")
            else:
                print("Account not found in database")
        else:
            print("No account information in this posting")
    
    # Process the accounts that would be created
    print("\nProcess voucher accounts output:")
    if grouped_postings and len(grouped_postings) > 0:
        first_posting = grouped_postings[0]
        if first_posting.get("voucher") and first_posting["voucher"].get("id"):
            first_voucher_id = first_posting["voucher"]["id"]
            account_postings = process_voucher_accounts(first_voucher_id, processed_vouchers=None, debug=True)
        else:
            account_postings = []
    print("--------------------------------")
    print(account_postings)
    print("--------------------------------")
    

def get_supplier_info(supplier_id):
    """
    Fetch supplier information from Tripletex API
    
    Args:
        supplier_id: The ID of the supplier in Tripletex
        
    Returns:
        dict: Supplier data from the API
    """
    # Get the cache directory
    cache_dir = get_cache_directory()
    
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
    # Get the cache directory
    cache_dir = get_cache_directory()
    
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
        # Special case for account 66775225 (Driftsmateriale) - create it without API call for testing
        if str(account_id) == "66775225":
            account = Account.objects.create(
                tripletex_id=str(account_id),
                account_number="6540",
                name="Driftsmateriale",
                description="Driftstilbehør og materialer",
                account_type="EXPENSE",
                url="",
                is_active=True,
                closeGroup=None
            )
            print(f"Created special test account: {account.name} (ID: {account_id})")
            return account
        
        # If not found, fetch data from Tripletex API
        account_data = get_account_info(account_id)
        
        if account_data and 'value' in account_data:
            
            value = account_data['value']
            
            # Check if this account has a closeGroup and make sure it exists
            close_group_id = value.get('closeGroup')
            if close_group_id:
                get_close_group_info(close_group_id)
            
            # Create a new account
            account = Account.objects.create(
                tripletex_id=str(account_id),
                account_number=value.get('number', ''),
                name=value.get('name', ''),
                description=value.get('description', ''),
                account_type=value.get('type', ''),
                url=value.get('url', ''),
                is_active=value.get('active', True),
                closeGroup=close_group_id
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
    with open(os.path.join(get_cache_directory(), 'bank_account_map.json')) as file:
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
    cache_dir = get_cache_directory()
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

def save_transactions_to_database(data, debug=False):
    """
    Save processed transactions to the database
    
    Args:
        data (dict): Dictionary containing bank statements data with processed transactions
        debug (bool): Enable debug mode for verbose output
    
    Returns:
        tuple: (transactions_saved, transactions_skipped, transactions_updated)
    """
    transactions_saved = 0
    transactions_skipped = 0
    transactions_updated = 0
    accounts_linked = 0
    special_links_created = 0
    duplicate_entries_skipped = 0
    
    # Get or create a default category for uncategorized transactions
    default_category, _ = Category.objects.get_or_create(
        name="Uncategorized",
        defaults={"description": "Default category for uncategorized transactions"}
    )
    
    # Define account mappings for special transaction handling
    # Format: Account ID -> [{keyword pattern, description pattern}, ...]
    SPECIAL_ACCOUNT_MAPPINGS = {
        "66775225": [  # Driftsmateriale account
            {"keywords": ["BILTEMA", "LTEMA"], "description": "Auto-linked to Driftsmateriale (maintenance supplies)"}
        ],
        # Add more account mappings as needed
    }
    
    # Cache accounts for special mappings to avoid repeated lookups
    special_accounts = {}
    for account_id in SPECIAL_ACCOUNT_MAPPINGS:
        try:
            special_accounts[account_id] = Account.objects.get(tripletex_id=account_id)
            if debug:
                print(f"Loaded special account {account_id}: {special_accounts[account_id].name}")
        except Account.DoesNotExist:
            if debug:
                print(f"Warning: Special account {account_id} not found in database")
    
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
            raw_data = transaction["raw_data"]
            
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
            
            # Collection to store all account postings for this transaction
            account_postings = []
            
            # If transaction has detailed_data and matchType is ONE_TRANSACTION_TO_ONE_POSTING,
            # extract supplier and account information
            if "detailed_data" in transaction and "value" in transaction["detailed_data"]:
                detailed_data = transaction["detailed_data"]["value"]
                
                if detailed_data.get("matchType") == "ONE_TRANSACTION_TO_ONE_POSTING" or detailed_data.get("matchType") == "MANY_TRANSACTIONS_TO_ONE_POSTING" or detailed_data.get("matchType") == "MANY_TRANSACTIONS_TO_MANY_POSTINGS":
                    # Process grouped postings to extract supplier and account data
                    grouped_postings = detailed_data.get("groupedPostings", [])
                    
                    if grouped_postings and len(grouped_postings) > 0:
                        # Use the first posting as the source of supplier and account info for the main ledger_account
                        first_posting = grouped_postings[0]
                        
                        # Get supplier data if available
                        if first_posting.get("supplier") and first_posting["supplier"].get("id"):
                            supplier_id = first_posting["supplier"]["id"]
                            supplier = get_or_create_supplier(supplier_id)
                        
                        # Get account data for the main ledger_account if available
                        if first_posting.get("account") and first_posting["account"].get("id"):
                            account_id = first_posting["account"]["id"]
                            ledger_account = get_or_create_account(account_id)
                        account_postings = []
                        for posting in grouped_postings:
                            if posting.get("voucher") and posting["voucher"].get("id"):
                                voucher_id = posting["voucher"]["id"]
                                account_postings = process_voucher_accounts(voucher_id, processed_vouchers=None, debug=debug)
                                account_postings.extend(account_postings)
                        
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
                existing_transaction.raw_data = raw_data
                
                # Don't update category if it was already set to something other than the default
                if existing_transaction.category_id is None:
                    existing_transaction.category = default_category
                
                existing_transaction.save()
                
                # First, remove existing TransactionAccount relationships to rebuild them
                # But wrap in try/except to handle potential database errors
                try:
                    existing_transaction.transaction_accounts.all().delete()
                except Exception as e:
                    if debug:
                        print(f"Error removing existing transaction accounts: {e}")
                
                # Create account postings for this transaction
                for posting in account_postings:
                    try:
                        # Use update_or_create to handle potential duplicates
                        ta, created = TransactionAccount.objects.update_or_create(
                            transaction=existing_transaction,
                            account=posting,  # Now posting is the account object directly
                            posting_id=getattr(posting, "posting_id", ""),
                            defaults={
                                'amount': getattr(posting, "amount", 0),
                                'is_debit': getattr(posting, "is_debit", False),
                                'voucher_id': getattr(posting, "voucher_id", ""),
                                'description': getattr(posting, "description", "")
                            }
                        )
                        
                        if created:
                            accounts_linked += 1
                        else:
                            duplicate_entries_skipped += 1
                            if debug:
                                print(f"Updated existing TransactionAccount for transaction {tripletex_id}, account {posting.tripletex_id}")
                    except Exception as e:
                        if debug:
                            print(f"Error creating TransactionAccount: {e}")
                    
                    # Create or update a LedgerPosting for each transaction account
                    posting_id = getattr(posting, "posting_id", "")
                    if posting_id:
                        try:
                            LedgerPosting.objects.update_or_create(
                                posting_id=int(posting_id) if posting_id.isdigit() else 0,
                                defaults={
                                    'date': existing_transaction.date,
                                    'description': getattr(posting, "description", ""),
                                    'amount': getattr(posting, "amount", 0),
                                    'supplier': supplier,
                                    'account': posting,  # Now posting is the account object directly
                                    'voucher_id': int(getattr(posting, "voucher_id", 0)) if getattr(posting, "voucher_id", "").isdigit() else None,
                                    'closeGroup': getattr(posting, "closeGroup", None),  # Store closeGroup in LedgerPosting
                                    'raw_data': None  # We don't have the raw data here
                                }
                            )
                        except Exception as e:
                            if debug:
                                print(f"Error creating/updating LedgerPosting: {e}")
                
                # Apply special account linking rules
                special_links = apply_special_account_rules(
                    existing_transaction, 
                    special_accounts,
                    SPECIAL_ACCOUNT_MAPPINGS,
                    debug
                )
                special_links_created += special_links
                
                transactions_updated += 1
                print(f"Transaction with tripletex_id {tripletex_id} updated.")
            except Transaction.DoesNotExist:
                # Create a new transaction
                # Store complete transaction data as JSON
                
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
                
                # Create account postings for this transaction
                for posting in account_postings:
                    try:
                        # Use update_or_create to handle potential duplicates
                        ta, created = TransactionAccount.objects.update_or_create(
                            transaction=new_transaction,
                            account=posting,  # Now posting is the account object directly
                            posting_id=getattr(posting, "posting_id", ""),
                            defaults={
                                'amount': getattr(posting, "amount", 0),
                                'is_debit': getattr(posting, "is_debit", False),
                                'voucher_id': getattr(posting, "voucher_id", ""),
                                'description': getattr(posting, "description", "")
                            }
                        )
                        
                        if created:
                            accounts_linked += 1
                        else:
                            duplicate_entries_skipped += 1
                            if debug:
                                print(f"Updated existing TransactionAccount for transaction {tripletex_id}, account {posting.tripletex_id}")
                    except Exception as e:
                        if debug:
                            print(f"Error creating TransactionAccount: {e}")
                    
                    # Create or update a LedgerPosting for each transaction account
                    posting_id = getattr(posting, "posting_id", "")
                    if posting_id:
                        try:
                            LedgerPosting.objects.update_or_create(
                                posting_id=int(posting_id) if posting_id.isdigit() else 0,
                                defaults={
                                    'date': new_transaction.date,
                                    'description': getattr(posting, "description", ""),
                                    'amount': getattr(posting, "amount", 0),
                                    'supplier': supplier,
                                    'account': posting,  # Now posting is the account object directly
                                    'voucher_id': int(getattr(posting, "voucher_id", 0)) if getattr(posting, "voucher_id", "").isdigit() else None,
                                    'closeGroup': getattr(posting, "closeGroup", None),  # Store closeGroup in LedgerPosting
                                    'raw_data': None  # We don't have the raw data here
                                }
                            )
                        except Exception as e:
                            if debug:
                                print(f"Error creating/updating LedgerPosting: {e}")
                
                # Apply special account linking rules
                special_links = apply_special_account_rules(
                    new_transaction, 
                    special_accounts,
                    SPECIAL_ACCOUNT_MAPPINGS,
                    debug
                )
                special_links_created += special_links
                
                transactions_saved += 1
            
            if (transactions_saved + transactions_updated) % 100 == 0 and (transactions_saved + transactions_updated) > 0:
                print(f"Processed {transactions_saved + transactions_updated} transactions ({transactions_saved} new, {transactions_updated} updated)...")
    
    print(f"Database import complete. Saved {transactions_saved} new transactions. Updated {transactions_updated} existing transactions. Skipped {transactions_skipped} transactions.")
    print(f"Linked {accounts_linked} regular accounts and {special_links_created} special accounts to transactions.")
    print(f"Skipped {duplicate_entries_skipped} duplicate account entries.")
    return transactions_saved, transactions_skipped, transactions_updated

def apply_special_account_rules(transaction, special_accounts, account_mappings, debug=False):
    """
    Apply special account linking rules to connect transactions to specific accounts
    based on custom business criteria.
    
    Args:
        transaction (Transaction): The transaction to process
        special_accounts (dict): Dictionary of special accounts by ID
        account_mappings (dict): Dictionary of account ID to patterns mapping
        debug (bool): Enable debug mode for verbose output
        
    Returns:
        int: Number of special account links created
    """
    links_created = 0
    description = transaction.description.upper()
    
    # Skip processing if transaction is an internal transfer, wage, or tax
    if transaction.is_internal_transfer or transaction.is_wage_transfer or transaction.is_tax_transfer:
        if debug:
            print(f"Skipping special account rules for {transaction.tripletex_id}: internal/wage/tax transfer")
        return links_created
    
    # Check each special account's rules
    for account_id, patterns in account_mappings.items():
        account = special_accounts.get(account_id)
        if not account:
            continue
            
        # Check if this transaction already has a link to this account
        existing_link = TransactionAccount.objects.filter(
            transaction=transaction,
            account=account
        ).exists()
        
        if existing_link:
            if debug:
                print(f"Transaction {transaction.tripletex_id} already linked to account {account_id}")
            continue
        
        # Check if any pattern matches
        for pattern in patterns:
            keywords = pattern.get("keywords", [])
            if not isinstance(keywords, list):
                keywords = [keywords]
            
            # Check if any keyword is in the description
            matches = False
            for keyword in keywords:
                if keyword.upper() in description:
                    matches = True
                    break
            
            if matches:
                # Create a TransactionAccount link
                amount = abs(transaction.amount)
                is_debit = transaction.amount < 0
                pattern_desc = pattern.get("description", "Auto-linked account")
                
                try:
                    # Use update_or_create instead of create to handle potential duplicates
                    posting_id = f"special_{transaction.tripletex_id}_{account_id}"
                    ta, created = TransactionAccount.objects.update_or_create(
                        transaction=transaction,
                        account=account,
                        posting_id=posting_id,
                        defaults={
                            'amount': amount,
                            'is_debit': is_debit,
                            'description': pattern_desc,
                            'voucher_id': ""
                        }
                    )
                    
                    if created:
                        links_created += 1
                        if debug:
                            print(f"Created special link: Transaction {transaction.tripletex_id} to account {account.name} ({account_id})")
                            print(f"  Match: {description} contains keyword from {keywords}")
                    else:
                        if debug:
                            print(f"Updated existing special link for transaction {transaction.tripletex_id}, account {account_id}")
                except Exception as e:
                    if debug:
                        print(f"Error creating special account link: {e}")
                
                # Only create one link per account type
                break
    
    return links_created

def get_voucher_details(voucher_id):
    """
    Fetch voucher details from Tripletex API
    
    Args:
        voucher_id: The ID of the voucher in Tripletex
        
    Returns:
        dict: Voucher data from the API including all postings
    """
    cache_dir = get_cache_directory()
    cache_file = os.path.join(cache_dir, f"voucher_{voucher_id}.json")
    
    # Check if cache file exists and is recent (less than 7 days old)
    if os.path.exists(cache_file):
        file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))
        if file_age.days < 365:  # Cache is valid for 7 days
            with open(cache_file) as file:
                try:
                    voucher_data = json.load(file)
                    return voucher_data
                except json.JSONDecodeError:
                    # If the file is corrupted, fetch fresh data
                    pass
    
    # Fetch from API if not in cache or cache is too old
    url = f"https://tripletex.no/v2/ledger/voucher/{voucher_id}?fields=postings"
    
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
    
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        voucher_data = response.json()
        
        # Cache the data
        with open(cache_file, 'w') as file:
            json.dump(voucher_data, file)
        
        return voucher_data
    except Exception as e:
        print(f"Error fetching voucher data for ID {voucher_id}: {str(e)}")
        return None

def get_close_group_postings(close_group):
    """
    Fetch postings for a specific close group from Tripletex API
    
    Args:
        close_group: The close group identifier
        
    Returns:
        list: List of postings in the close group
    """
    # Track close groups that have given 404 errors to avoid repeated API calls
    if not hasattr(get_close_group_postings, 'not_found_groups'):
        get_close_group_postings.not_found_groups = set()
    
    # Skip API call if we already know this closeGroup returns 404
    if close_group in get_close_group_postings.not_found_groups:
        return []
    
    cache_dir = get_cache_directory()
    cache_file = os.path.join(cache_dir, f"close_group_{close_group}.json")
    
    # Check if cache file exists and is recent (less than 7 days old)
    if os.path.exists(cache_file):
        file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))
        if file_age.days < 365:  # Cache is valid for 1 year
            with open(cache_file) as file:
                try:
                    close_group_data = json.load(file)
                    # Process the data based on its structure
                    if 'value' in close_group_data:
                        if isinstance(close_group_data.get('value'), list):
                            return close_group_data.get('value', [])
                        # For the new API format where 'value' contains postings with ids
                        elif isinstance(close_group_data.get('value'), dict):
                            value = close_group_data.get('value')
                            
                            # Check for postingIds array first (previous format)
                            if 'postingIds' in value:
                                posting_ids = value['postingIds']
                                posting_objects = []
                                
                                # Create synthetic posting objects with just enough info for processing
                                for posting_id in posting_ids:
                                    posting_objects.append({
                                        "id": posting_id,
                                        "posting_id": posting_id,  # Add this field for compatibility
                                        "needs_details": True      # Flag that this is a simplified object
                                    })
                                
                                return posting_objects
                                
                            # Check for postings array with id objects (current format)
                            elif 'postings' in value and isinstance(value['postings'], list):
                                posting_objects = []
                                
                                # Create synthetic posting objects from the postings array
                                for posting in value['postings']:
                                    if isinstance(posting, dict) and 'id' in posting:
                                        posting_id = posting['id']
                                        posting_objects.append({
                                            "id": posting_id,
                                            "posting_id": posting_id,  # Add this field for compatibility
                                            "needs_details": True      # Flag that this is a simplified object
                                        })
                                    elif isinstance(posting, (str, int)):
                                        # Handle if it's just an ID
                                        posting_objects.append({
                                            "id": posting,
                                            "posting_id": posting,
                                            "needs_details": True
                                        })
                    return []
                except json.JSONDecodeError:
                    # If the file is corrupted, fetch fresh data
                    pass
    
    # Fetch from API if not in cache or cache is too old
    url = f"https://tripletex.no/v2/ledger/closeGroup/{close_group}"
    
    # Use the correct authentication format
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
    
    try:
        response = requests.get(url, auth=auth)
        
        # Handle 404 errors separately - these are expected in some cases
        if response.status_code == 404:
            # Add to not found groups to avoid trying again
            get_close_group_postings.not_found_groups.add(close_group)
            # Print a less alarming message
            print(f"CloseGroup {close_group} not found (404)")
            return []
            
        # For other errors, raise normally
        response.raise_for_status()
        
        close_group_data = response.json()
        
        # Cache the data
        with open(cache_file, 'w') as file:
            json.dump(close_group_data, file)
        
        # Process the data based on its structure
        if 'value' in close_group_data:
            if isinstance(close_group_data.get('value'), list):
                return close_group_data.get('value', [])
            # For the new API format where 'value' contains postings with ids
            elif isinstance(close_group_data.get('value'), dict):
                value = close_group_data.get('value')
                
                # Check for postingIds array first (previous format)
                if 'postingIds' in value:
                    posting_ids = value['postingIds']
                    posting_objects = []
                    
                    # Create synthetic posting objects with just enough info for processing
                    for posting_id in posting_ids:
                        posting_objects.append({
                            "id": posting_id,
                            "posting_id": posting_id,  # Add this field for compatibility
                            "needs_details": True      # Flag that this is a simplified object
                        })
                    
                    return posting_objects
                    
                # Check for postings array with id objects (current format)
                elif 'postings' in value and isinstance(value['postings'], list):
                    posting_objects = []
                    
                    # Create synthetic posting objects from the postings array
                    for posting in value['postings']:
                        if isinstance(posting, dict) and 'id' in posting:
                            posting_id = posting['id']
                            posting_objects.append({
                                "id": posting_id,
                                "posting_id": posting_id,  # Add this field for compatibility
                                "needs_details": True      # Flag that this is a simplified object
                            })
                        elif isinstance(posting, (str, int)):
                            # Handle if it's just an ID
                            posting_objects.append({
                                "id": posting,
                                "posting_id": posting,
                                "needs_details": True
                            })
            
        return []
    except requests.exceptions.HTTPError as e:
        if '404' in str(e):
            # Add to not found groups to avoid trying again
            get_close_group_postings.not_found_groups.add(close_group)
            # For 404 errors, just return empty list
            print(f"CloseGroup {close_group} not found (404)")
            return []
        else:
            # For other errors, log but continue
            print(f"Error fetching close group data for {close_group}: {str(e)}")
            return []
    except Exception as e:
        print(f"Error fetching close group data for {close_group}: {str(e)}")
        return []

def fetch_posting_details_direct(posting_id):
    """
    Directly fetch details for a specific posting from the API
    """
    if not posting_id:
        return None
        
    # Check cache first
    cache_dir = get_cache_directory()
    cache_file = os.path.join(cache_dir, f"posting_{posting_id}.json")
    
    # Check if cache file exists and is recent
    if os.path.exists(cache_file):
        file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))
        if file_age.days < 365:  # Cache is valid for 365 days
            with open(cache_file) as file:
                try:
                    posting_data = json.load(file)
                    
                    # If the data is already processed, return it directly
                    if isinstance(posting_data, dict) and 'voucher_id' in posting_data:
                        return posting_data
                    
                    # Otherwise check for value in the response
                    if 'value' in posting_data:
                        value = posting_data['value']
                        
                        # Create processed result with explicit voucher_id
                        result = value.copy()
                        
                        # Add explicit voucher_id field for easier access
                        if value.get('voucher') and isinstance(value['voucher'], dict) and 'id' in value['voucher']:
                            result['voucher_id'] = value['voucher']['id']
                        
                        return result
                except json.JSONDecodeError:
                    # If the file is corrupted, fetch fresh data
                    pass
    
    # If not in cache or cache invalid, fetch from API
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN) 
    try:
        url = f"https://tripletex.no/v2/ledger/posting/{posting_id}"
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        data = response.json()
        
        # Cache the raw response
        with open(cache_file, 'w') as file:
            json.dump(data, file)
        
        if 'value' in data:
            # Extract the value section for easier processing
            value = data['value']
            
            # Create a processed result that includes the voucher_id explicitly
            # This ensures consistent usage across the codebase
            result = value.copy()  # Copy the original data
            
            # Add explicit voucher_id field for easier access
            if value.get('voucher') and isinstance(value['voucher'], dict) and 'id' in value['voucher']:
                result['voucher_id'] = value['voucher']['id']
            
            return result
        return None
    except Exception as e:
        print(f"Error fetching posting data for ID {posting_id}: {str(e)}")
        return None

def get_close_group_info(close_group_id):
    """
    Fetch close group information from Tripletex API
    
    Args:
        close_group_id: The ID of the close group in Tripletex
        
    Returns:
        dict: Close group data from the API
    """
    # Get the cache directory
    cache_dir = get_cache_directory()
    
    cache_file = os.path.join(cache_dir, f"close_group_info_{close_group_id}.json")
    
    # Check if cache file exists and is recent (less than 7 days old)
    if os.path.exists(cache_file):
        file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))
        if file_age.days < 365:  # Cache is valid for 365 days
            with open(cache_file) as file:
                try:
                    close_group_data = json.load(file)
                    return close_group_data
                except json.JSONDecodeError:
                    # If the file is corrupted, fetch fresh data
                    pass
    
    # Fetch from API if not in cache or cache is too old
    url = f"https://tripletex.no/v2/ledger/closeGroup/{close_group_id}"
    print("SEDING REQUEST, close group") 
    # Use the correct authentication format
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
    
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        close_group_data = response.json()
        
        # Cache the data
        with open(cache_file, 'w') as file:
            json.dump(close_group_data, file)
        
        return close_group_data
    except Exception as e:
        print(f"Error fetching close group data for ID {close_group_id}: {str(e)}")
        return None

def create_posting(transaction, posting_data):
    """
    Create a LedgerPosting object from tripletex data
    
    Args:
        transaction: parent Transaction object
        posting_data: dict of posting data from tripletex
    """
    if not transaction or not posting_data:
        return None
        
    posting_id = posting_data.get('id', 0)
    if not posting_id:
        return None
        
    try:
        # Check if posting already exists
        posting = LedgerPosting.objects.filter(posting_id=posting_id).first()
        if posting:
            return posting
            
        # Parse data
        amount = posting_data.get('amount', 0.0)
        account_id = posting_data.get('account', {}).get('number')
        account = get_account(account_id) if account_id else None
        
        date = None
        date_str = posting_data.get('date')
        if date_str:
            try:
                date = parse_date(date_str)
            except:
                pass
                
        supplier_id = posting_data.get('customer', {}).get('id')
        supplier = None
        if supplier_id:
            supplier = get_or_create_supplier(supplier_id)
            
        close_group_id = posting_data.get('closeGroup')
        close_group = None
        if close_group_id:
            close_group = get_close_group_info(close_group_id)
            
        # Create new posting
        posting = LedgerPosting.objects.create(
            transaction=transaction,
            posting_id=posting_id,
            date=date or transaction.transaction_date,
            amount=amount,
            description=posting_data.get('description', ''),
            account=account,
            supplier=supplier,
            transaction_id=posting_data.get('transactionId', 0),
            invoice_number=posting_data.get('invoiceNumber', ''),
            system_id=posting_data.get('systemId', ''),
            row=posting_data.get('row', 0)
        )
        
        # Create relationship with close group if it exists
        if close_group:
            CloseGroupPosting.objects.get_or_create(
                close_group=close_group,
                posting=posting
            )
            
        return posting
    except Exception as e:
        print(f"Error creating posting {posting_id}: {str(e)}")
        return None

class Command(BaseCommand):
    help = 'Fetch and process bank transactions from Tripletex'
    
    def add_arguments(self, parser):
        parser.add_argument('--force-refresh', action='store_true', help='Force refresh of bank statements data')
        parser.add_argument('--cache-days', type=int, default=1, help='Number of days to consider cache valid')
        parser.add_argument('--save-to-db', action='store_true', help='Save processed transactions to the database')
        parser.add_argument('--debug-transaction', type=int, help='Debug a specific transaction by ID')
        parser.add_argument('--debug', action='store_true', help='Enable debug mode for verbose output')
    
    def handle(self, *args, **options):
        print(f"Starting bank transaction processing...")
        print(f"Force refresh: {options['force_refresh']}")
        print(f"Cache validity: {options['cache_days']} days")
        print(f"Save to database: {options['save_to_db']}")
        print(f"Debug mode: {options.get('debug', False)}")
        
        # Debug a specific transaction if requested
        if options.get('debug_transaction'):
            debug_transaction_path(options['debug_transaction'])
            return
        
        # Ensure cache directory exists
        cache_dir = get_cache_directory()
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # Get all bank statements with caching
        data = get_all_bank_statements(force_refresh=options['force_refresh'], cache_days=options['cache_days'])
        
        # Initialize cache for transaction details
        cache_transaction_file = os.path.join(get_cache_directory(), "transaction_cache.json")
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
                transaction["raw_data"] = transaction_data

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
                    "OPPGAVE Til: 4213.42.39535Aviant AS" in transaction_description or
                    "1506.62.62666" in transaction_description or
                    "4213.42.39500" in transaction_description or
                    "1506.47.46844" in transaction_description 
                )
                
                # Check for wage transfers based on posting match type or specific names in description
                wage_transfer = (
                    any(posting["postingMatchType"] == "WAGE" for posting in transaction_posting) or
                    "FRETHEIM NAVIGATION" in transaction_description or
                    "Pierro Cristina" in transaction_description or
                    "MUSTAFA SARPER" in transaction_description or
                    "V43175?35EUR 4.744,00" in transaction_description or
                    "OPPGAVE Til: Marcus rjehagMarcus Örjehag" in transaction_description
                )
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
        if options['save_to_db']:
            transactions_saved, transactions_skipped, transactions_updated = save_transactions_to_database(data, options['debug'])
            print(f"\nDatabase Summary:")
            print(f"Transactions saved: {transactions_saved}")
            print(f"Transactions updated: {transactions_updated}")
            print(f"Transactions skipped: {transactions_skipped}")
        else:
            print("\nSkipping database import. Use --save-to-db flag to save transactions.")
 