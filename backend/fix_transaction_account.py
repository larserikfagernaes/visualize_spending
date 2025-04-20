#!/usr/bin/env python3
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import Transaction, Account, TransactionAccount
from django.db import transaction

def fix_transaction_account_link(transaction_id, account_id):
    """
    Manually connect a transaction to an account by creating a TransactionAccount record.
    
    Args:
        transaction_id (str): Tripletex ID of the transaction
        account_id (str): Tripletex ID of the account
    """
    print(f"Fixing connection between transaction {transaction_id} and account {account_id}")
    
    try:
        # Get the transaction and account
        trans = Transaction.objects.get(tripletex_id=transaction_id)
        account = Account.objects.get(tripletex_id=account_id)
        
        print(f"Found transaction: {trans.description} ({trans.date})")
        print(f"Found account: {account.name} ({account.account_number})")
        
        # Check if link already exists
        existing_link = TransactionAccount.objects.filter(
            transaction=trans,
            account=account
        ).first()
        
        if existing_link:
            print(f"Link already exists: {existing_link}")
            return
        
        # Create the link
        with transaction.atomic():
            # Use a negative amount for expense transactions (negative amount in Transaction)
            amount = abs(trans.amount) if trans.amount < 0 else trans.amount
            
            # Determine if this is a debit or credit posting
            # For expense transactions (negative amount), this is a debit posting
            is_debit = trans.amount < 0
            
            # Create the TransactionAccount record
            transaction_account = TransactionAccount.objects.create(
                transaction=trans,
                account=account,
                amount=amount,
                is_debit=is_debit,
                description=f"Manually linked: {trans.description}",
                posting_id=f"manual_{transaction_id}_{account_id}",
                voucher_id=""
            )
            
            print(f"Successfully created TransactionAccount link: {transaction_account}")
            
            # Output all accounts now linked to this transaction
            related_accounts = trans.accounts.all()
            print(f"\nTransaction now has {related_accounts.count()} linked accounts:")
            for acc in related_accounts:
                print(f"- {acc.tripletex_id}: {acc.name}")
            
    except Transaction.DoesNotExist:
        print(f"Error: Transaction with ID {transaction_id} not found")
    except Account.DoesNotExist:
        print(f"Error: Account with ID {account_id} not found")
    except Exception as e:
        print(f"Error: {e}")
    
if __name__ == "__main__":
    if len(sys.argv) > 2:
        transaction_id = sys.argv[1]
        account_id = sys.argv[2]
    else:
        # Default to the transaction and account from the issue
        transaction_id = "56575785"
        account_id = "66775225"
    
    fix_transaction_account_link(transaction_id, account_id) 