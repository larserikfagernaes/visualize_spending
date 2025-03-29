#!/usr/bin/env python
"""
Script to create bank accounts based on account_id values in Transaction model.
Run this script with Django's shell: python manage.py shell < create_bank_accounts.py
"""
from transactions.models import Transaction, BankAccount
from django.db.models import Count
from collections import defaultdict

# Get unique account_ids and count their occurrences
account_mapping = {}
account_ids = Transaction.objects.values('account_id').annotate(count=Count('account_id')).order_by('-count')

# Define name mapping based on account IDs
account_name_mapping = {
    '82642706': 'Personal Account',
    '136636846': 'Business Account - Cards',
    '136637859': 'Business Account - Main',
    '136638262': 'Business Account - Expenses'
}

# Print the account IDs and their counts
print('Found the following account IDs:')
for item in account_ids:
    if item['account_id']:
        print(f"Account ID: {item['account_id']}, Count: {item['count']}")
        
# Create bank accounts for each unique account_id
print('\nCreating bank accounts...')
created_count = 0
for item in account_ids:
    account_id = item['account_id']
    if not account_id:
        continue
        
    # Skip if bank account already exists with this account number
    if BankAccount.objects.filter(account_number=account_id).exists():
        print(f"Bank account with account number {account_id} already exists. Skipping.")
        continue
    
    # Get a name for the account, either from the mapping or a default
    account_name = account_name_mapping.get(account_id, f"Account {account_id}")
    
    # Create the bank account
    bank_account = BankAccount.objects.create(
        name=account_name,
        account_number=account_id,
        bank_name='Bank',
        account_type='Checking',
        is_active=True
    )
    created_count += 1
    print(f"Created bank account: {bank_account.name} (ID: {bank_account.id})")

print(f"\nCreated {created_count} bank accounts")

# Now update all transactions with the appropriate bank account
print('\nUpdating transactions with bank account references...')
updated_count = 0

for account_id, name in account_name_mapping.items():
    # Get the bank account
    try:
        bank_account = BankAccount.objects.get(account_number=account_id)
        
        # Update all transactions with this account_id
        count = Transaction.objects.filter(account_id=account_id, bank_account__isnull=True).update(
            bank_account=bank_account
        )
        
        updated_count += count
        print(f"Updated {count} transactions with bank account: {bank_account.name}")
    except BankAccount.DoesNotExist:
        print(f"Bank account with account number {account_id} not found!")

print(f"\nUpdated {updated_count} transactions with bank account references")
