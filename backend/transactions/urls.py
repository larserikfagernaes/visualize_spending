"""
URL patterns for the transactions app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api.views import (
    TransactionViewSet,
    CategoryViewSet,
    BankStatementViewSet,
    BankAccountViewSet,
    import_from_tripletex,
    analyze_transfers
)
from .views import categorize_transaction

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'transactions', TransactionViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'bank-statements', BankStatementViewSet)
router.register(r'bank-accounts', BankAccountViewSet)

# The API URLs are now determined automatically by the router
urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
    
    # Import and analysis endpoints
    path('import-tripletex/', import_from_tripletex, name='import-from-tripletex'),
    path('analyze-transfers/', analyze_transfers, name='analyze-transfers'),
    
    # Category endpoints
    path('categorize/<int:transaction_id>/', categorize_transaction, name='categorize-transaction'),
] 