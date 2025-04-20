#!/usr/bin/env python3
import os
import sys
import django
import importlib

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import Transaction, Account, TransactionAccount
from django.db import connection
from django.db import transaction as db_transaction

# Import the apply_special_account_rules function
get_transactions_module = importlib.import_module('transactions.management.commands.00_get_transactions')
apply_special_account_rules = getattr(get_transactions_module, 'apply_special_account_rules')

def find_similar_transactions():
    """Find transactions with similar descriptions to LTEMA and BILTEMA"""
    ACCOUNT_ID = "66775225"  # Driftsmateriale
    
    # Get the target account
    try:
        special_account = Account.objects.get(tripletex_id=ACCOUNT_ID)
        print(f"Found special account: {special_account.name} (ID: {ACCOUNT_ID})")
        special_accounts = {ACCOUNT_ID: special_account}
    except Account.DoesNotExist:
        print(f"Error: Special account {ACCOUNT_ID} not found in database")
        return
    
    # Define the special account mappings
    SPECIAL_ACCOUNT_MAPPINGS = {
        "66775225": [  # Driftsmateriale account
            {"keywords": ["BILTEMA", "LTEMA"], "description": "Auto-linked to Driftsmateriale (maintenance supplies)"}
        ],
    }
    
    # Find transactions containing LTEMA or BILTEMA
    biltema_transactions = Transaction.objects.filter(description__icontains="BILTEMA").order_by('-date')[:5]
    ltema_transactions = Transaction.objects.filter(description__icontains="LTEMA").order_by('-date')[:5]
    
    # Get all matching transactions
    matching_transactions = list(biltema_transactions) + list(ltema_transactions)
    unique_transactions = {}
    
    for trans in matching_transactions:
        if trans.tripletex_id not in unique_transactions:
            unique_transactions[trans.tripletex_id] = trans
    
    print(f"Found {len(unique_transactions)} matching transactions")
    
    # Process each transaction
    for trans_id, trans in unique_transactions.items():
        print(f"\n---- Processing Transaction {trans_id} ----")
        print(f"Description: {trans.description}")
        print(f"Amount: {trans.amount}")
        print(f"Date: {trans.date}")
        
        # Check if already linked
        existing_links = TransactionAccount.objects.filter(
            transaction=trans,
            account=special_account
        )
        
        print(f"Existing links to Driftsmateriale: {existing_links.count()}")
        for link in existing_links:
            print(f"- Link: Amount={link.amount}, Is Debit={link.is_debit}, Posting ID={link.posting_id}")
        
        # Test if the rule would match
        upper_desc = trans.description.upper()
        for pattern in SPECIAL_ACCOUNT_MAPPINGS[ACCOUNT_ID]:
            keywords = pattern.get("keywords", [])
            if not isinstance(keywords, list):
                keywords = [keywords]
            
            for keyword in keywords:
                match = keyword.upper() in upper_desc
                if match:
                    print(f"Keyword match: '{keyword}' found in '{upper_desc}'")
        
        # Create missing links if needed and transaction is eligible
        if not existing_links.exists() and not trans.is_internal_transfer and not trans.is_wage_transfer and not trans.is_tax_transfer:
            print("Transaction eligible for automatic linking, applying rule...")
            with db_transaction.atomic():
                links_created = apply_special_account_rules(
                    trans, 
                    special_accounts,
                    SPECIAL_ACCOUNT_MAPPINGS,
                    debug=True
                )
            print(f"Links created: {links_created}")
        elif existing_links.exists():
            print("Transaction already linked correctly.")
        else:
            print("Transaction not eligible for account linking.")

def debug_batch_processing():
    """Test batch processing on several similar transactions"""
    ACCOUNT_ID = "66775225"  # Driftsmateriale
    
    # Define SQL query to find appropriate transactions - using LIKE for SQLite compatibility
    sql = """
    SELECT t.tripletex_id, t.description, t.amount, t.date, t.is_internal_transfer, t.is_wage_transfer, t.is_tax_transfer
    FROM transactions_transaction t
    WHERE (t.description LIKE '%BILTEMA%' OR t.description LIKE '%LTEMA%')
    AND t.is_internal_transfer = 0
    AND t.is_wage_transfer = 0
    AND t.is_tax_transfer = 0
    ORDER BY t.date DESC
    LIMIT 20
    """
    
    # Get the target account
    try:
        special_account = Account.objects.get(tripletex_id=ACCOUNT_ID)
        print(f"Found special account: {special_account.name} (ID: {ACCOUNT_ID})")
        special_accounts = {ACCOUNT_ID: special_account}
    except Account.DoesNotExist:
        print(f"Error: Special account {ACCOUNT_ID} not found in database")
        return
    
    # Define the special account mappings
    SPECIAL_ACCOUNT_MAPPINGS = {
        "66775225": [  # Driftsmateriale account
            {"keywords": ["BILTEMA", "LTEMA"], "description": "Auto-linked to Driftsmateriale (maintenance supplies)"}
        ],
    }
    
    # Execute the SQL query
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    
    print(f"Found {len(rows)} transactions matching the criteria")
    
    # Process each transaction
    for row in rows:
        tripletex_id, description, amount, date, is_internal, is_wage, is_tax = row
        
        print(f"\n---- Processing Transaction {tripletex_id} ----")
        print(f"Description: {description}")
        print(f"Amount: {amount}")
        print(f"Date: {date}")
        
        # Get the transaction object
        try:
            trans = Transaction.objects.get(tripletex_id=tripletex_id)
        except Transaction.DoesNotExist:
            print(f"Error: Could not find transaction with ID {tripletex_id}")
            continue
        
        # Check if already linked
        existing_links = TransactionAccount.objects.filter(
            transaction=trans,
            account=special_account
        )
        
        print(f"Existing links to Driftsmateriale: {existing_links.count()}")
        for link in existing_links:
            print(f"- Link: Amount={link.amount}, Is Debit={link.is_debit}, Posting ID={link.posting_id}")
        
        # Create missing links if needed
        if not existing_links.exists():
            print("No existing link found. Applying special account rule...")
            with db_transaction.atomic():
                links_created = apply_special_account_rules(
                    trans, 
                    special_accounts,
                    SPECIAL_ACCOUNT_MAPPINGS,
                    debug=True
                )
            print(f"Links created: {links_created}")
        else:
            print("Transaction already linked correctly.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        debug_batch_processing()
    else:
        find_similar_transactions() 