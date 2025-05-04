#!/usr/bin/env python3
import os
import sys
import logging
from django.core.management.base import BaseCommand
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Set up environment
load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')

# Import Django after setting environment
import django
django.setup()

# Import models after Django setup
from transactions.models import Transaction, Supplier

# Import methods from comparison script
try:
    from transactions.management.commands.compare_supplier_matching_methods import (
        method1_tfidf,
        method2_levenshtein,
        method3_tfidf_fuzzy_hybrid,
        method4_ngram,
        apply_best_method_to_database,
        SIMILARITY_THRESHOLD
    )
except ImportError:
    logger.error("Could not import methods from compare_supplier_matching_methods.py")
    sys.exit(1)


class Command(BaseCommand):
    help = 'Automatically match transactions without suppliers using the best available method'

    def add_arguments(self, parser):
        parser.add_argument(
            '--method',
            type=int,
            default=3,  # Default to hybrid method
            choices=[1, 2, 3, 4],
            help='Method to use (1: Enhanced TF-IDF, 2: Levenshtein, 3: TF-IDF + Fuzzy Hybrid, 4: N-gram). Default is 3 (Hybrid)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of transactions to process'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=SIMILARITY_THRESHOLD,
            help=f'Similarity threshold (0.0-1.0). Default is {SIMILARITY_THRESHOLD}'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show matches but do not update the database'
        )

    def handle(self, *args, **options):
        method_id = options['method']
        limit = options['limit']
        threshold = options['threshold']
        dry_run = options['dry_run']
        
        # Get all transactions without suppliers
        query = Transaction.objects.filter(
            supplier__isnull=True,
            is_internal_transfer=False,  # Skip internal transfers
            is_wage_transfer=False,      # Skip wage transfers
            is_tax_transfer=False,       # Skip tax transfers
            is_forbidden=False,          # Skip forbidden transactions
        )
        
        if limit:
            query = query.order_by('-date')[:limit]
            
        unmatched_txs = list(query.values('id', 'description'))
        
        if not unmatched_txs:
            self.stdout.write("No unmatched transactions found.")
            return
            
        self.stdout.write(f"Found {len(unmatched_txs)} transactions without suppliers")
        
        # Get all transactions with suppliers for reference
        matched_txs = Transaction.objects.filter(
            supplier__isnull=False
        ).select_related('supplier').values(
            'id', 'description', 'supplier__name', 'supplier__id'
        )
        
        self.stdout.write(f"Using {len(matched_txs)} transactions with suppliers as reference")
        
        # Select method
        method_name = ""
        if method_id == 1:
            method_name = "Method 1: Enhanced TF-IDF + Cosine Similarity"
            method_func = method1_tfidf
        elif method_id == 2:
            method_name = "Method 2: Fuzzy Matching / String Similarity" 
            method_func = method2_levenshtein
        elif method_id == 3:
            method_name = "Method 3: TF-IDF + Fuzzy Matching Hybrid"
            method_func = method3_tfidf_fuzzy_hybrid
        elif method_id == 4:
            method_name = "Method 4: N-gram Analysis"
            method_func = method4_ngram
        
        self.stdout.write(f"Using {method_name}")
        
        # Run the selected method
        try:
            results = method_func(matched_txs, unmatched_txs)
            
            if 'error' in results:
                self.stderr.write(f"Error: {results['error']}")
                return
                
            # Process and update database
            matched_count = 0
            skipped_count = 0
            
            for result in results['results']:
                tx_id = result['transaction_id']
                supplier_name = result['best_match_supplier_name']
                confidence = result['confidence_level']
                
                # Get the transaction description
                tx_desc = next((tx['description'] for tx in unmatched_txs if tx['id'] == tx_id), "Unknown")
                
                # Report match
                status = "MATCH" if confidence >= threshold * 100 else "LOW CONFIDENCE"
                self.stdout.write(f"[{status}] Transaction {tx_id}: {tx_desc[:50]}...")
                self.stdout.write(f"         → {supplier_name} (Confidence: {confidence}%)")
                
                if confidence >= threshold * 100:
                    if not dry_run:
                        try:
                            # Update the database
                            apply_successful = apply_best_method_to_database(
                                {'results': [result]},  # Wrap in expected format
                                method_name,
                                threshold
                            )
                            
                            if apply_successful:
                                matched_count += 1
                            else:
                                skipped_count += 1
                                
                        except Exception as e:
                            self.stderr.write(f"Error updating transaction {tx_id}: {e}")
                            skipped_count += 1
                else:
                    skipped_count += 1
            
            # Print summary
            if dry_run:
                self.stdout.write(f"\nDRY RUN - would have updated {matched_count} transactions")
            else:
                self.stdout.write(f"\nUpdated {matched_count} transactions with suppliers")
                
            self.stdout.write(f"Skipped {skipped_count} transactions (low confidence or errors)")
                
        except Exception as e:
            self.stderr.write(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    pass 