import os
import sys
import django

# Set up Django environment
# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import Transaction

def update_internal_transfers():
    """
    Updates existing transactions with specific text patterns to mark them as internal transfers.
    """
    # Get all transactions with "OVERFØRT Fra: AVIANT AS" in the description
    overfort_transactions = Transaction.objects.filter(description__contains='OVERFØRT Fra: AVIANT AS')
    
    # Get all transactions with "OPPGAVE Fra: Aviant AS" in the description that aren't already marked
    oppgave_transactions = Transaction.objects.filter(
        description__contains='OPPGAVE Fra: Aviant AS',
        is_internal_transfer=False
    )
    
    # Update OVERFØRT transactions
    overfort_count = 0
    for transaction in overfort_transactions:
        if not transaction.is_internal_transfer:
            transaction.is_internal_transfer = True
            transaction.save()
            overfort_count += 1
            print("Updated OVERFØRT transaction: {}".format(transaction.description))
    
    # Update OPPGAVE transactions
    oppgave_count = 0
    for transaction in oppgave_transactions:
        transaction.is_internal_transfer = True
        transaction.save()
        oppgave_count += 1
        print("Updated OPPGAVE transaction: {}".format(transaction.description))
    
    # Print summary
    total_updated = overfort_count + oppgave_count
    print("\nSummary:")
    print("Updated {} OVERFØRT transactions".format(overfort_count))
    print("Updated {} OPPGAVE transactions".format(oppgave_count))
    print("Total updates: {}".format(total_updated))

if __name__ == "__main__":
    update_internal_transfers() 