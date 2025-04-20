#!/usr/bin/env python3
import os
import sys
import difflib
import argparse
from django.core.management.base import BaseCommand
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
# Import Django after setting environment
import django
django.setup()

# Import Django models after setup
from transactions.models import Transaction, Supplier

def calculate_similarity(text1, text2):
    """Calculates the similarity ratio between two strings."""
    if not text1 or not text2:
        return 0
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def get_unmatched_transactions():
    """Retrieves all transactions without a supplier."""
    return Transaction.objects.filter(
        supplier__isnull=True
    ).values('id', 'description')

def get_matched_transactions():
    """Retrieves all transactions with a supplier for reference."""
    return Transaction.objects.exclude(
        supplier__isnull=True
    ).values('id', 'description', 'supplier__name', 'supplier__id')

def find_best_matches(unmatched_transactions, reference_transactions):
    """Find the best supplier match for each unmatched transaction."""
    results = []
    
    for unmatched_tx in unmatched_transactions:
        best_match = {
            'transaction_id': unmatched_tx['id'],
            'description': unmatched_tx['description'],
            'best_match_supplier': None,
            'best_match_supplier_id': None,
            'best_match_tx_id': None,
            'best_match_description': None,
            'similarity_score': 0
        }
        
        for ref_tx in reference_transactions:
            similarity = calculate_similarity(unmatched_tx['description'], ref_tx['description'])
            
            if similarity > best_match['similarity_score']:
                best_match['similarity_score'] = similarity
                best_match['best_match_supplier'] = ref_tx['supplier__name']
                best_match['best_match_supplier_id'] = ref_tx['supplier__id']
                best_match['best_match_tx_id'] = ref_tx['id']
                best_match['best_match_description'] = ref_tx['description']
        
        results.append(best_match)
    
    return results

def print_results(results, limit=20):
    """Print the matching results in a readable format."""
    print(f"\nMatching Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Found {len(results)} unmatched transactions")
    print("-" * 80)
    
    # Sort by similarity score (highest first)
    sorted_results = sorted(results, key=lambda x: x['similarity_score'], reverse=True)
    
    # Show top matches first (limit if there are many)
    display_results = sorted_results[:limit] if len(sorted_results) > limit else sorted_results
    
    for result in display_results:
        print(f"Transaction ID: {result['transaction_id']}")
        print(f"  Description: '{result['description']}'")
        
        if result['best_match_supplier'] and result['similarity_score'] > 0:
            print(f"  Proposed Match: Supplier '{result['best_match_supplier']}' (ID: {result['best_match_supplier_id']})")
            print(f"  From Transaction: {result['best_match_tx_id']} - '{result['best_match_description']}'")
            print(f"  Similarity Score: {result['similarity_score']:.2f}")
        else:
            print("  No suitable match found.")
            
        print("-" * 80)
    
    if len(sorted_results) > limit:
        print(f"Showing top {limit} results of {len(sorted_results)} total matches.")

def apply_matches_to_database(results, similarity_threshold=0.7):
    """Apply the matches to the database if they meet the similarity threshold."""
    applied_count = 0
    skipped_count = 0
    
    for result in results:
        if result['similarity_score'] >= similarity_threshold and result['best_match_supplier_id']:
            # Get the transaction and supplier objects
            try:
                transaction = Transaction.objects.get(id=result['transaction_id'])
                supplier = Supplier.objects.get(id=result['best_match_supplier_id'])
                
                # Update the transaction with the matched supplier
                transaction.supplier = supplier
                
                # If raw_data contains matchType, update it
                if transaction.raw_data and isinstance(transaction.raw_data, dict):
                    transaction.raw_data['matchType'] = 'auto_matched'
                
                transaction.save()
                applied_count += 1
                print(f"Applied match for Transaction {transaction.id} to Supplier '{supplier.name}' (ID: {supplier.id})")
            
            except (Transaction.DoesNotExist, Supplier.DoesNotExist) as e:
                print(f"Error applying match: {e}")
                skipped_count += 1
        else:
            skipped_count += 1
    
    print(f"\nMatching complete: {applied_count} matches applied, {skipped_count} skipped")
    return applied_count, skipped_count

class Command(BaseCommand):
    help = 'Match transactions without suppliers based on description similarity.'

    def add_arguments(self, parser):
        parser.add_argument('-a', '--apply', action='store_true', 
                          help='Apply matches to the database without prompting')
        parser.add_argument('-t', '--threshold', type=float, default=0.7,
                          help='Similarity threshold for matching (default: 0.7)')
        parser.add_argument('-l', '--limit', type=int, default=0,
                          help='Limit processing to N transactions (default: 0 = all transactions)')
        parser.add_argument('-d', '--display', type=int, default=20,
                          help='Number of results to display (default: 20)')

    def handle(self, *args, **options):
        try:
            # Get transactions
            self.stdout.write("Fetching transactions from database...")
            unmatched_transactions = get_unmatched_transactions()
            reference_transactions = get_matched_transactions()
            
            unmatched_count = unmatched_transactions.count()
            reference_count = reference_transactions.count()
            
            self.stdout.write(f"Found {unmatched_count} transactions without suppliers")
            self.stdout.write(f"Found {reference_count} reference transactions with suppliers")
            
            if unmatched_count == 0:
                self.stdout.write("No unmatched transactions found. Nothing to process.")
                return
                
            if reference_count == 0:
                self.stdout.write("No reference transactions with suppliers found. Cannot perform matching.")
                return
            
            # Apply limit if specified in command line arguments
            if options['limit'] > 0 and unmatched_count > options['limit']:
                self.stdout.write(f"Processing only the first {options['limit']} of {unmatched_count} unmatched transactions.")
                unmatched_transactions = unmatched_transactions[:options['limit']]
            else:
                self.stdout.write(f"Processing all {unmatched_count} unmatched transactions.")
            
            # Find best matches
            self.stdout.write("Processing matches...")
            results = find_best_matches(unmatched_transactions, reference_transactions)
            
            # Print results
            print_results(results, options['display'])
            
            # Apply matches to database if --apply flag is set
            if options['apply']:
                self.stdout.write(f"\nApplying matches to database with similarity threshold ≥ {options['threshold']}...")
                apply_matches_to_database(results, options['threshold'])
            else:
                self.stdout.write("\nRun with --apply flag to update the database with these matches.")
                self.stdout.write(f"Note: Only matches with similarity score ≥ {options['threshold']} will be applied.")
            
        except Exception as e:
            self.stderr.write(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main() 