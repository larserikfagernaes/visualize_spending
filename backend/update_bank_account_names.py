#!/usr/bin/env python
"""
Script to update bank account names based on bank_account_map.json
"""
import os
import json
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import BankAccount

def get_current_directory():
    """Returns the absolute directory path of the current file."""
    return os.path.dirname(os.path.abspath(__file__))

def main():
    print("Updating bank account names based on bank_account_map.json...")
    
    # Load bank account mapping from bank_account_map.json
    bank_map_path = os.path.join(get_current_directory(), 'transactions', 'bank_account_map.json')
    with open(bank_map_path, 'r') as f:
        bank_account_map = json.load(f)
    
    # Print loaded mapping
    print("Loaded {} bank account mappings:".format(len(bank_account_map)))
    for entry in bank_account_map:
        print("  - Account {}: {} (Ignore: {})".format(entry['bank_id'], entry['bank_name'], entry['ignore']))
    
    # Update each bank account
    updated_count = 0
    for entry in bank_account_map:
        bank_id = str(entry['bank_id'])
        bank_name = entry['bank_name']
        ignore = entry['ignore']
        
        if ignore:
            print("Skipping {} ({}) as it is marked to ignore".format(bank_id, bank_name))
            continue
        
        try:
            # Find the bank account by account_number
            bank_account = BankAccount.objects.get(account_number=bank_id)
            
            # Save the old name for logging
            old_name = bank_account.name
            
            # Update the name
            bank_account.name = bank_name
            bank_account.save()
            
            updated_count += 1
            print("Updated bank account ID {}: {} -> {}".format(bank_account.id, old_name, bank_name))
            
        except BankAccount.DoesNotExist:
            print("Warning: Bank account with number {} does not exist in the database".format(bank_id))
    
    print("\nUpdated {} bank accounts with new names".format(updated_count))

if __name__ == "__main__":
    main() 