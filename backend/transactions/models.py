from django.db import models

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class BankStatement(models.Model):
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='bank_statements')
    source_file = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} - {self.description} ({self.amount})"

class Transaction(models.Model):
    # Tripletex transaction details
    tripletex_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    
    # Processed data
    bank_account_id = models.CharField(max_length=255, blank=True, null=True)
    account_id = models.CharField(max_length=255, blank=True, null=True)
    is_internal_transfer = models.BooleanField(default=False)
    is_wage_transfer = models.BooleanField(default=False)
    is_tax_transfer = models.BooleanField(default=False)
    is_forbidden = models.BooleanField(default=False)
    should_process = models.BooleanField(default=True)
    
    # Relations and metadata
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} - {self.description} ({self.amount})"
    
    class Meta:
        indexes = [
            models.Index(fields=['tripletex_id']),
            models.Index(fields=['date']),
            models.Index(fields=['bank_account_id']),
            models.Index(fields=['account_id']),
            models.Index(fields=['should_process']),
        ]
