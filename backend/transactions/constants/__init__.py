"""
Constants for the transactions application.
Centralizes all constant values used throughout the app.
"""

# Transaction types
TRANSACTION_TYPE_INTERNAL = 'internal'
TRANSACTION_TYPE_WAGE = 'wage'
TRANSACTION_TYPE_TAX = 'tax'
TRANSACTION_TYPE_REGULAR = 'regular'

# Transaction statuses
STATUS_PENDING = 'pending'
STATUS_PROCESSED = 'processed'
STATUS_IGNORED = 'ignored'

# API endpoints
TRIPLETEX_API_BASE_URL = 'https://tripletex.no/v2'
TRIPLETEX_API_BANK_STATEMENT_ENDPOINT = '/bank/statement'
TRIPLETEX_API_TRANSACTION_ENDPOINT = '/bank/transaction'

# Cache settings
CACHE_EXPIRY_DAYS = 7
DEFAULT_CACHE_DIR = 'cache'

# Transfer detection
INTERNAL_TRANSFER_KEYWORDS = [
    'intern overføring',
    'overført fra: aviant',
    'oppgave fra: aviant',
    'overføring mellom egne kontoer',
    'overføring til egen konto',
    'overføring fra egen konto',
    'oppgave kontoreguleringaviant as'
]

# Category mapping keywords
CATEGORY_KEYWORDS = {
    'Food & Dining': ['restaurant', 'café', 'bakery', 'grocery', 'food', 'takeaway'],
    'Transportation': ['taxi', 'uber', 'train', 'bus', 'transport', 'travel', 'fuel', 'parking'],
    'Shopping': ['shop', 'store', 'retail', 'purchase'],
    'Entertainment': ['cinema', 'theater', 'concert', 'event', 'ticket'],
    'Utilities': ['electricity', 'water', 'gas', 'internet', 'phone', 'mobile', 'utility'],
}
