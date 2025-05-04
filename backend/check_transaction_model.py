#!/usr/bin/env python
import os
import sys
import json
from pprint import pprint

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
import django
django.setup()

# Import models after Django setup
from transactions.models import Transaction

def check_transaction_model():
    """Check the Transaction model structure and fields, focusing on rawData and GroupedPosting."""
    # Print all fields
    fields = [f.name for f in Transaction._meta.get_fields()]
    print("All Transaction fields:")
    pprint(fields)
    print()
    
    # Get a sample transaction
    tx = Transaction.objects.first()
    if not tx:
        print("No transactions found in the database.")
        return
    
    # Check if transaction has raw_data that might contain GroupedPosting
    print("\nChecking raw_data field for GroupedPosting:")
    if hasattr(tx, 'raw_data') and tx.raw_data:
        try:
            raw_data = tx.raw_data
            print("Raw data type:", type(raw_data))
            
            if isinstance(raw_data, dict):
                print("\nTop-level keys in raw_data:")
                pprint(list(raw_data.keys()))
                
                # Examine 'value' field which might contain GroupedPosting
                if 'value' in raw_data:
                    value_data = raw_data['value']
                    print("\nValue field type:", type(value_data))
                    
                    if isinstance(value_data, dict):
                        print("\nKeys in value field:")
                        pprint(list(value_data.keys()))
                        
                        # Check for GroupedPosting or similar fields
                        grouped_posting_keys = [k for k in value_data.keys() if 'post' in k.lower()]
                        if grouped_posting_keys:
                            print("\nFound potential GroupedPosting keys:", grouped_posting_keys)
                            for key in grouped_posting_keys:
                                print(f"\nExamining '{key}':")
                                posting_data = value_data[key]
                                
                                if isinstance(posting_data, list):
                                    print(f"Number of items: {len(posting_data)}")
                                    if posting_data:
                                        print("First item keys:")
                                        pprint(list(posting_data[0].keys()) if isinstance(posting_data[0], dict) else "Not a dictionary")
                                        
                                        # Check if items have descriptions
                                        if isinstance(posting_data[0], dict) and 'description' in posting_data[0]:
                                            print("\nSample descriptions:")
                                            for i, item in enumerate(posting_data[:3]):  # Show first 3
                                                print(f"{i+1}. {item.get('description', 'No description')}")
                                else:
                                    print(f"Type: {type(posting_data)}")
                    
                    # Try to find any field that might contain "posting" at any level
                    def find_postings(data, path=""):
                        if isinstance(data, dict):
                            for k, v in data.items():
                                if 'post' in k.lower():
                                    print(f"Found potential posting field at {path}/{k}")
                                    if isinstance(v, list) and v:
                                        print(f"  Contains {len(v)} items")
                                        if isinstance(v[0], dict):
                                            print(f"  First item keys: {list(v[0].keys())}")
                                    elif isinstance(v, dict):
                                        print(f"  Keys: {list(v.keys())}")
                                find_postings(v, f"{path}/{k}")
                        elif isinstance(data, list):
                            for i, item in enumerate(data[:3]):  # Check first 3 items
                                find_postings(item, f"{path}[{i}]")
                    
                    print("\nSearching for posting-related fields in raw_data:")
                    find_postings(raw_data)
                
                # Check for specific fields in transaction
                sample_tx = Transaction.objects.filter(raw_data__isnull=False).first()
                if sample_tx and sample_tx.raw_data:
                    print("\nChecking a sample transaction with raw_data:")
                    try:
                        # Try to access fields directly
                        if 'value' in sample_tx.raw_data:
                            value = sample_tx.raw_data['value']
                            print("\nFound 'value' field in sample transaction")
                            
                            # Check for common field names
                            for field in ['postings', 'groupedPostings', 'ledgerPostings', 'postingList']:
                                if field in value:
                                    print(f"\nFound '{field}' in value:")
                                    postings = value[field]
                                    print(f"Type: {type(postings)}")
                                    if isinstance(postings, list):
                                        print(f"Number of items: {len(postings)}")
                                        if postings:
                                            print("First item keys:")
                                            pprint(list(postings[0].keys()) if isinstance(postings[0], dict) else "Not a dictionary")
                                            
                                            # Print sample descriptions
                                            descriptions = []
                                            for post in postings:
                                                if isinstance(post, dict) and 'description' in post:
                                                    descriptions.append(post['description'])
                                            
                                            if descriptions:
                                                print("\nSample descriptions from postings:")
                                                for i, desc in enumerate(descriptions[:3]):
                                                    print(f"{i+1}. {desc}")
                    except Exception as e:
                        print(f"Error examining sample transaction: {str(e)}")
        except Exception as e:
            print(f"Error processing raw_data: {str(e)}")
    else:
        print("raw_data is empty or not available")
    
    # Look at several transactions to find ones with postings
    print("\nSearching for transactions with grouped postings in raw_data:")
    count = 0
    for tx in Transaction.objects.filter(raw_data__isnull=False)[:30]:
        if tx.raw_data and isinstance(tx.raw_data, dict) and 'value' in tx.raw_data:
            value = tx.raw_data['value']
            if isinstance(value, dict):
                for key in value.keys():
                    if 'post' in key.lower():
                        print(f"\nTransaction {tx.id} has '{key}' in raw_data['value']")
                        postings = value[key]
                        if isinstance(postings, list) and postings:
                            print(f"  Number of items: {len(postings)}")
                            if isinstance(postings[0], dict):
                                print(f"  First item keys: {list(postings[0].keys())}")
                                if 'description' in postings[0]:
                                    print(f"  First description: {postings[0]['description']}")
                        count += 1
                        if count >= 5:  # Limit to 5 examples
                            break
        if count >= 5:
            break
    
    # Print sample transaction data
    print("\nSample transaction info:")
    print(f"ID: {tx.id}")
    print(f"Description: {tx.description}")
    print(f"Amount: {tx.amount}")
    print(f"Date: {tx.date}")
    print(f"Supplier: {tx.supplier}")
    print(f"Category: {tx.category}")

if __name__ == "__main__":
    check_transaction_model() 