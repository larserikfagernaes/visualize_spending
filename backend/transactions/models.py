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

class CloseGroup(TimeStampedModel):
    """
    Model to store information about closeGroups from Tripletex.
    CloseGroups connect postings across different vouchers that are related.
    """
    tripletex_id = models.CharField(_("Tripletex ID"), max_length=255, unique=True)
    name = models.CharField(_("Name"), max_length=255, blank=True, null=True)
    description = models.TextField(_("Description"), blank=True, null=True)
    postings_count = models.IntegerField(_("Postings count"), default=0)
    
    # Add many-to-many relationship to LedgerPosting
    postings = models.ManyToManyField(
        'LedgerPosting',
        through='CloseGroupPosting',
        related_name='close_groups',
        verbose_name=_("Related Postings")
    )
    
    class Meta:
        verbose_name = _("Close Group")
        verbose_name_plural = _("Close Groups")
        ordering = ['tripletex_id']
        indexes = [
            models.Index(fields=['tripletex_id']),
        ]
    
    def __str__(self):
        return self.name or f"CloseGroup {self.tripletex_id}"

class CloseGroupPosting(TimeStampedModel):
    """
    Intermediate model connecting CloseGroups to LedgerPostings.
    This enables a many-to-many relationship between close groups and postings.
    """
    close_group = models.ForeignKey(
        CloseGroup,
        on_delete=models.CASCADE,
        related_name='closegroup_postings',
        verbose_name=_("Close Group")
    )
    posting = models.ForeignKey(
        'LedgerPosting',
        on_delete=models.CASCADE,
        related_name='closegroup_postings',
        verbose_name=_("Posting")
    )
    
    class Meta:
        verbose_name = _("Close Group Posting")
        verbose_name_plural = _("Close Group Postings")
        unique_together = ('close_group', 'posting')
        indexes = [
            models.Index(fields=['close_group']),
            models.Index(fields=['posting']),
        ]
    
    def __str__(self):
        return f"{self.close_group} - {self.posting}"

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
    closeGroup = models.CharField(_("Close Group ID"), max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        ordering = ['account_number', 'name']
        indexes = [
            models.Index(fields=['tripletex_id']),
            models.Index(fields=['account_number']),
            models.Index(fields=['closeGroup']),
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
    
    # Multiple accounts through TransactionAccount relationship
    accounts = models.ManyToManyField(
        Account,
        through='TransactionAccount',
        related_name='related_transactions',
        verbose_name=_("Related Accounts")
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

class TransactionAccount(TimeStampedModel):
    """
    Model to represent the relationship between transactions and accounts.
    A transaction can be linked to multiple accounts, and this model stores 
    the details of each account posting within the transaction.
    """
    transaction = models.ForeignKey(
        Transaction, 
        on_delete=models.CASCADE,
        related_name='transaction_accounts',
        verbose_name=_("Transaction")
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='account_transactions',
        verbose_name=_("Account")
    )
    amount = models.DecimalField(_("Amount"), max_digits=15, decimal_places=2, null=True, blank=True)
    is_debit = models.BooleanField(_("Is Debit"), default=True, help_text=_("True if this is a debit posting, False for credit"))
    posting_id = models.CharField(_("Posting ID"), max_length=255, blank=True, null=True)
    voucher_id = models.CharField(_("Voucher ID"), max_length=255, blank=True, null=True)
    description = models.TextField(_("Description"), blank=True, null=True)
    
    class Meta:
        verbose_name = _("Transaction Account")
        verbose_name_plural = _("Transaction Accounts")
        unique_together = ('transaction', 'account', 'posting_id')
        indexes = [
            models.Index(fields=['transaction']),
            models.Index(fields=['account']),
            models.Index(fields=['posting_id']),
            models.Index(fields=['voucher_id']),
        ]
    
    def __str__(self):
        return f"{self.transaction} - {self.account} ({self.amount})"

class LedgerPosting(TimeStampedModel):
    """
    Model to store ledger postings from Tripletex.
    Represents individual entries in the accounting ledger.
    """
    posting_id = models.IntegerField(_("Tripletex Posting ID"), unique=True, help_text=_("The unique ID from Tripletex for this posting."))
    date = models.DateField(_("Date"))
    description = models.TextField(_("Description"), blank=True, null=True)
    amount = models.DecimalField(_("Amount"), max_digits=15, decimal_places=2)
    # The closeGroup field is now replaced with the ManyToMany relationship defined in CloseGroup model
    # This field is kept for backward compatibility during migration
    closeGroup = models.CharField(_("Close Group ID"), max_length=100, blank=True, null=True)

    # Relationships
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_postings',
        verbose_name=_("Supplier")
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_postings',
        verbose_name=_("Account")
    )

    # Voucher details (extracted from the voucher object in API response)
    voucher_id = models.IntegerField(_("Tripletex Voucher ID"), null=True, blank=True, db_index=True)
    voucher_number = models.CharField(_("Voucher Number"), max_length=100, null=True, blank=True)
    voucher_type = models.CharField(_("Voucher Type"), max_length=100, null=True, blank=True)

    # Raw data for reference
    raw_data = models.JSONField(_("Raw data"), null=True, blank=True,
                              help_text=_("Complete posting data from the Tripletex API"))

    class Meta:
        verbose_name = _("Ledger Posting")
        verbose_name_plural = _("Ledger Postings")
        ordering = ['-date', '-posting_id']
        indexes = [
            # posting_id is already indexed due to unique=True
            models.Index(fields=['date']),
            models.Index(fields=['supplier']),
            models.Index(fields=['account']),
            models.Index(fields=['closeGroup']),
            # voucher_id is indexed via db_index=True
        ]

    def __str__(self):
        return f"Posting {self.posting_id} ({self.date}): {self.description or 'No description'} - {self.amount}"

class CategorySupplierMap(TimeStampedModel):
    """
    Model to map suppliers to categories.
    This helps automatically categorize transactions based on their supplier.
    """
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='category_maps',
        verbose_name=_("Supplier")
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='supplier_maps',
        verbose_name=_("Category")
    )
    
    class Meta:
        verbose_name = _("Category-Supplier Mapping")
        verbose_name_plural = _("Category-Supplier Mappings")
        unique_together = ['supplier', 'category']
        
    def __str__(self):
        return f"{self.supplier.name} -> {self.category.name}"
