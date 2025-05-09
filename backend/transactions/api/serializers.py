"""
Serializers for the transactions API.
"""
from rest_framework import serializers
from ..models import Transaction, Category, BankStatement, BankAccount, Supplier

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model.
    """
    transaction_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'budget', 'transaction_count', 'created_at', 'updated_at']
    
    def get_transaction_count(self, obj):
        """Get the number of transactions associated with this category."""
        return obj.transactions.count()

class BankAccountSerializer(serializers.ModelSerializer):
    """
    Serializer for the BankAccount model.
    """
    transaction_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BankAccount
        fields = ['id', 'name', 'account_number', 'bank_name', 'account_type', 
                 'is_active', 'transaction_count', 'created_at', 'updated_at']
    
    def get_transaction_count(self, obj):
        """Get the number of transactions associated with this bank account."""
        return obj.transactions.count()

class BankStatementSerializer(serializers.ModelSerializer):
    """
    Serializer for the BankStatement model.
    """
    category_name = serializers.SerializerMethodField()
    bank_account_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BankStatement
        fields = ['id', 'description', 'amount', 'date', 'category', 'category_name',
                 'bank_account', 'bank_account_name', 'source_file', 'created_at', 'updated_at']
    
    def get_category_name(self, obj):
        """Get the name of the category associated with this bank statement."""
        if obj.category:
            return obj.category.name
        return None
    
    def get_bank_account_name(self, obj):
        """Get the name of the bank account associated with this bank statement."""
        if obj.bank_account:
            return obj.bank_account.name
        return None

class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for the Transaction model.
    """
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    bank_account_name = serializers.CharField(source='bank_account.name', read_only=True, allow_null=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, allow_null=True)
    related_accounts = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = ['id', 'tripletex_id', 'description', 'amount', 'date',
                 'bank_account', 'bank_account_name', 'bank_account_id', 'account_id',
                 'is_internal_transfer', 'is_wage_transfer', 'is_tax_transfer',
                 'is_forbidden', 'should_process',
                 'category', 'category_name', 'supplier', 'supplier_name', 
                 'related_accounts', 'imported_at', 'updated_at']
    
    def get_related_accounts(self, obj):
        """Get the related accounts through the M2M relationship."""
        # The transaction_accounts are already prefetched with their accounts
        return [
            {
                'id': ta.account.id,
                'name': ta.account.name,
                'account_number': ta.account.account_number,
                'amount': ta.amount
            }
            for ta in obj.transaction_accounts.all()
            if ta.account
        ]

class TransactionDetailSerializer(TransactionSerializer):
    """
    Detailed serializer for the Transaction model.
    Includes raw data for detailed view.
    """
    class Meta(TransactionSerializer.Meta):
        fields = TransactionSerializer.Meta.fields + ['raw_data']

class TransactionCategoryUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating the category of a transaction.
    """
    category_id = serializers.IntegerField(allow_null=True)
    
    def validate_category_id(self, value):
        """Validate that the category exists if provided."""
        if value is not None:
            try:
                Category.objects.get(id=value)
            except Category.DoesNotExist:
                raise serializers.ValidationError("Category does not exist")
        return value

class TransactionSummarySerializer(serializers.Serializer):
    """
    Serializer for transaction summary data.
    """
    total_transactions = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    categories = serializers.DictField(child=serializers.DictField())
    bank_accounts = serializers.DictField(child=serializers.DictField())
    related_accounts = serializers.DictField(child=serializers.DictField())

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'tripletex_id', 'name', 'organization_number', 'email', 'phone_number', 'address', 'url', 'created_at', 'updated_at'] 