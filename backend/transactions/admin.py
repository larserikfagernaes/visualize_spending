from django.contrib import admin
from .models import BankStatement, Transaction, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')

@admin.register(BankStatement)
class BankStatementAdmin(admin.ModelAdmin):
    list_display = ('date', 'description', 'amount', 'category', 'source_file', 'created_at')
    list_filter = ('date', 'category', 'source_file')
    search_fields = ('description',)
    date_hierarchy = 'date'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'description', 'amount', 'bank_account_id', 'is_internal_transfer', 
                    'is_wage_transfer', 'is_tax_transfer', 'should_process', 'category')
    list_filter = ('date', 'bank_account_id', 'is_internal_transfer', 'is_wage_transfer', 
                  'is_tax_transfer', 'is_forbidden', 'should_process', 'category')
    search_fields = ('description', 'tripletex_id')
    date_hierarchy = 'date'
    list_per_page = 50
