"""
Models for the transactions application.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class TimeStampedModel(models.Model):
    """
    Abstract base model that provides created_at and updated_at fields.
    """
    created_at = models.DateTimeField(_("Created at"), default=timezone.now)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        abstract = True

class Category(TimeStampedModel):
    """
    Category model for classifying transactions.
    Categories help organize and analyze spending patterns.
    """
    name = models.CharField(_("Name"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True, null=True)
    
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']
    
    def __str__(self):
        return self.name

class BankAccount(TimeStampedModel):
    """
    Model to store information about bank accounts.
    Each transaction is associated with a bank account.
    """
    name = models.CharField(_("Account name"), max_length=255)
    account_number = models.CharField(_("Account number"), max_length=50, blank=True, null=True)
    bank_name = models.CharField(_("Bank name"), max_length=100, blank=True, null=True)
    account_type = models.CharField(_("Account type"), max_length=50, blank=True, null=True)
    is_active = models.BooleanField(_("Is active"), default=True)
    
    class Meta:
        verbose_name = _("Bank account")
        verbose_name_plural = _("Bank accounts")
        ordering = ['name']
    
    def __str__(self):
        return self.name

class BankStatement(TimeStampedModel):
    """
    Model to store bank statement information.
    Each statement represents a transaction from a bank statement file.
    """
    description = models.CharField(_("Description"), max_length=255)
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    date = models.DateField(_("Date"))
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='bank_statements',
        verbose_name=_("Category")
    )
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='statements',
        verbose_name=_("Bank account")
    )
    source_file = models.CharField(_("Source file"), max_length=255, blank=True, null=True)
    
    class Meta:
        verbose_name = _("Bank statement")
        verbose_name_plural = _("Bank statements")
        ordering = ['-date', 'description']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['category']),
            models.Index(fields=['bank_account']),
        ]
    
    def __str__(self):
        return f"{self.date} - {self.description} ({self.amount})"

class Supplier(TimeStampedModel):
    """
    Model to store information about suppliers from Tripletex.
    Suppliers are linked to transactions when they are the source or recipient of payments.
    """
    tripletex_id = models.CharField(_("Tripletex ID"), max_length=255, unique=True)
    name = models.CharField(_("Name"), max_length=255, blank=True, null=True)
    organization_number = models.CharField(_("Organization number"), max_length=50, blank=True, null=True)
    email = models.EmailField(_("Email"), blank=True, null=True)
    phone_number = models.CharField(_("Phone number"), max_length=50, blank=True, null=True)
    address = models.TextField(_("Address"), blank=True, null=True)
    url = models.URLField(_("Tripletex URL"), blank=True, null=True)
    
    class Meta:
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ['name']
        indexes = [
            models.Index(fields=['tripletex_id']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name or f"Supplier {self.tripletex_id}"

class Account(TimeStampedModel):
    """
    Model to store ledger account information from Tripletex.
    Accounts represent specific ledger accounts in the accounting system.
    """
    tripletex_id = models.CharField(_("Tripletex ID"), max_length=255, unique=True)
    account_number = models.CharField(_("Account number"), max_length=50, blank=True, null=True)
    name = models.CharField(_("Name"), max_length=255, blank=True, null=True)
    description = models.TextField(_("Description"), blank=True, null=True)
    account_type = models.CharField(_("Account type"), max_length=100, blank=True, null=True)
    url = models.URLField(_("Tripletex URL"), blank=True, null=True)
    is_active = models.BooleanField(_("Is active"), default=True)
    
    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        ordering = ['account_number', 'name']
        indexes = [
            models.Index(fields=['tripletex_id']),
            models.Index(fields=['account_number']),
        ]
    
    def __str__(self):
        if self.account_number and self.name:
            return f"{self.account_number} - {self.name}"
        elif self.account_number:
            return self.account_number
        elif self.name:
            return self.name
        else:
            return f"Account {self.tripletex_id}"

class Transaction(TimeStampedModel):
    """
    Model to store financial transactions.
    Transactions can be imported from external sources or created manually.
    """
    # Core transaction details
    tripletex_id = models.CharField(_("Tripletex ID"), max_length=255, unique=True, null=True, blank=True)
    description = models.CharField(_("Description"), max_length=255)
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    date = models.DateField(_("Date"))
    
    # Bank and account information
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name=_("Bank account")
    )
    legacy_bank_account_id = models.CharField(_("Legacy bank account ID"), max_length=255, blank=True, null=True)
    account_id = models.CharField(_("Account ID"), max_length=255, blank=True, null=True)
    
    # New relationships to Supplier and Account
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name=_("Supplier")
    )
    ledger_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name=_("Ledger Account")
    )
    
    # Transaction classification
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions',
        verbose_name=_("Category")
    )
    
    # Transaction flags
    is_internal_transfer = models.BooleanField(_("Is internal transfer"), default=False)
    is_wage_transfer = models.BooleanField(_("Is wage transfer"), default=False)
    is_tax_transfer = models.BooleanField(_("Is tax transfer"), default=False)
    is_forbidden = models.BooleanField(_("Is forbidden"), default=False)
    should_process = models.BooleanField(_("Should process"), default=True)
    
    # Raw data
    raw_data = models.JSONField(_("Raw data"), null=True, blank=True, 
                              help_text=_("Complete transaction data from the source system"))
    
    # Import metadata
    imported_at = models.DateTimeField(_("Imported at"), default=timezone.now)
    
    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        ordering = ['-date', 'description']
        indexes = [
            models.Index(fields=['tripletex_id']),
            models.Index(fields=['date']),
            models.Index(fields=['legacy_bank_account_id']),
            models.Index(fields=['account_id']),
            models.Index(fields=['should_process']),
            models.Index(fields=['is_internal_transfer']),
            models.Index(fields=['is_wage_transfer']),
            models.Index(fields=['is_tax_transfer']),
            models.Index(fields=['category']),
            models.Index(fields=['supplier']),
            models.Index(fields=['ledger_account']),
        ]
    
    def __str__(self):
        return f"{self.date} - {self.description} ({self.amount})"
