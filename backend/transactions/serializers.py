from rest_framework import serializers
from .models import BankStatement, Transaction, Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']

class BankStatementSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = BankStatement
        fields = ['id', 'description', 'amount', 'date', 'category', 'category_name', 'source_file', 'created_at', 'updated_at']

    def get_category_name(self, obj):
        if obj.category:
            return obj.category.name
        return None

class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = ['id', 'tripletex_id', 'description', 'amount', 'date', 
                 'bank_account_id', 'account_id', 'is_internal_transfer', 'is_wage_transfer', 
                 'is_tax_transfer', 'is_forbidden', 'should_process',
                 'category', 'category_name', 'imported_at', 'updated_at']

    def get_category_name(self, obj):
        if obj.category:
            return obj.category.name
        return None

class TransactionSummarySerializer(serializers.Serializer):
    total_transactions = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    categories = serializers.DictField(child=serializers.DictField())
    bank_accounts = serializers.DictField(child=serializers.DictField()) 