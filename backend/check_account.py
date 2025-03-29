import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

# Import models after Django setup
from transactions.models import Account, Transaction

# Check if account exists
account = Account.objects.filter(tripletex_id='82642706').first()
print(f'Account exists: {account is not None}')

if account:
    print(f'Account: {account.name} (ID: {account.id})')
    print(f'Transactions linked to this account: {account.transactions.count()}')
    
    # List a few transactions linked to this account
    transactions = account.transactions.all()[:5]
    print("Sample transactions:")
    for tx in transactions:
        print(f"- {tx.tripletex_id}: {tx.description} ({tx.amount})")
    
    # Look for a specific transaction
    try:
        transaction = Transaction.objects.get(tripletex_id='126215474')
        print(f'Transaction exists: True')
        print(f'Transaction date: {transaction.date}')
        print(f'Transaction ledger_account: {transaction.ledger_account}')
        print(f'Transaction supplier: {transaction.supplier}')
    except Transaction.DoesNotExist:
        print(f'Transaction with ID 126215474 does not exist') 