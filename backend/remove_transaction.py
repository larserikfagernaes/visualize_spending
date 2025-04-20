#!/usr/bin/env python3
"""
Script to remove a specific transaction ID from the transaction_cache.json file
"""
import os
import json
import sys

def get_current_directory():
    """Returns the absolute directory path of the current file."""
    return os.path.dirname(os.path.abspath(__file__))

def remove_transaction_from_cache(transaction_id):
    """
    Remove a transaction from the transaction cache file
    
    Args:
        transaction_id: The ID of the transaction to remove
    
    Returns:
        bool: True if the transaction was removed, False otherwise
    """
    # Convert transaction_id to string to ensure it matches the cache keys
    transaction_id = str(transaction_id)
    
    # Path to transaction cache file
    cache_file = os.path.join(get_current_directory(), "transactions", "cache", "transaction_cache.json")
    
    # Check if cache file exists
    if not os.path.exists(cache_file):
        print(f"Cache file not found at {cache_file}")
        return False
    
    # Load transaction cache
    with open(cache_file, 'r') as file:
        try:
            cache_data = json.load(file)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {cache_file}")
            return False
    
    # Check if transaction ID exists in cache
    if transaction_id not in cache_data:
        print(f"Transaction ID {transaction_id} not found in cache")
        return False
    
    # Remove transaction from cache
    del cache_data[transaction_id]
    print(f"Removed transaction ID {transaction_id} from cache")
    
    # Save updated cache
    with open(cache_file, 'w') as file:
        json.dump(cache_data, file)
    
    print(f"Cache updated. New cache contains {len(cache_data)} transactions.")
    return True

if __name__ == "__main__":
    # If a transaction ID is provided as an argument, use it, otherwise use the hardcoded ID
    transaction_id = sys.argv[1] if len(sys.argv) > 1 else "84525444"
    
    print(f"Removing transaction ID {transaction_id} from cache...")
    remove_transaction_from_cache(transaction_id) 