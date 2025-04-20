#!/usr/bin/env python3
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

# Import models
from transactions.models import Transaction, LedgerPosting

def print_recent_data():
    """Print information about the most recent transactions and ledger postings."""
    print("Recent Transactions:")
    for t in Transaction.objects.order_by('-date')[:5]:
        description = t.description[:50] + "..." if len(t.description) > 50 else t.description
        print(f"{t.date} - {description} (Amount: {t.amount})")
    
    print("\nRecent Ledger Postings:")
    for p in LedgerPosting.objects.order_by('-date')[:5]:
        description = p.description[:50] + "..." if p.description and len(p.description) > 50 else (p.description or "No description")
        print(f"{p.date} - {description} (Amount: {p.amount})")
        
    # Print totals 
    print(f"\nTotal Transactions: {Transaction.objects.count()}")
    print(f"Total Ledger Postings: {LedgerPosting.objects.count()}")

def check_matching_entries():
    """Check for transactions and postings with the same date and amount."""
    print("\nLooking for potential matches (same date and amount):")
    matches_found = 0
    
    # Get payment postings (those containing "Betaling" in the description)
    payment_postings = LedgerPosting.objects.filter(
        description__icontains="Betaling"
    ).order_by('-date')[:100]
    
    print(f"Found {payment_postings.count()} payment postings to check")
    
    for p in payment_postings:
        # Look for matching transactions
        matching_transactions = Transaction.objects.filter(
            date=p.date,
            amount=p.amount
        )
        
        if matching_transactions.exists():
            matches_found += 1
            posting_desc = p.description[:50] + "..." if p.description and len(p.description) > 50 else (p.description or "No description")
            print(f"\nPosting: {p.date} - {posting_desc} (Amount: {p.amount})")
            print("Matching Transactions:")
            
            for idx, t in enumerate(matching_transactions[:3]):
                t_desc = t.description[:50] + "..." if len(t.description) > 50 else t.description
                print(f"  {idx+1}. {t.date} - {t_desc} (Amount: {t.amount})")
            
            # Stop after finding a few examples
            if matches_found >= 10:
                break
    
    if matches_found == 0:
        print("No exact matches found in the 100 most recent payment postings")

def get_payment_postings():
    """Find ledger postings that are likely actual payments (not accounting entries)."""
    print("\nGetting specific posting IDs to try in the management command:")
    
    # Look for postings containing "Betaling" in the description
    payment_postings = LedgerPosting.objects.filter(
        description__icontains="Betaling"
    ).order_by('-date')[:20]
    
    for p in payment_postings:
        posting_desc = p.description[:50] + "..." if p.description and len(p.description) > 50 else (p.description or "No description")
        print(f"Posting ID: {p.posting_id}, Date: {p.date}, Description: {posting_desc}, Amount: {p.amount}")
        
        # Look for matching transactions
        matching_transactions = Transaction.objects.filter(
            date=p.date,
            amount=p.amount
        )
        
        if matching_transactions.exists():
            print(f"  Has {matching_transactions.count()} matching transactions")
        else:
            print("  No matching transactions")
    
if __name__ == "__main__":
    print_recent_data()
    check_matching_entries()
    get_payment_postings() 