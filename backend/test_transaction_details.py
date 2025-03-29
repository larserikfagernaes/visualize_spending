import os
import django
import json
import requests
from datetime import datetime
import time

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

# Import required models
from transactions.models import Transaction
from transactions.get_transactions import get_current_directory, get_details_for_transaction
from requests.auth import HTTPBasicAuth

# Get auth credentials from environment variables
TRIPLETEX_COMPANY_ID = os.getenv("3T_AUTH_USER")  # Default is 0 for the main company
TRIPLETEX_AUTH_TOKEN = os.getenv("3T_SESSION_TOKEN")  # Your session token

# Verify credentials
if not TRIPLETEX_AUTH_TOKEN:
    raise ValueError("3T_SESSION_TOKEN environment variable is not set. Please set it before running this script.")

def get_transaction_details_endpoint(trans_id):
    """
    Get transaction details using the /bank/statement/transaction/{id}/details endpoint
    """
    url = f"https://tripletex.no/v2/bank/statement/transaction/{trans_id}/details"
    
    payload={}
    # Use the correct authentication format
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
    
    try:
        response = requests.request("GET", url, data=payload, auth=auth)
        print(f"Response: {response.json()}")
        response.raise_for_status()
        response_data = response.json()
        print(f"Response structure: {json.dumps(response_data, indent=2)[:500]}...")  # Print first 500 chars of the response
        return response_data
    except Exception as e:
        print(f"Error fetching details for transaction {trans_id}: {str(e)}")
        return None

def compare_transaction_details(transaction_id):
    """
    Compare the data we currently have in the database with what the 
    /bank/statement/transaction/{id}/details endpoint provides
    """
    # Get the transaction from the database
    try:
        transaction = Transaction.objects.get(tripletex_id=transaction_id)
        print(f"\n===== Transaction ID: {transaction_id} =====")
        print(f"Description: {transaction.description}")
        print(f"Amount: {transaction.amount}")
        print(f"Date: {transaction.date}")
        print(f"Supplier: {transaction.supplier}")
        print(f"Ledger Account: {transaction.ledger_account}")
        
        # Check what we have in the raw_data
        raw_data = transaction.raw_data if transaction.raw_data else {}
        current_match_type = raw_data.get('detailed_data', {}).get('value', {}).get('matchType', 'Not available')
        print(f"Current matchType: {current_match_type}")
        
        # Get details from the current endpoint
        print("\n1. Current endpoint data:")
        standard_details = get_details_for_transaction(transaction_id)
        
        # Get details from the /details endpoint
        print("\n2. New /details endpoint data:")
        details_endpoint = get_transaction_details_endpoint(transaction_id)
        
        if details_endpoint and 'value' in details_endpoint:
            print(f"Successfully fetched data from /details endpoint")
            
            # Print the contents of the 'Detaljer' field if it exists
            details_value = details_endpoint['value']
            if 'Detaljer' in details_value:
                print(f"\nDetailed transaction info:")
                print(f"  - Detaljer: {details_value['Detaljer']}")
                
                # Check if this field contains any information about suppliers or accounts
                details_text = details_value['Detaljer']
                
                # Parse and analyze details_text
                # This is a simple check for potential supplier or account identifiers
                parts = details_text.split('?')
                
                print("\nParsed details:")
                for i, part in enumerate(parts):
                    if part.strip():
                        print(f"  - Part {i}: {part}")
                
                # Check for numbers that might be account numbers
                potential_accounts = []
                for part in parts:
                    # Look for numeric strings that could be account numbers
                    if part.isdigit() and len(part) >= 5:
                        potential_accounts.append(part)
                
                if potential_accounts:
                    print("\nPotential account numbers found:")
                    for acc in potential_accounts:
                        print(f"  - {acc}")
            else:
                print("No 'Detaljer' field found in the response")
        else:
            print("Could not fetch data from /details endpoint or no value field in response")
            
    except Transaction.DoesNotExist:
        print(f"Transaction with ID {transaction_id} not found in database")

# Main execution
if __name__ == "__main__":
    # Test both an OpenAI transaction and a transaction with supplier
    openai_tx = Transaction.objects.filter(
        description__icontains="OPENAI"
    ).first()
    
    with_supplier_tx = Transaction.objects.filter(
        supplier__isnull=False
    ).first()
    
    # Test transactions
    transactions_to_test = []
    
    if openai_tx:
        transactions_to_test.append(openai_tx.tripletex_id)
    else:
        print("No OpenAI transaction found")
        
    if with_supplier_tx:
        transactions_to_test.append(with_supplier_tx.tripletex_id)
    else:
        print("No transaction with supplier found")
    
    print(f"Testing {len(transactions_to_test)} transactions...")
    
    for tx_id in transactions_to_test:
        compare_transaction_details(tx_id)
        # Add a small delay to avoid rate limits
        time.sleep(1) 