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

# Create your views here.

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().order_by('-date')
    serializer_class = TransactionSerializer

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
