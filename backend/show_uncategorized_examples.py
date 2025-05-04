#!/usr/bin/env python3
"""
Script to show examples of transactions in the Uncategorized category.
"""
import os
import sys
import django
from datetime import datetime

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_visualizer.settings")
django.setup()

from django.db.models import Q
from transactions.models import Transaction, Category


def get_uncategorized_examples(count=5, start_date=None, end_date=None):
    """
    Get example transactions from the Uncategorized category.
    
    Args:
        count (int): Number of examples to show
        start_date (datetime, optional): Start date filter
        end_date (datetime, optional): End date filter
        
    Returns:
        List of transaction descriptions
    """
    # Try to find the 'Uncategorized' category
    try:
        uncategorized_category = Category.objects.get(name='Uncategorized')
    except Category.DoesNotExist:
        # If no exact match, try searching with case-insensitive name contains
        try:
            uncategorized_category = Category.objects.filter(
                name__icontains='uncategorized'
            ).first()
        except:
            print("No 'Uncategorized' category found.")
            return []
    
    if not uncategorized_category:
        print("No 'Uncategorized' category found.")
        return []
    
    # Set up query filter
    query_filter = Q(category=uncategorized_category)
    
    # Add date filters if provided
    if start_date:
        query_filter &= Q(date__gte=start_date)
    if end_date:
        query_filter &= Q(date__lt=end_date)
    
    # Get transactions from the Uncategorized category
    uncategorized_transactions = Transaction.objects.filter(
        query_filter
    ).exclude(
        is_internal_transfer=True  # Exclude internal transfers
    ).order_by('-amount')[:count]  # Order by amount, get top 'count'
    
    # Extract details as a list of tuples (amount, date, description)
    examples = []
    for trans in uncategorized_transactions:
        examples.append((
            trans.amount, 
            trans.date.strftime('%Y-%m-%d'),
            trans.description
        ))
    
    return examples


def main():
    # Set date range (same as the spending report)
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 4, 1)
    count = 5
    
    print(f"\nTop {count} Uncategorized Transactions ({start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}):")
    print("-" * 100)
    print(f"{'Amount (NOK)':<15} {'Date':<12} {'Description':<70}")
    print("-" * 100)
    
    examples = get_uncategorized_examples(count, start_date, end_date)
    
    if not examples:
        print("No uncategorized transactions found in the specified date range.")
        return
    
    for amount, date, description in examples:
        # Format the amount with a negative sign for expenses (amount < 0)
        formatted_amount = f"{amount:,.2f}".replace(",", " ")
        print(f"{formatted_amount:<15} {date:<12} {description[:70]}")
    
    print("-" * 100)


if __name__ == "__main__":
    main() 