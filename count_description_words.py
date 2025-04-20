#!/usr/bin/env python3
import os
import sys
import django

# Set up Django environment
sys.path.append('/Users/larserik/Aviant/programming/visualise_spending/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

# Import the Transaction model after Django setup
from transactions.models import Transaction

def count_description_words():
    # Get all transaction descriptions
    descriptions = Transaction.objects.values_list('description', flat=True)
    
    # Count words in all descriptions
    total_words = 0
    for desc in descriptions:
        if desc:  # Check if description is not None or empty
            words = desc.split()
            total_words += len(words)
    
    print(f"Total number of words across all transaction descriptions: {total_words}")
    print(f"Total number of transactions with descriptions: {descriptions.count()}")
    
    # Calculate average words per description
    if descriptions.count() > 0:
        avg_words = total_words / descriptions.count()
        print(f"Average words per description: {avg_words:.2f}")

if __name__ == "__main__":
    count_description_words() 