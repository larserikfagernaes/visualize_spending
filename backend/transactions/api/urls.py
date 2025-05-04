from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TransactionViewSet,
    CategoryViewSet,
    BankAccountViewSet,
    BankStatementViewSet,
    import_from_tripletex,
    analyze_transfers,
    clear_cache,
    SupplierViewSet
)

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'bank-accounts', BankAccountViewSet)
router.register(r'bank-statements', BankStatementViewSet)
router.register(r'suppliers', SupplierViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('import-tripletex/', import_from_tripletex, name='import-tripletex'),
    path('analyze-transfers/', analyze_transfers, name='analyze-transfers'),
    path('clear-cache/', clear_cache, name='clear-cache'),
] 