"""
API views for the transactions app.
"""
import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..models import Transaction, Category, BankStatement, BankAccount
from .serializers import (
    TransactionSerializer,
    TransactionDetailSerializer,
    CategorySerializer,
    BankStatementSerializer,
    BankAccountSerializer,
    TransactionSummarySerializer,
    TransactionCategoryUpdateSerializer
)
from ..services.transaction_service import (
    get_transaction_summary,
    update_transaction_category,
    import_transactions_from_tripletex,
    update_all_internal_transfers
)
from ..services.category_service import (
    initialize_default_categories
)

logger = logging.getLogger('transactions')

class TransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing transactions.
    """
    queryset = Transaction.objects.all().order_by('-date')
    serializer_class = TransactionSerializer
    permission_classes = [AllowAny]  # Update this based on your security requirements
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'date', 'is_internal_transfer', 'is_wage_transfer', 'is_tax_transfer', 'should_process']
    search_fields = ['description', 'tripletex_id', 'bank_account_id']
    ordering_fields = ['date', 'amount', 'description']
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on action.
        """
        if self.action == 'retrieve' or self.action == 'detail_with_raw_data':
            return TransactionDetailSerializer
        return TransactionSerializer
    
    @swagger_auto_schema(
        operation_description="Get detailed transaction information including raw data",
        responses={200: TransactionDetailSerializer}
    )
    @action(detail=True, methods=['get'])
    def detail_with_raw_data(self, request, pk=None):
        """
        Retrieve a transaction with its raw data.
        """
        transaction = self.get_object()
        serializer = TransactionDetailSerializer(transaction)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get transaction summary statistics",
        responses={200: TransactionSummarySerializer}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get summary statistics for transactions.
        """
        # Get query parameters for filtering
        filters = {}
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        category_id = request.query_params.get('category')
        bank_account_id = request.query_params.get('bank_account')
        
        if date_from:
            filters['date_from'] = date_from
        
        if date_to:
            filters['date_to'] = date_to
            
        if category_id:
            filters['category'] = category_id
            
        if bank_account_id:
            filters['bank_account'] = bank_account_id
        
        # Get summary data
        summary_data = get_transaction_summary(filters)
        
        # Serialize and return
        serializer = TransactionSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Update transaction category",
        request_body=TransactionCategoryUpdateSerializer,
        responses={
            200: openapi.Response(description="Category updated successfully"),
            400: openapi.Response(description="Invalid request"),
            404: openapi.Response(description="Transaction not found")
        }
    )
    @action(detail=True, methods=['post'])
    def update_category(self, request, pk=None):
        """
        Update the category of a transaction.
        """
        transaction = self.get_object()
        
        # Validate request data
        serializer = TransactionCategoryUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update category
        category_id = serializer.validated_data.get('category_id')
        success = update_transaction_category(transaction.id, category_id)
        
        if success:
            return Response({"status": "success", "message": "Category updated"})
        else:
            return Response(
                {"status": "error", "message": "Failed to update category"},
                status=status.HTTP_400_BAD_REQUEST
            )

class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing categories.
    """
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]  # Update this based on your security requirements
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']
    
    @swagger_auto_schema(
        operation_description="Initialize default categories",
        responses={200: openapi.Response(description="Categories initialized successfully")}
    )
    @action(detail=False, methods=['post'])
    def initialize(self, request):
        """
        Initialize default categories if they don't exist.
        """
        created_count = initialize_default_categories()
        return Response({
            "status": "success",
            "message": f"Initialized {created_count} categories"
        })

class BankAccountViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing bank accounts.
    """
    queryset = BankAccount.objects.all().order_by('name')
    serializer_class = BankAccountSerializer
    permission_classes = [AllowAny]  # Update this based on your security requirements
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'account_number', 'bank_name']

class BankStatementViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing bank statements.
    """
    queryset = BankStatement.objects.all().order_by('-date')
    serializer_class = BankStatementSerializer
    permission_classes = [AllowAny]  # Update this based on your security requirements
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'date']
    search_fields = ['description', 'source_file']
    ordering_fields = ['date', 'amount', 'description']

@swagger_auto_schema(
    method='post',
    operation_description="Import transactions from Tripletex",
    responses={
        200: openapi.Response(description="Import successful", schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, description="Status of the import"),
                'new_transactions': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of new transactions imported"),
                'updated_transactions': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of transactions updated"),
                'errors': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of errors encountered")
            }
        )),
        400: openapi.Response(description="Import failed")
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])  # Update this based on your security requirements
def import_from_tripletex(request):
    """
    Import transactions from Tripletex API.
    """
    try:
        import_result = import_transactions_from_tripletex()
        
        return Response({
            "status": "success",
            "new_transactions": import_result['new_transactions'],
            "updated_transactions": import_result['updated_transactions'],
            "errors": import_result['errors']
        })
    except Exception as e:
        logger.error(f"Error importing transactions: {str(e)}")
        return Response(
            {"status": "error", "message": f"Import failed: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

@swagger_auto_schema(
    method='post',
    operation_description="Update internal transfers",
    responses={
        200: openapi.Response(description="Update successful", schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, description="Status of the update"),
                'updated_transactions': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of transactions updated"),
                'already_marked': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of transactions already marked as internal transfers"),
                'total_processed': openapi.Schema(type=openapi.TYPE_INTEGER, description="Total number of transactions processed")
            }
        ))
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])  # Update this based on your security requirements
def analyze_transfers(request):
    """
    Analyze transactions to identify internal transfers.
    """
    try:
        update_result = update_all_internal_transfers()
        
        return Response({
            "status": "success",
            "updated_transactions": update_result['updated_transactions'],
            "already_marked": update_result['already_marked'],
            "total_processed": update_result['total_processed']
        })
    except Exception as e:
        logger.error(f"Error analyzing transfers: {str(e)}")
        return Response(
            {"status": "error", "message": f"Analysis failed: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        ) 