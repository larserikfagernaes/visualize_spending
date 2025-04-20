import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import Transaction, Account, TransactionAccount
from django.db import connection

def verify_transaction(transaction_id):
    try:
        # Find the transaction
        transaction = Transaction.objects.get(tripletex_id=transaction_id)
        print(f"Found transaction: {transaction.tripletex_id}")
        print(f"Description: {transaction.description}")
        print(f"Amount: {transaction.amount}")
        print(f"Date: {transaction.date}")
        
        # Get related accounts through TransactionAccount
        related_accounts = transaction.accounts.all()
        print(f"\nRelated accounts: {related_accounts.count()}")
        for account in related_accounts:
            print(f"Account {account.tripletex_id}: {account.name} - {account.account_number}")
        
        # Check if the specific account (66775225) is connected
        try:
            account_to_check = Account.objects.get(tripletex_id='66775225')
            print(f"\nTarget account: {account_to_check.name} (ID: {account_to_check.tripletex_id})")
            
            if account_to_check in related_accounts:
                print(f"Account 66775225 IS connected to this transaction.")
            else:
                print(f"Account 66775225 is NOT connected to this transaction.")
                
            # Check using TransactionAccount directly
            transaction_accounts = TransactionAccount.objects.filter(
                transaction=transaction, 
                account=account_to_check
            )
            print(f"Direct relationship check: {transaction_accounts.count()} connections found")
            
            if transaction_accounts.exists():
                for ta in transaction_accounts:
                    print(f"  - Amount: {ta.amount}, Description: {ta.description}")
            
        except Account.DoesNotExist:
            print("\nAccount 66775225 does not exist in database")
            print("Let's check all available accounts with similar IDs:")
            similar_accounts = Account.objects.filter(tripletex_id__startswith='667')
            for acc in similar_accounts:
                print(f"  - {acc.tripletex_id}: {acc.name}")
        
        # Look at the transaction accounts explicitly
        print("\nTransaction Accounts:")
        for ta in TransactionAccount.objects.filter(transaction=transaction):
            print(f"  - Account {ta.account.tripletex_id}: {ta.account.name}, Amount: {ta.amount}")
    
    except Transaction.DoesNotExist:
        print(f"Transaction with ID {transaction_id} not found in database")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        transaction_id = int(sys.argv[1])
        verify_transaction(transaction_id)
    else:
        # Use the example transaction ID if none provided
        verify_transaction(56575785) 