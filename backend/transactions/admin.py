"""
Admin interface for the transactions app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Transaction, Category, BankStatement, BankAccount, Supplier, Account

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'transaction_count', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def transaction_count(self, obj):
        return obj.transactions.count()
    transaction_count.short_description = 'Transactions'

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_number', 'bank_name', 'account_type', 'is_active', 'transaction_count', 'created_at')
    search_fields = ('name', 'account_number', 'bank_name')
    list_filter = ('is_active', 'account_type')
    ordering = ('name',)
    
    def transaction_count(self, obj):
        return obj.transactions.count()
    transaction_count.short_description = 'Transactions'

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'tripletex_id', 'organization_number', 'email', 'phone_number', 'transaction_count', 'created_at')
    search_fields = ('name', 'tripletex_id', 'organization_number', 'email')
    list_filter = ('created_at',)
    ordering = ('name',)
    
    def transaction_count(self, obj):
        return obj.transactions.count()
    transaction_count.short_description = 'Transactions'

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'name', 'tripletex_id', 'account_type', 'is_active', 'transaction_count', 'created_at')
    search_fields = ('name', 'account_number', 'tripletex_id')
    list_filter = ('is_active', 'account_type')
    ordering = ('account_number', 'name')
    
    def transaction_count(self, obj):
        return obj.transactions.count()
    transaction_count.short_description = 'Transactions'

@admin.register(BankStatement)
class BankStatementAdmin(admin.ModelAdmin):
    list_display = ('formatted_date', 'description', 'formatted_amount', 'category', 'bank_account', 'source_file')
    list_filter = ('date', 'category', 'bank_account')
    search_fields = ('description', 'source_file')
    ordering = ('-date', 'description')
    raw_id_fields = ('category', 'bank_account')
    date_hierarchy = 'date'
    
    def formatted_date(self, obj):
        return obj.date.strftime('%Y-%m-%d')
    formatted_date.short_description = 'Date'
    
    def formatted_amount(self, obj):
        color = 'green' if obj.amount >= 0 else 'red'
        return format_html('<span style="color: {};">{}</span>', color, f'{obj.amount:.2f}')
    formatted_amount.short_description = 'Amount'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('formatted_date', 'description', 'formatted_amount', 'category', 'bank_account', 'supplier', 'ledger_account', 'is_internal_transfer')
    list_filter = ('date', 'category', 'bank_account', 'supplier', 'ledger_account', 'is_internal_transfer', 'is_wage_transfer', 'is_tax_transfer', 'is_forbidden', 'should_process')
    search_fields = ('description', 'tripletex_id', 'legacy_bank_account_id', 'account_id')
    ordering = ('-date', 'description')
    raw_id_fields = ('category', 'bank_account', 'supplier', 'ledger_account')
    date_hierarchy = 'date'
    readonly_fields = ('imported_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('description', 'amount', 'date', 'tripletex_id', 'category', 'bank_account')
        }),
        ('Tripletex Information', {
            'fields': ('supplier', 'ledger_account')
        }),
        ('Classification', {
            'fields': ('is_internal_transfer', 'is_wage_transfer', 'is_tax_transfer', 'is_forbidden', 'should_process')
        }),
        ('Legacy Fields', {
            'classes': ('collapse',),
            'fields': ('legacy_bank_account_id', 'account_id')
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('imported_at', 'updated_at')
        }),
        ('Raw Data', {
            'classes': ('collapse',),
            'fields': ('raw_data',)
        }),
    )
    
    def formatted_date(self, obj):
        return obj.date.strftime('%Y-%m-%d')
    formatted_date.short_description = 'Date'
    
    def formatted_amount(self, obj):
        color = 'green' if obj.amount >= 0 else 'red'
        return format_html('<span style="color: {};">{}</span>', color, f'{obj.amount:.2f}')
    formatted_amount.short_description = 'Amount'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('category', 'bank_account', 'supplier', 'ledger_account')
    
    def changelist_view(self, request, extra_context=None):
        """
        Add summary data to changelist view
        """
        response = super().changelist_view(request, extra_context)
        
        # Only execute if we're showing the changelist view
        if hasattr(response, 'context_data'):
            # Get queryset from response
            queryset = response.context_data['cl'].queryset
            
            # Calculate totals
            total_amount = queryset.aggregate(total=Sum('amount'))['total'] or 0
            count = queryset.count()
            
            # Add extra context
            response.context_data.update({
                'summary_data': {
                    'total_amount': total_amount,
                    'count': count,
                    'average': total_amount / count if count > 0 else 0
                }
            })
        
        return response
