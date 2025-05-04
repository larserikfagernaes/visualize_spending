#!/usr/bin/env python3
"""
Script to calculate average monthly spending per category between Jan 1, 2025 and Apr 1, 2025.
"""
import os
import sys
import django
from datetime import datetime
from decimal import Decimal
import locale

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_visualizer.settings")
django.setup()

# Set locale for number formatting with spaces
try:
    locale.setlocale(locale.LC_ALL, 'nb_NO.UTF-8')  # Norwegian locale
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')  # Fallback to US locale
    except locale.Error:
        pass  # Use default locale if others fail

from django.db.models import Sum
from transactions.models import Transaction, Category


def format_number(value):
    """Format number with spaces as thousand separators"""
    try:
        # Try to use locale-specific formatting with spaces
        return locale.format_string("%.2f", value, grouping=True)
    except:
        # Fallback formatting with manual spaces
        value_str = f"{value:.2f}"
        parts = value_str.split('.')
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else "00"
        
        # Add spaces every 3 digits from the right
        result = ""
        for i, char in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                result = " " + result
            result = char + result
            
        return f"{result}.{decimal_part}"


def calculate_category_averages(start_date, end_date, months_count=3):
    """
    Calculate average monthly spending per category between given dates.
    
    Args:
        start_date (datetime): Start date for the calculation
        end_date (datetime): End date for the calculation
        months_count (int): Number of months to divide by for average
        
    Returns:
        List of tuples with category name and average monthly spending
    """
    # Filter transactions by date range
    transactions = Transaction.objects.filter(
        date__gte=start_date,
        date__lt=end_date,
        # Exclude internal transfers as they don't represent actual spending
        is_internal_transfer=False,
        # Only include negative amounts (expenses)
        amount__lt=0
        # Keep wage and tax transfers included
    ).exclude(
        category=None  # Exclude transactions without a category
    )
    
    # Group transactions by category and sum amounts
    category_spending = transactions.values('category__name').annotate(
        total=Sum('amount')
    )
    
    # Calculate monthly averages and sort by absolute amount (highest first)
    category_averages = []
    for item in category_spending:
        category_name = item['category__name']
        total_amount = item['total']
        monthly_average = abs(total_amount) / months_count
        category_averages.append((category_name, total_amount, monthly_average))
    
    # Sort by absolute total amount, descending
    category_averages.sort(key=lambda x: abs(x[1]), reverse=True)
    
    return category_averages


def main():
    # Set date range: Jan 1, 2025 to Apr 1, 2025
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 4, 1)
    months_count = 3
    
    print(f"\nCategory Expense Report: {start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}")
    print(f"Monthly averages over {months_count} months (expenses only - negative amounts):")
    print("-" * 80)
    print(f"{'Category':<30} {'Total (NOK)':<20} {'Monthly Avg (NOK)':<20}")
    print("-" * 80)
    
    category_averages = calculate_category_averages(start_date, end_date, months_count)
    
    total_spending = Decimal('0.00')
    total_monthly_avg = Decimal('0.00')
    
    for name, total, monthly_avg in category_averages:
        total_spending += abs(total)
        total_monthly_avg += monthly_avg
        print(f"{name:<30} {format_number(abs(total)):<20} {format_number(monthly_avg):<20}")
    
    print("-" * 80)
    print(f"{'TOTAL':<30} {format_number(total_spending):<20} {format_number(total_monthly_avg):<20}")
    print("-" * 80)


if __name__ == "__main__":
    main() 