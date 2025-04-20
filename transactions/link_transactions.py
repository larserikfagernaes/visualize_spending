"""
Module for linking transactions with suppliers and accounts
using the ledger/posting endpoint from Tripletex API.
"""

import os
import sys
import json
import requests
import logging
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from dotenv import load_dotenv
import django

# Setup logging
logger = logging.getLogger(__name__)

# Setup Django environment for standalone execution
if __name__ == "__main__":
    # Add the parent directory to sys.path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
    django.setup()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("link_transactions.log"),
            logging.StreamHandler()
        ]
    )
    
    # Import directly for standalone script
    from transactions.models import Transaction, Supplier, Account
    from transactions.get_transactions import get_or_create_supplier, get_or_create_account
else:
    # Import as relative imports when used as a module
    from .models import Transaction, Supplier, Account
    from .get_transactions import get_or_create_supplier, get_or_create_account

def get_ledger_postings(date_from=None, date_to=None, limit=500):
    """
    Query the ledger/posting endpoint to retrieve posting information.
    
    Args:
        date_from: Start date for filtering postings (default: 180 days ago)
        date_to: End date for filtering postings (default: today)
        limit: Maximum number of results to return
    
    Returns:
        The API response with posting data
    """
    # Load environment variables
    load_dotenv()
    
    # Authentication variables
    TRIPLETEX_COMPANY_ID = os.getenv("3T_AUTH_USER")
    TRIPLETEX_AUTH_TOKEN = os.getenv("3T_SESSION_TOKEN")
    
    # Check if credentials are available
    if not TRIPLETEX_AUTH_TOKEN:
        raise ValueError("TRIPLETEX_AUTH_TOKEN environment variable is not set. Please set it before running this script.")
    
    # Set default dates if not provided
    if date_from is None:
        date_from = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
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
    logger.info(f"Fetching ledger postings from {date_from} to {date_to}...")
    response = requests.get(base_url, params=params, auth=auth)
    
    # Check if request was successful
    if response.status_code == 200:
        data = response.json()
        logger.info(f"Retrieved {len(data.get('values', []))} ledger postings")
        return data
    else:
        logger.error(f"Error: {response.status_code}")
        logger.error(response.text)
        return None

def find_matching_transaction(posting):
    """
    Try to find a transaction that matches the posting.
    
    Args:
        posting: The posting data from the API
    
    Returns:
        A Transaction object if a match is found, None otherwise
    """
    posting_date = posting.get('date')
    posting_amount = posting.get('amount')
    posting_description = posting.get('description', '')
    
    # Look for an exact match by date and amount
    potential_matches = Transaction.objects.filter(
        date=posting_date,
        amount=posting_amount
    )
    
    # If we have multiple matches, try to narrow down by description
    if potential_matches.count() > 1 and posting_description:
        # Look for partial matches in description
        description_matches = []
        for transaction in potential_matches:
            # Check if any significant words from the posting description appear in the transaction description
            posting_words = set([w.lower() for w in posting_description.split() if len(w) > 3])
            transaction_words = set([w.lower() for w in transaction.description.split() if len(w) > 3])
            
            # Calculate word overlap
            common_words = posting_words.intersection(transaction_words)
            
            if common_words:
                similarity = len(common_words) / max(len(posting_words), len(transaction_words))
                description_matches.append((transaction, similarity))
        
        # Sort by similarity score
        if description_matches:
            description_matches.sort(key=lambda x: x[1], reverse=True)
            return description_matches[0][0]
    
    # If we have a single match or couldn't narrow down by description, return the first match
    if potential_matches.exists():
        return potential_matches.first()
    
    return None

def link_transactions_with_suppliers_and_accounts(limit=1000, update_existing=False):
    """
    Link transactions with suppliers and accounts based on data from the ledger/posting endpoint.
    
    Args:
        limit: Maximum number of postings to process
        update_existing: If True, update suppliers and accounts even if already set
    
    Returns:
        dict: Statistics about the linking process
    """
    # Get ledger postings
    postings_data = get_ledger_postings(limit=limit)
    
    if not postings_data or 'values' not in postings_data:
        logger.error("No postings data found.")
        return {
            'success': False,
            'error': 'No postings data found'
        }
    
    postings = postings_data['values']
    
    # Stats for reporting
    stats = {
        'total_postings': len(postings),
        'matches_found': 0,
        'suppliers_linked': 0,
        'accounts_linked': 0,
        'no_match': 0,
        'postings_with_supplier': 0,
        'success': True
    }
    
    # Process each posting
    for posting in postings:
        # Get posting details
        posting_id = posting.get('id')
        posting_date = posting.get('date')
        posting_amount = posting.get('amount')
        posting_description = posting.get('description', '')
        supplier_data = posting.get('supplier')
        account_data = posting.get('account')
        
        # Count postings with supplier data
        if supplier_data and supplier_data.get('id'):
            stats['postings_with_supplier'] += 1
        
        # Find matching transaction
        transaction = find_matching_transaction(posting)
        
        if transaction:
            stats['matches_found'] += 1
            logger.debug(f"Match found for posting {posting_id}: Transaction {transaction.id}")
            
            # Track if we need to save the transaction
            changes_made = False
            
            # Update supplier information if available
            if supplier_data and supplier_data.get('id') and (update_existing or not transaction.supplier):
                supplier_id = supplier_data.get('id')
                supplier_name = supplier_data.get('name', 'Unknown')
                
                if transaction.supplier and not update_existing:
                    logger.debug(f"Transaction already has supplier: {transaction.supplier}")
                else:
                    try:
                        # Get or create supplier
                        supplier = get_or_create_supplier(supplier_id)
                        
                        # Link supplier to transaction
                        if supplier:
                            transaction.supplier = supplier
                            changes_made = True
                            stats['suppliers_linked'] += 1
                            logger.info(f"Linked transaction {transaction.id} with supplier {supplier}")
                        else:
                            logger.warning(f"Failed to get or create supplier {supplier_id}")
                    except Exception as e:
                        logger.error(f"Error linking supplier: {e}")
            
            # Update account information if available
            if account_data and account_data.get('id') and (update_existing or not transaction.ledger_account):
                account_id = account_data.get('id')
                try:
                    # Get or create account
                    account = get_or_create_account(account_id)
                    
                    # Link account to transaction
                    if account:
                        transaction.ledger_account = account
                        changes_made = True
                        stats['accounts_linked'] += 1
                        logger.info(f"Linked transaction {transaction.id} with account {account}")
                except Exception as e:
                    logger.error(f"Error linking account: {e}")
            
            # Save transaction if changes were made
            if changes_made:
                transaction.save()
        else:
            stats['no_match'] += 1
            if stats['no_match'] <= 10:  # Only log the first 10 to avoid excessive logging
                logger.debug(f"No match found for posting {posting_id}: {posting_date} - {posting_description} (${posting_amount})")
    
    # Report results
    logger.info("Linking process completed!")
    logger.info(f"Total postings processed: {stats['total_postings']}")
    logger.info(f"Postings with supplier data: {stats['postings_with_supplier']}")
    logger.info(f"Matches found: {stats['matches_found']}")
    logger.info(f"Suppliers linked: {stats['suppliers_linked']}")
    logger.info(f"Accounts linked: {stats['accounts_linked']}")
    logger.info(f"No matches found: {stats['no_match']}")
    
    return stats

if __name__ == "__main__":
    # Run the linking process
    print("Starting process to link transactions with suppliers and accounts...")
    result = link_transactions_with_suppliers_and_accounts(update_existing=False)
    print(f"Process completed with result: {result['success']}")
    print(f"Matches found: {result['matches_found']}")
    print(f"Suppliers linked: {result['suppliers_linked']}")
    print(f"Accounts linked: {result['accounts_linked']}") 