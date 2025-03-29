"""
Utility functions for working with the Tripletex API.
"""
import os
import json
import requests
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ..constants import (
    TRIPLETEX_API_BASE_URL,
    TRIPLETEX_API_BANK_STATEMENT_ENDPOINT,
    TRIPLETEX_API_TRANSACTION_ENDPOINT
)
from .paths import get_cache_file_path

logger = logging.getLogger('transactions')

def get_tripletex_credentials():
    """
    Get Tripletex API credentials from environment variables.
    
    Returns:
        dict: A dictionary containing the credentials needed for Tripletex API calls
    
    Raises:
        ValueError: If required environment variables are not set
    """
    company_id = os.getenv("3T_AUTH_USER")
    auth_token = os.getenv("3T_SESSION_TOKEN")
    
    if not auth_token:
        raise ValueError("TRIPLETEX_AUTH_TOKEN environment variable is not set.")
    
    return {
        'company_id': company_id,
        'auth_token': auth_token
    }

def get_api_headers():
    """
    Get headers for Tripletex API requests.
    
    Returns:
        dict: Headers for Tripletex API requests
    """
    credentials = get_tripletex_credentials()
    
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {credentials["auth_token"]}'
    }

def get_date_range(months_back=12):
    """
    Get a list of date ranges for Tripletex API requests.
    
    Args:
        months_back (int): Number of months to go back from current month
        
    Returns:
        list: List of dictionaries with from_date and to_date strings in YYYY-MM-DD format
    """
    today = datetime.now()
    
    # Generate monthly date ranges
    date_ranges = []
    for i in range(months_back, 0, -1):
        start_date = today - relativedelta(months=i)
        end_date = start_date + relativedelta(months=1) - timedelta(days=1)
        
        # Format dates as YYYY-MM-DD
        from_date = start_date.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')
        
        date_ranges.append({
            'from_date': from_date,
            'to_date': to_date
        })
    
    # Add current month
    start_of_month = datetime(today.year, today.month, 1)
    date_ranges.append({
        'from_date': start_of_month.strftime('%Y-%m-%d'),
        'to_date': today.strftime('%Y-%m-%d')
    })
    
    return date_ranges

def get_transaction_details(transaction_id):
    """
    Get detailed information about a specific transaction from Tripletex.
    
    Args:
        transaction_id (str): The ID of the transaction to get details for
        
    Returns:
        dict: Transaction details
        
    Raises:
        Exception: If the API request fails
    """
    headers = get_api_headers()
    url = f"{TRIPLETEX_API_BASE_URL}{TRIPLETEX_API_TRANSACTION_ENDPOINT}/{transaction_id}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except Exception as e:
        logger.error(f"Error getting transaction details for ID {transaction_id}: {str(e)}")
        raise

def load_transaction_cache():
    """
    Load transaction cache from disk.
    
    Returns:
        dict: Transaction cache data or empty dict if file doesn't exist
    """
    cache_file = get_cache_file_path('transaction_cache.json')
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as file:
                return json.load(file)
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {cache_file}")
            return {}
        except Exception as e:
            logger.error(f"Error loading transaction cache: {str(e)}")
            return {}
    
    return {}

def save_transaction_cache(cache_data):
    """
    Save transaction cache to disk.
    
    Args:
        cache_data (dict): Transaction cache data to save
    """
    cache_file = get_cache_file_path('transaction_cache.json')
    
    try:
        with open(cache_file, 'w') as file:
            json.dump(cache_data, file)
        logger.info(f"Saved {len(cache_data)} transactions to cache")
    except Exception as e:
        logger.error(f"Error saving transaction cache: {str(e)}")

def clean_bank_account_id(bank_id):
    """
    Clean bank account ID by removing special characters and trimming whitespace.
    
    Args:
        bank_id (str): Bank account ID to clean
        
    Returns:
        str: Cleaned bank account ID
    """
    if not bank_id:
        return ''
    
    # Convert to string if needed
    bank_id_str = str(bank_id)
    
    # Remove special characters and trim whitespace
    return bank_id_str.strip().replace(' ', '_').replace('-', '_') 