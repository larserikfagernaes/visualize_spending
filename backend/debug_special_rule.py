#!/usr/bin/env python3
import os
import sys
import django
import importlib

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import Transaction, Account, TransactionAccount
from django.db import transaction as db_transaction

# Import the apply_special_account_rules function
get_transactions_module = importlib.import_module('transactions.management.commands.00_get_transactions')
apply_special_account_rules = getattr(get_transactions_module, 'apply_special_account_rules')

def debug_account_rule():
    """Debug the account rule for transaction 56575785"""
    TRANSACTION_ID = "56575785"
    ACCOUNT_ID = "66775225"  # Driftsmateriale
    
    # Debug flags
    FORCE_DELETE_LINKS = True  # Changed to True to test rule application
    SKIP_EXISTING_LINKS = False  # Changed to False
    DEBUG = True  # Enable verbose output
    
    # Define the special account mappings
    SPECIAL_ACCOUNT_MAPPINGS = {
        "66775225": [  # Driftsmateriale account
            {"keywords": ["BILTEMA", "LTEMA"], "description": "Auto-linked to Driftsmateriale (maintenance supplies)"}
        ],
    }
    
    # Get the special account
    try:
        special_account = Account.objects.get(tripletex_id=ACCOUNT_ID)
        print(f"Found special account: {special_account.name} (ID: {ACCOUNT_ID})")
        special_accounts = {ACCOUNT_ID: special_account}
    except Account.DoesNotExist:
        print(f"Error: Special account {ACCOUNT_ID} not found in database")
        return
    
    # Get the transaction
    try:
        trans = Transaction.objects.get(tripletex_id=TRANSACTION_ID)
        print(f"Found transaction: {trans.description} (ID: {trans.tripletex_id})")
        print(f"Amount: {trans.amount}")
        print(f"Date: {trans.date}")
        print(f"Internal transfer: {trans.is_internal_transfer}")
        print(f"Wage transfer: {trans.is_wage_transfer}")
        print(f"Tax transfer: {trans.is_tax_transfer}")
        print(f"Forbidden: {trans.is_forbidden}")
        print(f"Should process: {trans.should_process}")
    except Transaction.DoesNotExist:
        print(f"Error: Transaction {TRANSACTION_ID} not found in database")
        return
    
    # Check existing links
    existing_links = TransactionAccount.objects.filter(
        transaction=trans,
        account=special_account
    )
    
    print(f"\nCurrent links: {existing_links.count()}")
    for link in existing_links:
        print(f"- {link.account.name}: Amount={link.amount}, Is Debit={link.is_debit}, Posting ID={link.posting_id}, Description={link.description}")
    
    # Test pattern matching
    upper_desc = trans.description.upper()
    for pattern in SPECIAL_ACCOUNT_MAPPINGS[ACCOUNT_ID]:
        keywords = pattern.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = [keywords]
        
        print("\nTesting keywords against description:")
        for keyword in keywords:
            match = keyword.upper() in upper_desc
            print(f"Keyword '{keyword}' in '{upper_desc}': {match}")
    
    # Get all rules for this transaction
    if existing_links.exists() and SKIP_EXISTING_LINKS:
        print("\nTransaction already has links to this account. Skipping rule application.")
        return
    
    # Force delete existing links if requested
    if FORCE_DELETE_LINKS and existing_links.exists():
        print(f"\nForce deleting {existing_links.count()} existing links...")
        with db_transaction.atomic():
            existing_links.delete()
        print("Links deleted.")
    
    # Apply the rule
    print("\nApplying special account rule...")
    with db_transaction.atomic():
        links_created = apply_special_account_rules(
            trans, 
            special_accounts,
            SPECIAL_ACCOUNT_MAPPINGS,
            debug=DEBUG
        )
    
    print(f"Links created: {links_created}")
    
    # Verify links after application
    updated_links = TransactionAccount.objects.filter(
        transaction=trans,
        account=special_account
    )
    
    print(f"\nUpdated links: {updated_links.count()}")
    for link in updated_links:
        print(f"- {link.account.name}: Amount={link.amount}, Is Debit={link.is_debit}, Posting ID={link.posting_id}, Description={link.description}")

if __name__ == "__main__":
    debug_account_rule() 