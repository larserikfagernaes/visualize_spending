from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'transactions', views.TransactionViewSet)
router.register(r'bank-statements', views.BankStatementViewSet)
router.register(r'categories', views.CategoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('import/', views.import_transactions, name='import-transactions'),
    path('import-tripletex/', views.import_from_tripletex, name='import-from-tripletex'),
    path('categorize/<int:transaction_id>/', views.categorize_transaction, name='categorize-transaction'),
] 