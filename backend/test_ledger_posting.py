#!/usr/bin/env python3
"""
Script to test the '/ledger/posting' endpoint from Tripletex API
to explore how to link transactions with suppliers.
"""

import os
import json
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from dotenv import load_dotenv
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import Transaction, Supplier, Account

# Load environment variables
load_dotenv()

# Authentication variables
TRIPLETEX_COMPANY_ID = os.getenv("3T_AUTH_USER")
TRIPLETEX_AUTH_TOKEN = os.getenv("3T_SESSION_TOKEN")

# Check if credentials are available
if not TRIPLETEX_AUTH_TOKEN:
    raise ValueError("TRIPLETEX_AUTH_TOKEN environment variable is not set. Please set it before running this script.")

def get_ledger_postings(date_from=None, date_to=None, limit=100, include_supplier=True, include_account=True):
    """
    Query the ledger/posting endpoint to retrieve posting information.
    
    Args:
        date_from: Start date for filtering postings (default: 30 days ago)
        date_to: End date for filtering postings (default: today)
        limit: Maximum number of results to return
        include_supplier: Whether to include supplier information
        include_account: Whether to include account information
    
    Returns:
        The API response with posting data
    """
    # Set default dates if not provided
    if date_from is None:
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if date_to is None:
        date_to = datetime.now().strftime("%Y-%m-%d")
    
    # Build URL with query parameters
    base_url = "https://tripletex.no/v2/ledger/posting"
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "from": 0,
        "count": limit,
        "fields": "id,date,description,amount,supplier,account,voucher"
    }
    
    # Prepare authentication
    auth = HTTPBasicAuth(TRIPLETEX_COMPANY_ID, TRIPLETEX_AUTH_TOKEN)
    
    # Make API request
    print(f"Fetching ledger postings from {date_from} to {date_to}...")
    response = requests.get(base_url, params=params, auth=auth)
    
    # Check if request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def analyze_postings_and_transactions():
    """
    Analyze the relationship between ledger postings and transactions,
    focusing on supplier relationships.
    """
    # Get ledger postings
    postings_data = get_ledger_postings(limit=20)
    
    if not postings_data or 'values' not in postings_data:
        print("No postings data found.")
        return
    
    postings = postings_data['values']
    print(f"Retrieved {len(postings)} ledger postings.")
    
    # Save the first posting's full data for reference
    if postings:
        with open('posting_example.json', 'w') as f:
            json.dump(postings[0], f, indent=2)
        print(f"Saved example posting to posting_example.json")
    
    # Analyze the relationships between postings and transactions
    for i, posting in enumerate(postings[:5]):  # Analyze first 5 postings
        posting_id = posting.get('id')
        supplier_data = posting.get('supplier')
        account_data = posting.get('account')
        voucher_data = posting.get('voucher')
        
        print(f"\n--- Posting {i+1} ---")
        print(f"ID: {posting_id}")
        print(f"Date: {posting.get('date')}")
        print(f"Description: {posting.get('description')}")
        print(f"Amount: {posting.get('amount')}")
        
        # Display voucher information if available
        if voucher_data:
            voucher_id = voucher_data.get('id')
            voucher_number = voucher_data.get('number', 'Unknown')
            print(f"Voucher: #{voucher_number} (ID: {voucher_id})")
        
        # Check if this posting has supplier information
        if supplier_data:
            supplier_id = supplier_data.get('id')
            supplier_name = supplier_data.get('name', 'Unknown')
            print(f"Supplier: {supplier_name} (ID: {supplier_id})")
            
            # Check if this supplier exists in our database
            try:
                supplier = Supplier.objects.get(tripletex_id=str(supplier_id))
                print(f"  ✅ Supplier found in database: {supplier}")
                
                # Find transactions with this supplier
                transactions = Transaction.objects.filter(supplier=supplier)
                print(f"  Number of transactions with this supplier: {transactions.count()}")
            except Supplier.DoesNotExist:
                print(f"  ❌ Supplier not found in database")
        else:
            print("No supplier information for this posting")
        
        # Check if this posting has account information
        if account_data:
            account_id = account_data.get('id')
            account_name = account_data.get('name', 'Unknown')
            account_number = account_data.get('number', 'Unknown')
            print(f"Account: {account_number} - {account_name} (ID: {account_id})")
            
            # Check if this account exists in our database
            try:
                account = Account.objects.get(tripletex_id=str(account_id))
                print(f"  ✅ Account found in database: {account}")
                
                # Find transactions with this account
                transactions = Transaction.objects.filter(ledger_account=account)
                print(f"  Number of transactions with this account: {transactions.count()}")
            except Account.DoesNotExist:
                print(f"  ❌ Account not found in database")
        else:
            print("No account information for this posting")

def analyze_transaction_matching():
    """
    Check if we can match postings with existing transactions
    by comparing various fields like date, amount, and description.
    """
    # Get a sample of ledger postings
    postings_data = get_ledger_postings(limit=50)
    
    if not postings_data or 'values' not in postings_data:
        print("No postings data found.")
        return
    
    postings = postings_data['values']
    matches_found = 0
    
    for posting in postings:
        posting_id = posting.get('id')
        posting_date = posting.get('date')
        posting_amount = posting.get('amount')
        posting_description = posting.get('description', '')
        
        # Try to find matching transaction by various criteria
        potential_matches = Transaction.objects.filter(
            date=posting_date,
            amount=posting_amount
        )
        
        if potential_matches.exists():
            matches_found += 1
            print(f"\nMatch found for posting {posting_id}:")
            print(f"  Posting: {posting_date} - {posting_description} (${posting_amount})")
            
            for transaction in potential_matches[:3]:  # Show up to 3 matches
                print(f"  Transaction: {transaction.date} - {transaction.description} (${transaction.amount})")
                print(f"    ID: {transaction.id}, Tripletex ID: {transaction.tripletex_id}")
                if transaction.supplier:
                    print(f"    Supplier: {transaction.supplier}")
                if transaction.ledger_account:
                    print(f"    Account: {transaction.ledger_account}")
    
    print(f"\nFound {matches_found} potential matches out of {len(postings)} postings.")

if __name__ == "__main__":
    print("Testing the Tripletex ledger/posting endpoint...")
    print(f"Using company ID: {TRIPLETEX_COMPANY_ID}")
    
    # First, let's get and analyze some ledger postings
    analyze_postings_and_transactions()
    
    # Then, try to match with existing transactions
    analyze_transaction_matching() 