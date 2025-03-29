from django.shortcuts import render
import os
import json
from decimal import Decimal
from django.db.models import Sum, Count
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from .models import BankStatement, Transaction, Category
from .serializers import BankStatementSerializer, TransactionSerializer, CategorySerializer, TransactionSummarySerializer
import datetime
import decimal
from .get_transactions import get_current_directory

# Create your views here.

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().order_by('-date')
    serializer_class = TransactionSerializer

    @action(detail=True, methods=['get'])
    def detail_with_raw_data(self, request, pk=None):
        """
        Retrieve a transaction with its raw data.
        This endpoint is useful for debugging and analysis of transaction data.
        
        If raw_data is not present, it will attempt to populate it from the transaction_cache.json file
        and save it to the database for future requests.
        """
        try:
            transaction = self.get_object()
            
            # Check if raw_data needs to be populated
            if transaction.raw_data is None and transaction.tripletex_id:
                print(f"Transaction {transaction.id} needs raw_data, tripletex_id: {transaction.tripletex_id}")
                
                # Look for the transaction in both cache files
                main_cache_file = os.path.join(get_current_directory(), "transaction_cache.json")
                alt_cache_file = os.path.join(get_current_directory(), "cache", "transaction_cache.json")
                
                # Try both cache files
                for cache_file in [main_cache_file, alt_cache_file]:
                    if os.path.exists(cache_file):
                        try:
                            print(f"Checking cache file: {cache_file}")
                            with open(cache_file) as file:
                                transaction_cache = json.load(file)
                            
                            # Try exact match first
                            if transaction.tripletex_id in transaction_cache:
                                print(f"Found exact match for tripletex_id: {transaction.tripletex_id}")
                                detailed_data = transaction_cache[transaction.tripletex_id]
                                
                                # Create raw_data structure
                                raw_data = {
                                    "transaction": {
                                        "id": transaction.tripletex_id,
                                        "description": transaction.description,
                                        "amount": float(transaction.amount)
                                    },
                                    "detailed_data": detailed_data,
                                    "processed_data": {
                                        "bank_account_name": transaction.bank_account_id,
                                        "amount": float(transaction.amount),
                                        "description": transaction.description,
                                        "is_forbidden": transaction.is_forbidden,
                                        "is_internal_transfer": transaction.is_internal_transfer,
                                        "is_wage_transfer": transaction.is_wage_transfer,
                                        "is_tax_transfer": transaction.is_tax_transfer,
                                        "should_process": transaction.should_process,
                                        "account_id": transaction.account_id
                                    },
                                    "statement": {
                                        "fromDate": transaction.date.strftime("%Y-%m-%d")
                                    }
                                }
                                
                                # Update transaction
                                transaction.raw_data = raw_data
                                transaction.save()
                                print(f"Populated raw_data for transaction {transaction.id} (tripletex_id: {transaction.tripletex_id})")
                                break  # Exit the loop if we found a match
                            else:
                                # If not found, print first 5 keys from cache for debugging
                                cache_keys = list(transaction_cache.keys())[:5]
                                print(f"No match for tripletex_id: {transaction.tripletex_id}. Sample cache keys: {cache_keys}")
                                
                                # Try searching for a substring match if the ID might have been modified
                                if transaction.tripletex_id.isdigit():
                                    for cache_key in transaction_cache.keys():
                                        if cache_key.isdigit() and cache_key.endswith(transaction.tripletex_id[-5:]):
                                            print(f"Found potential match: {cache_key} for tripletex_id: {transaction.tripletex_id}")
                                            detailed_data = transaction_cache[cache_key]
                                            
                                            # Create raw_data structure
                                            raw_data = {
                                                "transaction": {
                                                    "id": cache_key,
                                                    "original_id": transaction.tripletex_id,
                                                    "description": transaction.description,
                                                    "amount": float(transaction.amount)
                                                },
                                                "detailed_data": detailed_data,
                                                "processed_data": {
                                                    "bank_account_name": transaction.bank_account_id,
                                                    "amount": float(transaction.amount),
                                                    "description": transaction.description,
                                                    "is_forbidden": transaction.is_forbidden,
                                                    "is_internal_transfer": transaction.is_internal_transfer,
                                                    "is_wage_transfer": transaction.is_wage_transfer,
                                                    "is_tax_transfer": transaction.is_tax_transfer,
                                                    "should_process": transaction.should_process,
                                                    "account_id": transaction.account_id
                                                },
                                                "statement": {
                                                    "fromDate": transaction.date.strftime("%Y-%m-%d")
                                                }
                                            }
                                            
                                            # Update transaction
                                            transaction.raw_data = raw_data
                                            transaction.save()
                                            print(f"Populated raw_data using partial match: {cache_key} for transaction {transaction.id}")
                                            break
                        except Exception as e:
                            print(f"Error processing cache file {cache_file}: {e}")
            
            serializer = self.get_serializer(transaction)
            return Response(serializer.data)
        except Transaction.DoesNotExist:
            return Response(
                {"error": "Transaction not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Unexpected error in detail_with_raw_data: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Failed to retrieve transaction details: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        # Get total number of transactions
        total_transactions = Transaction.objects.count()
        
        # Get total amount
        total_amount = Transaction.objects.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        # Get summary by category
        categories = {}
        category_summary = Transaction.objects.values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        for item in category_summary:
            category_name = item['category__name'] or 'Uncategorized'
            categories[category_name] = {
                'total': float(item['total']),
                'count': item['count']
            }
        
        # Get summary by bank account
        bank_accounts = {}
        bank_account_summary = Transaction.objects.values('bank_account_id').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        for item in bank_account_summary:
            bank_account_id = item['bank_account_id'] or 'Unknown'
            bank_accounts[bank_account_id] = {
                'total': float(item['total']),
                'count': item['count']
            }
        
        summary_data = {
            'total_transactions': total_transactions,
            'total_amount': float(total_amount),
            'categories': categories,
            'bank_accounts': bank_accounts
        }
        
        serializer = TransactionSummarySerializer(summary_data)
        return Response(serializer.data)

class BankStatementViewSet(viewsets.ModelViewSet):
    queryset = BankStatement.objects.all().order_by('-date')
    serializer_class = BankStatementSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer

@api_view(['POST'])
def import_transactions(request):
    """Import transactions from JSON files in the data directory."""
    data_dir = os.path.join(settings.BASE_DIR, 'data')
    
    if not os.path.exists(data_dir):
        return Response({"error": "Data directory not found"}, status=status.HTTP_404_NOT_FOUND)
    
    files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    
    if not files:
        return Response({"error": "No JSON files found in data directory"}, status=status.HTTP_404_NOT_FOUND)
    
    transaction_count = 0
    
    for file_name in files:
        file_path = os.path.join(data_dir, file_name)
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
                for item in data:
                    # Adapt this to match your JSON structure
                    bank_statement = BankStatement(
                        description=item.get('description', ''),
                        amount=Decimal(str(item.get('amount', 0))),
                        date=item.get('date', ''),
                        source_file=file_name
                    )
                    bank_statement.save()
                    transaction_count += 1
                    
        except Exception as e:
            return Response({"error": f"Error processing file {file_name}: {str(e)}"}, 
                           status=status.HTTP_400_BAD_REQUEST)
    
    return Response({"message": f"Successfully imported {transaction_count} bank statements", 
                    "count": transaction_count})

@api_view(['POST'])
def categorize_transaction(request, transaction_id):
    """Categorize a transaction."""
    try:
        transaction = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
    
    category_id = request.data.get('category_id')
    
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            transaction.category = category
        except Category.DoesNotExist:
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
    else:
        transaction.category = None
    
    transaction.save()
    serializer = TransactionSerializer(transaction)
    return Response(serializer.data)

@api_view(['POST'])
def import_from_tripletex(request):
    """Import transactions from Tripletex using get_transactions.py."""
    from .get_transactions import get_all_bank_statements
    
    try:
        # Create Expense and Income categories
        expense_category, _ = Category.objects.get_or_create(
            name="Expenses",
            defaults={"description": "All expenses imported from Tripletex"}
        )
        
        income_category, _ = Category.objects.get_or_create(
            name="Income",
            defaults={"description": "All income imported from Tripletex"}
        )
        
        # Get bank statements from Tripletex
        data = get_all_bank_statements(force_refresh=False, cache_days=1)
        
        # Transaction counters
        transactions_imported = 0
        transactions_skipped = 0
        
        # Process each bank statement
        for statement in data["values"]:
            # Each statement contains multiple transactions
            for tx in statement.get("transactions", []):
                if "detailed_data" not in tx or "processed_data" not in tx:
                    transactions_skipped += 1
                    continue
                
                # Get transaction details
                detail = tx["detailed_data"].get("value", {})
                processed = tx["processed_data"]
                
                # Skip if necessary data is missing
                tx_id = detail.get("id", None)
                if not tx_id:
                    transactions_skipped += 1
                    continue
                
                # Check if transaction already exists
                if Transaction.objects.filter(tripletex_id=str(tx_id)).exists():
                    transactions_skipped += 1
                    continue
                
                # Extract needed fields
                description = detail.get("description", "")
                amount_currency = detail.get("amountCurrency")
                date_str = detail.get("date")
                
                if not description or amount_currency is None or not date_str:
                    transactions_skipped += 1
                    continue
                
                try:
                    amount = Decimal(str(amount_currency))
                    date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                except (ValueError, decimal.InvalidOperation):
                    transactions_skipped += 1
                    continue
                
                # Choose category based on amount
                category = income_category if amount >= 0 else expense_category
                
                # Create the transaction
                Transaction.objects.create(
                    tripletex_id=str(tx_id),
                    description=description,
                    amount=amount,
                    date=date,
                    bank_account_id=processed.get("bank_account_id", ""),
                    is_internal_transfer=processed.get("is_internal_transfer", False),
                    is_wage_transfer=processed.get("is_wage_transfer", False),
                    is_tax_transfer=processed.get("is_tax_transfer", False),
                    is_forbidden=processed.get("is_forbidden", False),
                    should_process=processed.get("should_process", True),
                    category=category
                )
                
                transactions_imported += 1
        
        return Response({
            "message": f"Successfully imported {transactions_imported} transactions",
            "imported": transactions_imported,
            "skipped": transactions_skipped
        })
        
    except Exception as e:
        return Response({"error": f"Error importing from Tripletex: {str(e)}"}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def analyze_transfers(request):
    """
    Analyze transactions to identify potential internal transfers.
    Returns statistics and details to help improve internal transfer detection.
    """
    # Get all transactions
    transactions = Transaction.objects.all()
    
    # Get internal transfers
    internal_transfers = Transaction.objects.filter(is_internal_transfer=True)
    
    # Analyze descriptions and look for patterns
    description_patterns = {}
    raw_data_analysis = []
    
    # Analyze current internal transfers
    for transaction in internal_transfers[:100]:  # Limit to 100 for performance
        description = transaction.description.lower()
        
        # Count description patterns
        words = set(description.split())
        for word in words:
            if len(word) > 3:  # Skip small words
                if word in description_patterns:
                    description_patterns[word] += 1
                else:
                    description_patterns[word] = 1
        
        # Analyze raw data if available
        if transaction.raw_data:
            postings = transaction.raw_data.get('detailed_data', {}).get('value', {}).get('groupedPostings', [])
            posting_descriptions = [posting.get('description') for posting in postings if posting.get('description')]
            
            if posting_descriptions:
                raw_data_analysis.append({
                    'id': transaction.id,
                    'description': transaction.description,
                    'amount': float(transaction.amount),
                    'posting_descriptions': posting_descriptions
                })
    
    # Find common patterns in raw data
    posting_patterns = {}
    for analysis in raw_data_analysis:
        for desc in analysis.get('posting_descriptions', []):
            if desc in posting_patterns:
                posting_patterns[desc] += 1
            else:
                posting_patterns[desc] = 1
    
    # Sort patterns by frequency
    sorted_description_patterns = sorted(
        description_patterns.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:20]  # Top 20
    
    sorted_posting_patterns = sorted(
        posting_patterns.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:10]  # Top 10
    
    # Return analysis
    return Response({
        'total_transactions': transactions.count(),
        'internal_transfers': internal_transfers.count(),
        'internal_transfer_percentage': round((internal_transfers.count() / transactions.count()) * 100, 2),
        'common_description_patterns': dict(sorted_description_patterns),
        'common_posting_patterns': dict(sorted_posting_patterns),
        'raw_data_samples': raw_data_analysis[:10]  # First 10 samples
    })
