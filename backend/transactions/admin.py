"""
Admin interface for the transactions app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import (
    Transaction, Category, BankStatement, BankAccount, 
    Supplier, Account, LedgerPosting, CategorySupplierMap, 
    TransactionAccount, CloseGroup, CloseGroupPosting
)

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
    list_display = ('account_number', 'name', 'tripletex_id', 'account_type', 'is_active', 'closeGroup', 'transaction_count', 'created_at')
    search_fields = ('name', 'account_number', 'tripletex_id', 'closeGroup')
    list_filter = ('is_active', 'account_type', 'closeGroup')
    ordering = ('account_number', 'name')
    
    def transaction_count(self, obj):
        return obj.transactions.count()
    transaction_count.short_description = 'Transactions'

class TransactionAccountInline(admin.TabularInline):
    model = TransactionAccount
    extra = 0
    fields = ('account', 'amount', 'is_debit', 'posting_id', 'voucher_id', 'description')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('account',)
    can_delete = False
    show_change_link = True
    verbose_name = "Related Account"
    verbose_name_plural = "Related Accounts"

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
    list_display = ('formatted_date', 'description', 'formatted_amount', 'category', 'bank_account', 'supplier', 'ledger_account', 'related_account_count', 'is_internal_transfer')
    list_filter = ('date', 'category', 'bank_account', 'supplier', 'ledger_account', 'is_internal_transfer', 'is_wage_transfer', 'is_tax_transfer', 'is_forbidden', 'should_process')
    search_fields = ('description', 'tripletex_id', 'legacy_bank_account_id', 'account_id')
    ordering = ('-date', 'description')
    raw_id_fields = ('category', 'bank_account', 'supplier', 'ledger_account')
    date_hierarchy = 'date'
    readonly_fields = ('imported_at', 'updated_at', 'related_account_count')
    inlines = [TransactionAccountInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('description', 'amount', 'date', 'tripletex_id', 'category', 'bank_account')
        }),
        ('Tripletex Information', {
            'fields': ('supplier', 'ledger_account', 'related_account_count')
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
    
    def related_account_count(self, obj):
        return obj.transaction_accounts.count()
    related_account_count.short_description = 'Related Accounts'
    
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

@admin.register(TransactionAccount)
class TransactionAccountAdmin(admin.ModelAdmin):
    list_display = ('transaction_info', 'account_info', 'formatted_amount', 'is_debit', 'posting_id', 'account_close_group', 'voucher_id', 'created_at')
    list_filter = ('is_debit', 'created_at', 'account__closeGroup')
    search_fields = ('transaction__description', 'account__name', 'account__account_number', 'posting_id', 'voucher_id', 'description', 'account__closeGroup')
    raw_id_fields = ('transaction', 'account')
    readonly_fields = ('created_at', 'updated_at', 'account_close_group')
    
    fieldsets = (
        ('Relationship', {
            'fields': ('transaction', 'account', 'account_close_group')
        }),
        ('Posting Information', {
            'fields': ('amount', 'is_debit', 'posting_id', 'voucher_id', 'description')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def transaction_info(self, obj):
        return f"{obj.transaction.date} - {obj.transaction.description[:50]}"
    transaction_info.short_description = 'Transaction'
    
    def account_info(self, obj):
        if obj.account:
            if obj.account.account_number and obj.account.name:
                return f"{obj.account.account_number} - {obj.account.name}"
            elif obj.account.account_number:
                return obj.account.account_number
            else:
                return obj.account.name
        return "No account"
    account_info.short_description = 'Account'
    
    def account_close_group(self, obj):
        if obj.account and obj.account.closeGroup:
            return obj.account.closeGroup
        return "-"
    account_close_group.short_description = 'Close Group'
    account_close_group.admin_order_field = 'account__closeGroup'
    
    def formatted_amount(self, obj):
        if obj.amount is None:
            return '-'
        color = 'green' if obj.amount >= 0 else 'red'
        return format_html('<span style="color: {};">{}</span>', color, f'{obj.amount:.2f}')
    formatted_amount.short_description = 'Amount'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('transaction', 'account')

@admin.register(LedgerPosting)
class LedgerPostingAdmin(admin.ModelAdmin):
    list_display = ('posting_id', 'formatted_date', 'description', 'formatted_amount', 'supplier', 'account', 'closeGroup', 'account_close_group', 'voucher_number', 'voucher_type')
    list_filter = ('date', 'supplier', 'account', 'voucher_type', 'account__closeGroup', 'closeGroup')
    search_fields = ('posting_id', 'description', 'voucher_number', 'account__closeGroup', 'closeGroup')
    ordering = ('-date', '-posting_id')
    raw_id_fields = ('supplier', 'account')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at', 'posting_id', 'account_close_group')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('posting_id', 'date', 'description', 'amount')
        }),
        ('Relationships', {
            'fields': ('supplier', 'account', 'account_close_group', 'closeGroup')
        }),
        ('Voucher Information', {
            'fields': ('voucher_id', 'voucher_number', 'voucher_type')
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
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
    
    def account_close_group(self, obj):
        if obj.account and obj.account.closeGroup:
            return obj.account.closeGroup
        return "-"
    account_close_group.short_description = 'Close Group'
    account_close_group.admin_order_field = 'account__closeGroup'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('supplier', 'account')
    
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

@admin.register(CategorySupplierMap)
class CategorySupplierMapAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'category', 'created_at', 'updated_at')
    list_filter = ('category', 'created_at')
    search_fields = ('supplier__name', 'category__name')
    raw_id_fields = ('supplier', 'category')
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('supplier', 'category')

class CloseGroupPostingInline(admin.TabularInline):
    model = CloseGroupPosting
    extra = 0
    fields = ('posting', 'created_at')
    readonly_fields = ('created_at',)
    raw_id_fields = ('posting',)
    verbose_name = "Related Posting"
    verbose_name_plural = "Related Postings"

@admin.register(CloseGroup)
class CloseGroupAdmin(admin.ModelAdmin):
    list_display = ('tripletex_id', 'name', 'description', 'postings_count', 'created_at', 'updated_at')
    search_fields = ('tripletex_id', 'name', 'description')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CloseGroupPostingInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tripletex_id', 'name', 'description', 'postings_count')
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('postings')

@admin.register(CloseGroupPosting)
class CloseGroupPostingAdmin(admin.ModelAdmin):
    list_display = ('close_group', 'posting', 'created_at')
    list_filter = ('created_at', 'close_group')
    search_fields = ('close_group__name', 'close_group__tripletex_id', 'posting__posting_id', 'posting__description')
    raw_id_fields = ('close_group', 'posting')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Relationship', {
            'fields': ('close_group', 'posting')
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('close_group', 'posting')
