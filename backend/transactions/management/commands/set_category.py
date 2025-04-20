#!/usr/bin/env python3
"""
Script to set the 'Salary' category for all transactions with is_wage_transfer=True or is_tax_transfer=True.
Also updates the supplier-category mapping for any suppliers associated with these transactions.
"""
import os
import sys
import django
from django.db import transaction
from datetime import datetime

# Add the project path to the system path
script_dir = os.path.dirname(os.path.abspath(__file__))
# Adjust path calculation: go up more levels to reach the project root (backend directory)
project_dir = os.path.abspath(os.path.join(script_dir, '../../../'))
sys.path.append(project_dir)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

# Import models after setting up Django
from transactions.models import Transaction, Category, CategorySupplierMap

def set_wage_transfer_categories():
    """
    Find all transactions with is_wage_transfer=True or is_tax_transfer=True and set their category to 'Salary'.
    Also update the CategorySupplierMap for any associated suppliers.
    """
    # Get or create the Salary category
    salary_category, created = Category.objects.get_or_create(
        name="Salary",
        defaults={"description": "Salary and wage payments"}
    )
    
    if created:
        print(f"Created new 'Salary' category with ID: {salary_category.id}")
    else:
        print(f"Using existing 'Salary' category with ID: {salary_category.id}")
    
    # Get all wage transfer and tax transfer transactions
    wage_transfers = Transaction.objects.filter(is_wage_transfer=True) | Transaction.objects.filter(is_tax_transfer=True)
    
    if not wage_transfers.exists():
        print("No wage transfer or tax transfer transactions found.")
        return
    
    print(f"Found {wage_transfers.count()} wage transfer and tax transfer transactions.")
    
    # Track counts for reporting
    updated_count = 0
    already_categorized_count = 0
    supplier_mappings_created = 0
    supplier_mappings_updated = 0
    
    # Use a transaction to ensure atomicity
    with transaction.atomic():
        # Process each transaction
        for tx in wage_transfers:
            if tx.category == salary_category:
                already_categorized_count += 1
                continue
            
            # Update the transaction category
            tx.category = salary_category
            tx.save()
            updated_count += 1
            
            # Update or create supplier mapping if this transaction has a supplier
            if tx.supplier:
                try:
                    # Try to get existing mapping
                    mapping, created = CategorySupplierMap.objects.update_or_create(
                        supplier=tx.supplier,
                        defaults={'category': salary_category}
                    )
                    
                    if created:
                        supplier_mappings_created += 1
                    else:
                        supplier_mappings_updated += 1
                except Exception as e:
                    print(f"Error updating supplier mapping for supplier '{tx.supplier.name}': {e}")
    
    # Print summary
    print("\nOperation completed successfully!")
    print("-" * 40)
    print(f"Transactions already categorized as 'Salary': {already_categorized_count}")
    print(f"Transactions updated to 'Salary' category: {updated_count}")
    print(f"New supplier-category mappings created: {supplier_mappings_created}")
    print(f"Existing supplier-category mappings updated: {supplier_mappings_updated}")
    print("-" * 40)
    print(f"Total transactions processed: {wage_transfers.count()}")
    
    return {
        "already_categorized": already_categorized_count,
        "updated": updated_count,
        "supplier_mappings_created": supplier_mappings_created,
        "supplier_mappings_updated": supplier_mappings_updated,
        "total_processed": wage_transfers.count()
    }

if __name__ == "__main__":
    print(f"Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Setting 'Salary' category for all wage transfer and tax transfer transactions...")
    result = set_wage_transfer_categories()
    print(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 