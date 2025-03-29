import os
import django
import sys
import json

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import Transaction

def update_internal_transfers():
    """
    Updates internal transfer detection using enhanced logic based on raw transaction data.
    This looks for patterns in transaction descriptions, postings, and related data to 
    more accurately identify transfers between company accounts.
    """
    # Get all transactions that might need updating
    transactions = Transaction.objects.all()
    print(f"Analyzing {transactions.count()} transactions for internal transfers")
    
    # Keywords that indicate internal transfers
    internal_keywords = [
        "intern overføring",
        "overført fra: aviant",
        "oppgave fra: aviant",
        "overføring mellom egne kontoer",
        "overføring til egen konto",
        "overføring fra egen konto",
        "oppgave kontoreguleringaviant as"
    ]
    
    # Account IDs that indicate money movements between company accounts
    company_accounts = [
        # Add known company account IDs here if needed
    ]
    
    count_updated = 0
    count_already_marked = 0
    count_raw_data_used = 0
    
    for transaction in transactions:
        was_already_marked = transaction.is_internal_transfer
        should_mark = False
        raw_data_used = False
        
        # First check: Regular description matching (as before)
        description = transaction.description.lower()
        if any(keyword in description for keyword in internal_keywords):
            should_mark = True
        
        # Enhanced check: Use raw_data if available
        if transaction.raw_data and not should_mark:
            raw_data_used = True
            
            # Check for internal transfer in detailed data
            if 'detailed_data' in transaction.raw_data:
                detailed_data = transaction.raw_data.get('detailed_data', {})
                
                # Check postings for internal transfer indicators
                postings = detailed_data.get('value', {}).get('groupedPostings', [])
                if any(posting.get('description') == 'Intern overføring' for posting in postings):
                    should_mark = True
                
                # Check if both accounts involved are company accounts
                try:
                    posting_accounts = [posting.get('account', {}).get('id') for posting in postings]
                    if len(set(posting_accounts).intersection(company_accounts)) >= 2:
                        should_mark = True
                except (KeyError, AttributeError):
                    pass
        
        # Update transaction if needed
        if should_mark and not was_already_marked:
            transaction.is_internal_transfer = True
            transaction.save()
            count_updated += 1
        elif was_already_marked:
            count_already_marked += 1
        
        if raw_data_used and should_mark:
            count_raw_data_used += 1
    
    print(f"Summary:")
    print(f"- {count_updated} transactions newly marked as internal transfers")
    print(f"- {count_already_marked} transactions were already marked")
    print(f"- {count_raw_data_used} transactions identified using raw_data")

if __name__ == "__main__":
    update_internal_transfers() 