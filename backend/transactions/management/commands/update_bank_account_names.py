from django.core.management.base import BaseCommand
import os
import json
from transactions.models import BankAccount

class Command(BaseCommand):
    help = 'Update bank account names based on bank_account_map.json'

    def handle(self, *args, **options):
        self.stdout.write("Updating bank account names based on bank_account_map.json...")
        
        # Get the current directory
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # Load bank account mapping from bank_account_map.json
        bank_map_path = os.path.join(current_dir, 'transactions', 'bank_account_map.json')
        with open(bank_map_path, 'r') as f:
            bank_account_map = json.load(f)
        
        # Print loaded mapping
        self.stdout.write("Loaded {} bank account mappings:".format(len(bank_account_map)))
        for entry in bank_account_map:
            self.stdout.write("  - Account {}: {} (Ignore: {})".format(entry['bank_id'], entry['bank_name'], entry['ignore']))
        
        # Update each bank account
        updated_count = 0
        for entry in bank_account_map:
            bank_id = str(entry['bank_id'])
            bank_name = entry['bank_name']
            ignore = entry['ignore']
            
            if ignore:
                self.stdout.write("Skipping {} ({}) as it is marked to ignore".format(bank_id, bank_name))
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
                self.stdout.write(self.style.SUCCESS("Updated bank account ID {}: {} -> {}".format(bank_account.id, old_name, bank_name)))
                
            except BankAccount.DoesNotExist:
                self.stdout.write(self.style.WARNING("Warning: Bank account with number {} does not exist in the database".format(bank_id)))
        
        self.stdout.write(self.style.SUCCESS("\nUpdated {} bank accounts with new names".format(updated_count))) 