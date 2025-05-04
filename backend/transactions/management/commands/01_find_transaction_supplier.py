#!/usr/bin/env python3
import os
import sys
import difflib
import argparse
from django.core.management.base import BaseCommand
from datetime import datetime
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
# Import Django after setting environment
import django
django.setup()

# Import Django models after setup
from transactions.models import Transaction, Supplier, Category, CategorySupplierMap

# Import scikit-learn for n-gram matching
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    print("Required package scikit-learn not installed. Please run: pip install scikit-learn")
    sys.exit(1)

def preprocess_description(text):
    """
    Preprocess description text:
    1. Convert to lowercase
    2. Replace series of digits with spaces
    3. Remove excess whitespace
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace consecutive digits with a single space
    text = re.sub(r'\d+', ' ', text)
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Trim whitespace
    return text.strip()

def calculate_similarity(text1, text2):
    """Calculates the similarity ratio between two strings."""
    if not text1 or not text2:
        return 0
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def get_unmatched_transactions():
    """Retrieves all transactions without a supplier."""
    return Transaction.objects.filter(
        supplier__isnull=True
    ).order_by('-date', '-id').values('id', 'description', 'raw_data')

def get_matched_transactions():
    """Retrieves all transactions with a supplier for reference."""
    return Transaction.objects.exclude(
        supplier__isnull=True
    ).values('id', 'description', 'supplier__name', 'supplier__id', 'raw_data')

def find_best_matches(unmatched_transactions, reference_transactions):
    """Find the best supplier match for each unmatched transaction using n-gram Best Match Method."""
    results = []
    
    # Prepare data structures for n-gram matching
    train_descriptions = []
    supplier_info = []
    
    # Extract descriptions from training data and preprocess
    for ref_tx in reference_transactions:
        # Preprocess the main description
        preprocessed_description = preprocess_description(ref_tx['description'])
        train_descriptions.append(preprocessed_description)
        supplier_info.append({
            'supplier_id': ref_tx['supplier__id'],
            'supplier_name': ref_tx['supplier__name'],
            'tx_id': ref_tx['id'],
            'description': ref_tx['description']
        })
        
        # Extract additional descriptions from groupedPostings in raw_data
        additional_descriptions = []
        try:
            if ref_tx['raw_data'] and isinstance(ref_tx['raw_data'], dict) and 'value' in ref_tx['raw_data']:
                value = ref_tx['raw_data']['value']
                if isinstance(value, dict) and 'groupedPostings' in value:
                    grouped_postings = value['groupedPostings']
                    if isinstance(grouped_postings, list):
                        for posting in grouped_postings:
                            if isinstance(posting, dict) and 'description' in posting and posting['description']:
                                desc = posting['description'].strip()
                                if desc:
                                    # Add to training data
                                    train_descriptions.append(preprocess_description(desc))
                                    supplier_info.append({
                                        'supplier_id': ref_tx['supplier__id'],
                                        'supplier_name': ref_tx['supplier__name'],
                                        'tx_id': ref_tx['id'],
                                        'description': posting['description']
                                    })
        except Exception as e:
            # If any error occurs, just continue
            pass
    
    # Create TF-IDF vectorizer using character n-grams
    vectorizer = TfidfVectorizer(
        analyzer='char',
        ngram_range=(3, 5),
        lowercase=True,
        min_df=2  # Ignore n-grams that appear in less than 2 documents
    )
    
    # Fit and transform training descriptions
    train_vectors = vectorizer.fit_transform(train_descriptions)
    
    # Process each unmatched transaction
    for unmatched_tx in unmatched_transactions:
        # Initialize best match record
        best_match = {
            'transaction_id': unmatched_tx['id'],
            'description': unmatched_tx['description'],
            'best_match_supplier': None,
            'best_match_supplier_id': None,
            'best_match_tx_id': None,
            'best_match_description': None,
            'similarity_score': 0,
            'from_source': None
        }
        
        # Preprocess the main description
        preprocessed_description = preprocess_description(unmatched_tx['description'])
        
        # Match based on main transaction description
        main_desc_vector = vectorizer.transform([preprocessed_description])
        main_cosine_scores = cosine_similarity(main_desc_vector, train_vectors).flatten()
        main_best_idx = main_cosine_scores.argmax()
        main_best_score = main_cosine_scores[main_best_idx]
        main_match_info = supplier_info[main_best_idx]
        
        # Update best match with the main description match
        best_match.update({
            'best_match_supplier': main_match_info['supplier_name'],
            'best_match_supplier_id': main_match_info['supplier_id'],
            'best_match_tx_id': main_match_info['tx_id'],
            'best_match_description': main_match_info['description'],
            'similarity_score': main_best_score,
            'from_source': 'main_description'
        })
        
        # Extract and check grouped posting descriptions if available
        try:
            if unmatched_tx['raw_data'] and isinstance(unmatched_tx['raw_data'], dict) and 'value' in unmatched_tx['raw_data']:
                value = unmatched_tx['raw_data']['value']
                if isinstance(value, dict) and 'groupedPostings' in value:
                    grouped_postings = value['groupedPostings']
                    if isinstance(grouped_postings, list):
                        for i, posting in enumerate(grouped_postings):
                            if isinstance(posting, dict) and 'description' in posting and posting['description']:
                                desc = posting['description'].strip()
                                if desc:
                                    # Preprocess grouped posting description
                                    preprocessed_gp_desc = preprocess_description(desc)
                                    
                                    # Match based on this grouped posting description
                                    gp_vector = vectorizer.transform([preprocessed_gp_desc])
                                    gp_cosine_scores = cosine_similarity(gp_vector, train_vectors).flatten()
                                    gp_best_idx = gp_cosine_scores.argmax()
                                    gp_best_score = gp_cosine_scores[gp_best_idx]
                                    gp_match_info = supplier_info[gp_best_idx]
                                    
                                    # Update best match if this grouped posting has a higher similarity score
                                    if gp_best_score > best_match['similarity_score']:
                                        best_match.update({
                                            'best_match_supplier': gp_match_info['supplier_name'],
                                            'best_match_supplier_id': gp_match_info['supplier_id'],
                                            'best_match_tx_id': gp_match_info['tx_id'],
                                            'best_match_description': gp_match_info['description'],
                                            'similarity_score': gp_best_score,
                                            'from_source': f'grouped_posting_{i}'
                                        })
        except Exception as e:
            # If any error occurs, just continue with the main description match
            pass
        
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
            print(f"  Similarity Score: {result['similarity_score']:.4f}")
            if 'from_source' in result and result['from_source']:
                print(f"  Match Source: {result['from_source']}")
        else:
            print("  No suitable match found.")
            
        print("-" * 80)
    
    if len(sorted_results) > limit:
        print(f"Showing top {limit} results of {len(sorted_results)} total matches.")

def apply_matches_to_database(results, similarity_threshold=0.7):
    """Apply the matches to the database if they meet the similarity threshold, and infer category from supplier's previous transactions."""
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
                
                # Infer category from previous transactions with this supplier
                prev_categories = (
                    Transaction.objects
                    .filter(supplier=supplier)
                    .exclude(category__isnull=True)
                    .values_list('category', flat=True)
                )
                if prev_categories:
                    # Find the most common category
                    from collections import Counter
                    most_common_category_id, _ = Counter(prev_categories).most_common(1)[0]
                    category = Category.objects.filter(id=most_common_category_id).first()
                    if category:
                        transaction.category = category
                        print(f"  → Set category to '{category.name}' (ID: {category.id}) based on supplier's previous transactions.")
                        # Optionally, update or create CategorySupplierMap
                        CategorySupplierMap.objects.get_or_create(supplier=supplier, category=category)
                
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
    help = 'Match transactions without suppliers based on description similarity using N-gram Best Match Method.'

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
            self.stdout.write("Processing matches using Best Match N-gram Method...")
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