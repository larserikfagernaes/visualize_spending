"""
Service layer for transaction-related operations.
Handles business logic for transactions.
"""
import logging
import os
import json
from datetime import datetime
import requests
from django.db import transaction
from django.db.models import Sum, Count
from django.utils.text import slugify

from ..models import Transaction, Category, BankAccount
from ..utils.tripletex import (
    get_api_headers, 
    get_date_range, 
    get_transaction_details,
    load_transaction_cache,
    save_transaction_cache,
    clean_bank_account_id
)
from ..constants import INTERNAL_TRANSFER_KEYWORDS, CATEGORY_KEYWORDS

logger = logging.getLogger('transactions')

def get_all_transactions(filters=None):
    """
    Get all transactions with optional filtering.
    
    Args:
        filters (dict): Optional filters to apply to the queryset
        
    Returns:
        QuerySet: Filtered transaction queryset
    """
    queryset = Transaction.objects.all().order_by('-date')
    
    if not filters:
        return queryset
    
    # Apply filters
    if 'date_from' in filters and filters['date_from']:
        queryset = queryset.filter(date__gte=filters['date_from'])
    
    if 'date_to' in filters and filters['date_to']:
        queryset = queryset.filter(date__lte=filters['date_to'])
    
    if 'category' in filters and filters['category']:
        queryset = queryset.filter(category_id=filters['category'])
    
    if 'search' in filters and filters['search']:
        queryset = queryset.filter(description__icontains=filters['search'])
    
    if 'bank_account' in filters and filters['bank_account']:
        queryset = queryset.filter(bank_account_id=filters['bank_account'])
    
    if 'amount_min' in filters and filters['amount_min']:
        queryset = queryset.filter(amount__gte=filters['amount_min'])
    
    if 'amount_max' in filters and filters['amount_max']:
        queryset = queryset.filter(amount__lte=filters['amount_max'])
    
    if 'internal_transfer' in filters:
        queryset = queryset.filter(is_internal_transfer=filters['internal_transfer'])
    
    if 'should_process' in filters:
        queryset = queryset.filter(should_process=filters['should_process'])
    
    return queryset

def get_transaction_by_id(transaction_id):
    """
    Get a transaction by its ID.
    
    Args:
        transaction_id (int): The ID of the transaction to get
        
    Returns:
        Transaction: The transaction object or None if not found
    """
    try:
        return Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        logger.error(f"Transaction with ID {transaction_id} not found")
        return None

def get_transaction_by_tripletex_id(tripletex_id):
    """
    Get a transaction by its Tripletex ID.
    
    Args:
        tripletex_id (str): The Tripletex ID of the transaction to get
        
    Returns:
        Transaction: The transaction object or None if not found
    """
    try:
        return Transaction.objects.get(tripletex_id=tripletex_id)
    except Transaction.DoesNotExist:
        logger.debug(f"Transaction with Tripletex ID {tripletex_id} not found")
        return None

def get_transaction_summary(filters=None):
    """
    Get a summary of transactions including total amount, count, and category breakdown.
    
    Args:
        filters (dict): Optional filters to apply to the queryset
        
    Returns:
        dict: Transaction summary data
    """
    transactions = get_all_transactions(filters)
    
    # Get total count and amount
    total_transactions = transactions.count()
    total_amount = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get category breakdown
    categories = {}
    category_breakdown = transactions.values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    for item in category_breakdown:
        category_name = item['category__name'] or 'Uncategorized'
        categories[category_name] = {
            'total': float(item['total']) if item['total'] else 0,
            'count': item['count'],
            'percentage': round((float(item['total'] or 0) / float(total_amount)) * 100, 2) if total_amount else 0
        }
    
    # Get bank account breakdown
    bank_accounts = {}
    account_breakdown = transactions.values('bank_account__name', 'bank_account_id').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    for item in account_breakdown:
        account_name = item['bank_account__name'] or item['bank_account_id'] or 'Unknown'
        bank_accounts[account_name] = {
            'total': float(item['total']) if item['total'] else 0,
            'count': item['count'],
            'percentage': round((float(item['total'] or 0) / float(total_amount)) * 100, 2) if total_amount else 0
        }
    
    # Get related accounts breakdown
    related_accounts = {}
    for transaction in transactions.prefetch_related('transaction_accounts__account'):
        for ta in transaction.transaction_accounts.all():
            if ta.account:
                account_name = ta.account.name or ta.account.account_number or f"Account {ta.account.id}"
                amount = float(ta.amount) if ta.amount else float(transaction.amount)
                
                if account_name not in related_accounts:
                    related_accounts[account_name] = {
                        'total': 0,
                        'count': 0,
                        'percentage': 0
                    }
                
                related_accounts[account_name]['total'] += abs(amount)
                related_accounts[account_name]['count'] += 1
    
    # Calculate percentages for related accounts
    total_related_amount = sum(acc['total'] for acc in related_accounts.values())
    for account_name, data in related_accounts.items():
        if total_related_amount > 0:
            data['percentage'] = round((data['total'] / total_related_amount) * 100, 2)
    
    return {
        'total_transactions': total_transactions,
        'total_amount': float(total_amount),
        'categories': categories,
        'bank_accounts': bank_accounts,
        'related_accounts': related_accounts
    }

def update_transaction_category(transaction_id, category_id):
    """
    Update the category of a transaction.
    
    Args:
        transaction_id (int): The ID of the transaction to update
        category_id (int): The ID of the category to assign
        
    Returns:
        bool: True if successful, False otherwise
    """
    transaction = get_transaction_by_id(transaction_id)
    if not transaction:
        return False
    
    try:
        category = Category.objects.get(id=category_id) if category_id else None
        transaction.category = category
        transaction.save()
        logger.info(f"Updated category for transaction {transaction_id} to {category.name if category else 'None'}")
        return True
    except Category.DoesNotExist:
        logger.error(f"Category with ID {category_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error updating category for transaction {transaction_id}: {str(e)}")
        return False

def import_transactions_from_tripletex():
    """
    Import transactions from Tripletex API.
    
    Returns:
        dict: Summary of import operation
    """
    headers = get_api_headers()
    date_ranges = get_date_range()
    
    # Initialize cache
    transaction_cache = load_transaction_cache()
    
    # Track stats
    new_count = 0
    updated_count = 0
    error_count = 0
    
    # Process each date range
    for date_range in date_ranges:
        try:
            # Get transactions for this date range
            url = f"{TRIPLETEX_API_BASE_URL}/bank/statement/list"
            params = {
                'from': date_range['from_date'],
                'to': date_range['to_date'],
                'fields': 'id,postings,accountingDate,amountOut,amountIn,description'
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            statements = response.json().get('values', [])
            logger.info(f"Retrieved {len(statements)} bank statements for {date_range['from_date']} to {date_range['to_date']}")
            
            # Process each statement
            with transaction.atomic():
                for statement in statements:
                    try:
                        # Extract transaction details
                        transaction_id = statement.get('id')
                        
                        # Skip if no transaction ID
                        if not transaction_id:
                            continue
                        
                        # Get details from API
                        transaction_details = get_transaction_details(transaction_id)
                        
                        # Cache transaction details
                        transaction_cache[str(transaction_id)] = transaction_details
                        
                        # Extract data
                        description = statement.get('description', '')
                        date_str = statement.get('accountingDate', '')
                        date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
                        
                        # Calculate amount (in - out)
                        amount_in = float(statement.get('amountIn', 0) or 0)
                        amount_out = float(statement.get('amountOut', 0) or 0)
                        amount = amount_in - amount_out
                        
                        # Get bank account info
                        bank_account_name = None
                        bank_account_obj = None
                        account_id = None
                        
                        if 'postings' in statement and statement['postings']:
                            bank_posting = statement['postings'][0]
                            account_id = bank_posting.get('account', {}).get('number')
                            bank_account_name = bank_posting.get('account', {}).get('name')
                            
                            # Create or get bank account
                            if bank_account_name:
                                bank_account_obj, created = BankAccount.objects.get_or_create(
                                    name=bank_account_name,
                                    defaults={
                                        'account_number': account_id
                                    }
                                )
                        
                        # Check if transaction already exists
                        existing = get_transaction_by_tripletex_id(str(transaction_id))
                        
                        if existing:
                            # Update existing transaction
                            existing.description = description
                            existing.amount = amount
                            existing.date = date
                            existing.bank_account_id = clean_bank_account_id(bank_account_name)
                            existing.account_id = account_id
                            existing.raw_data = transaction_details
                            existing.bank_account = bank_account_obj
                            existing.save()
                            updated_count += 1
                        else:
                            # Create new transaction
                            new_transaction = Transaction(
                                tripletex_id=str(transaction_id),
                                description=description,
                                amount=amount,
                                date=date,
                                bank_account_id=clean_bank_account_id(bank_account_name),
                                account_id=account_id,
                                raw_data=transaction_details,
                                bank_account=bank_account_obj
                            )
                            new_transaction.save()
                            new_count += 1
                            
                            # Check for internal transfers
                            detect_internal_transfer(new_transaction)
                            
                            # Auto-categorize
                            auto_categorize_transaction(new_transaction)
                    
                    except Exception as e:
                        logger.error(f"Error processing transaction {transaction_id}: {str(e)}")
                        error_count += 1
        
        except Exception as e:
            logger.error(f"Error retrieving transactions for {date_range['from_date']} to {date_range['to_date']}: {str(e)}")
            error_count += 1
    
    # Save cache
    save_transaction_cache(transaction_cache)
    
    # Return summary
    return {
        'new_transactions': new_count,
        'updated_transactions': updated_count,
        'errors': error_count
    }

def detect_internal_transfer(transaction_obj):
    """
    Detect if a transaction is an internal transfer.
    
    Args:
        transaction_obj (Transaction): The transaction to check
        
    Returns:
        bool: True if internal transfer was detected, False otherwise
    """
    if not transaction_obj:
        return False
    
    # Check description for keywords
    description = transaction_obj.description.lower() if transaction_obj.description else ''
    
    is_internal = any(keyword in description for keyword in INTERNAL_TRANSFER_KEYWORDS)
    
    if is_internal:
        transaction_obj.is_internal_transfer = True
        transaction_obj.save()
        logger.info(f"Detected internal transfer: {transaction_obj.description}")
        return True
    
    # Check raw data if available
    if transaction_obj.raw_data:
        try:
            # Add additional checks for raw data if needed
            pass
        except Exception as e:
            logger.error(f"Error parsing raw data for transaction {transaction_obj.id}: {str(e)}")
    
    return False

def auto_categorize_transaction(transaction_obj):
    """
    Automatically categorize a transaction based on its description.
    
    Args:
        transaction_obj (Transaction): The transaction to categorize
        
    Returns:
        bool: True if categorization was successful, False otherwise
    """
    if not transaction_obj or transaction_obj.category:
        return False
    
    description = transaction_obj.description.lower() if transaction_obj.description else ''
    
    # Skip internal transfers
    if transaction_obj.is_internal_transfer:
        return False
    
    # Try to match keywords to categories
    for category_name, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in description for keyword in keywords):
            try:
                category = Category.objects.get(name=category_name)
                transaction_obj.category = category
                transaction_obj.save()
                logger.info(f"Auto-categorized transaction {transaction_obj.id} to {category_name}")
                return True
            except Category.DoesNotExist:
                logger.warning(f"Category {category_name} not found")
    
    return False

def update_all_internal_transfers():
    """
    Update all transactions to identify internal transfers.
    
    Returns:
        dict: Summary of update operation
    """
    transactions = Transaction.objects.all()
    
    updated_count = 0
    already_marked_count = 0
    
    for transaction_obj in transactions:
        was_internal = transaction_obj.is_internal_transfer
        
        if detect_internal_transfer(transaction_obj):
            if was_internal:
                already_marked_count += 1
            else:
                updated_count += 1
    
    return {
        'updated_transactions': updated_count,
        'already_marked': already_marked_count,
        'total_processed': transactions.count()
    } 