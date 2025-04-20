#!/usr/bin/env python3
import os
import sys
import django
import importlib

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import Transaction, Account, TransactionAccount
from django.db import transaction

# Import the function using importlib to avoid syntax errors with the numeric module name
get_transactions_module = importlib.import_module('transactions.management.commands.00_get_transactions')
apply_special_account_rules = getattr(get_transactions_module, 'apply_special_account_rules')

def test_special_account_rules():
    """
    Test the special account rules functionality by creating a test transaction 
    and applying the rules to it.
    """
    # Define test data - using the exact description from the real transaction
    test_trans_id = "TEST_BILTEMA_REAL"
    test_description = "LTEMA AVD  202 TRONDHEI"
    test_account_id = "66775225"  # Driftsmateriale
    
    # Define the special account mappings (same as in 00_get_transactions.py)
    SPECIAL_ACCOUNT_MAPPINGS = {
        "66775225": [  # Driftsmateriale account
            {"keywords": ["BILTEMA", "LTEMA"], "description": "Auto-linked to Driftsmateriale (maintenance supplies)"}
        ],
    }
    
    print(f"Testing special account rules with transaction: {test_description}")
    
    # Get the special account
    try:
        special_account = Account.objects.get(tripletex_id=test_account_id)
        print(f"Found special account: {special_account.name} (ID: {test_account_id})")
        special_accounts = {test_account_id: special_account}
    except Account.DoesNotExist:
        print(f"Error: Account with ID {test_account_id} not found")
        return
    
    # Create or update a test transaction
    with transaction.atomic():
        # Check if test transaction already exists
        test_trans, created = Transaction.objects.update_or_create(
            tripletex_id=test_trans_id,
            defaults={
                'description': test_description,
                'amount': -1722.30,  # Exact amount from the real transaction
                'date': '2023-03-07',  # Exact date from the real transaction
                'is_internal_transfer': False,
                'is_wage_transfer': False,
                'is_tax_transfer': False,
                'is_forbidden': False,
                'should_process': True,
            }
        )
        
        if created:
            print(f"Created test transaction: {test_trans.description}")
        else:
            print(f"Using existing test transaction: {test_trans.description}")
            
        # Remove any existing transaction account links
        TransactionAccount.objects.filter(transaction=test_trans).delete()
        print("Cleared existing TransactionAccount links")
        
        # Apply the special account rules
        links_created = apply_special_account_rules(
            test_trans, 
            special_accounts,
            SPECIAL_ACCOUNT_MAPPINGS,
            debug=True
        )
        
        print(f"Created {links_created} special account links")
        
        # Verify the links
        links = TransactionAccount.objects.filter(transaction=test_trans)
        print(f"\nTransaction now has {links.count()} linked accounts:")
        for link in links:
            print(f"- {link.account.tripletex_id}: {link.account.name}")
            print(f"  Amount: {link.amount}, Description: {link.description}")
        
        print("\nTest completed successfully!")

if __name__ == "__main__":
    test_special_account_rules() 