#!/usr/bin/env python3
import os
import sys
import difflib
import argparse
import json
import random
import time
import numpy as np
from collections import Counter, defaultdict
from django.core.management.base import BaseCommand
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Import Django models
from transactions.models import Transaction, Supplier, Category, CategorySupplierMap

# Constants
SIMILARITY_THRESHOLD = 0.7  # Default threshold for similarity matching
MIN_TRANSACTIONS_PER_SUPPLIER = 2  # Minimum transactions per supplier for training

def calculate_similarity(text1, text2):
    """Calculates the similarity ratio between two strings using SequenceMatcher."""
    if not text1 or not text2:
        return 0
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def get_unmatched_transactions():
    """Retrieves all transactions without a supplier."""
    return Transaction.objects.filter(
        supplier__isnull=True,
        is_internal_transfer=False,  # Skip internal transfers
        is_wage_transfer=False,      # Skip wage transfers
        is_tax_transfer=False,       # Skip tax transfers
        is_forbidden=False,          # Skip forbidden transactions
    ).order_by('-date', '-id').values('id', 'description')

def get_matched_transactions():
    """Retrieves all transactions with a supplier for reference."""
    return Transaction.objects.exclude(
        supplier__isnull=True
    ).values('id', 'description', 'supplier__name', 'supplier__id')

def create_test_set(test_size=200):
    """Create a test set of transactions with known suppliers."""
    logger.info(f"Creating a test set of {test_size} transactions...")
    
    # Get transactions with suppliers for training
    all_matched = Transaction.objects.filter(
        supplier__isnull=False
    ).select_related('supplier').values(
        'id', 'description', 'supplier__name', 'supplier__id'
    )
    
    # Group by supplier
    supplier_transactions = defaultdict(list)
    for tx in all_matched:
        supplier_transactions[tx['supplier__id']].append(tx)
    
    # Find suppliers with at least 2 transactions
    eligible_suppliers = [
        supplier_id for supplier_id, txs in supplier_transactions.items()
        if len(txs) >= MIN_TRANSACTIONS_PER_SUPPLIER
    ]
    
    # Create test and training sets
    test_set = []
    training_set = []
    
    # Select a subset of suppliers for testing
    selected_suppliers = random.sample(eligible_suppliers, min(test_size, len(eligible_suppliers)))
    
    for supplier_id in eligible_suppliers:
        txs = supplier_transactions[supplier_id]
        
        if supplier_id in selected_suppliers:
            # Add one transaction to test set
            test_tx = random.choice(txs)
            test_set.append(test_tx)
            
            # Add remaining to training set
            for tx in txs:
                if tx['id'] != test_tx['id']:
                    training_set.append(tx)
        else:
            # Add all to training set
            training_set.extend(txs)
    
    logger.info(f"Created test set with {len(test_set)} transactions")
    logger.info(f"Training set contains {len(training_set)} transactions")
    
    return test_set, training_set

# Method implementations for different supplier matching algorithms

def method1_sequence_matcher(unmatched_transactions, reference_transactions):
    """
    Method 1: SequenceMatcher (original method)
    Uses Python's difflib.SequenceMatcher to find similar transactions
    """
    logger.info("Running Method 1: SequenceMatcher")
    start_time = time.time()
    
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
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    return {
        'name': "Method 1: SequenceMatcher",
        'results': results,
        'time': processing_time
    }

def method2_tfidf(unmatched_transactions, reference_transactions):
    """
    Method 2: TF-IDF + Cosine Similarity
    Uses TF-IDF vectorization to find similar transactions
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.error("Required packages not installed. Please run: pip install scikit-learn")
        return {
            'name': "Method 2: TF-IDF + Cosine Similarity",
            'error': "Missing required packages"
        }

    logger.info("Running Method 2: TF-IDF + Cosine Similarity")
    
    # Prepare data structures
    train_descriptions = []
    supplier_info = []
    
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in reference_transactions:
        supplier_transactions[tx['supplier__id']].append(tx)
        train_descriptions.append(tx['description'])
        supplier_info.append({
            'supplier_id': tx['supplier__id'],
            'supplier_name': tx['supplier__name'],
            'tx_id': tx['id']
        })
    
    start_time = time.time()
    
    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer(analyzer='word', lowercase=True)
    
    # Fit and transform training descriptions
    train_vectors = vectorizer.fit_transform(train_descriptions)
    
    # Transform test descriptions
    test_descriptions = [tx['description'] for tx in unmatched_transactions]
    test_vectors = vectorizer.transform(test_descriptions)
    
    # Match each test transaction
    results = []
    for i, test_vector in enumerate(test_vectors):
        # Compute cosine similarity with all training vectors
        cosine_scores = cosine_similarity(test_vector, train_vectors).flatten()
        
        # Get best match
        best_idx = np.argmax(cosine_scores)
        best_score = cosine_scores[best_idx]
        
        match_info = supplier_info[best_idx]
        
        # Add to results
        results.append({
            'transaction_id': unmatched_transactions[i]['id'],
            'description': unmatched_transactions[i]['description'],
            'best_match_supplier': match_info['supplier_name'],
            'best_match_supplier_id': match_info['supplier_id'],
            'best_match_tx_id': match_info['tx_id'],
            'best_match_description': train_descriptions[best_idx],
            'similarity_score': float(best_score)
        })
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    return {
        'name': "Method 2: TF-IDF + Cosine Similarity",
        'results': results,
        'time': processing_time
    }

def method3_ngram(unmatched_transactions, reference_transactions):
    """
    Method 3: N-gram Analysis
    Uses character n-grams to find similar transactions
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.error("Required packages not installed. Please run: pip install scikit-learn")
        return {
            'name': "Method 3: N-gram Analysis",
            'error': "Missing required packages"
        }

    logger.info("Running Method 3: N-gram Analysis")
    
    # Prepare data structures
    train_descriptions = []
    supplier_info = []
    
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in reference_transactions:
        supplier_transactions[tx['supplier__id']].append(tx)
        train_descriptions.append(tx['description'])
        supplier_info.append({
            'supplier_id': tx['supplier__id'],
            'supplier_name': tx['supplier__name'],
            'tx_id': tx['id']
        })
    
    start_time = time.time()
    
    # Create TF-IDF vectorizer using character n-grams
    # Use character n-grams of length 3-5
    vectorizer = TfidfVectorizer(
        analyzer='char',
        ngram_range=(3, 5),
        lowercase=True,
        min_df=1  # Include n-grams that appear in at least 1 document
    )
    
    # Fit and transform training descriptions
    train_vectors = vectorizer.fit_transform(train_descriptions)
    
    # Transform test descriptions
    test_descriptions = [tx['description'] for tx in unmatched_transactions]
    test_vectors = vectorizer.transform(test_descriptions)
    
    # Match each test transaction
    results = []
    for i, test_vector in enumerate(test_vectors):
        # Compute cosine similarity with all training vectors
        cosine_scores = cosine_similarity(test_vector, train_vectors).flatten()
        
        # Get best match
        best_idx = np.argmax(cosine_scores)
        best_score = cosine_scores[best_idx]
        
        match_info = supplier_info[best_idx]
        
        # Add to results in same format as method1
        results.append({
            'transaction_id': unmatched_transactions[i]['id'],
            'description': unmatched_transactions[i]['description'],
            'best_match_supplier': match_info['supplier_name'],
            'best_match_supplier_id': match_info['supplier_id'],
            'best_match_tx_id': match_info['tx_id'],
            'best_match_description': train_descriptions[best_idx],
            'similarity_score': float(best_score)
        })
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    return {
        'name': "Method 3: N-gram Analysis",
        'results': results,
        'time': processing_time
    }

def evaluate_results(results, test_transactions):
    """Evaluate matching results against truth data."""
    if not results or 'error' in results:
        return {
            'accuracy': 0,
            'avg_confidence': 0,
            'correct_count': 0,
            'total_count': len(test_transactions),
            'details': []
        }
    
    # Map transaction IDs to true suppliers
    true_suppliers = {tx['id']: tx['supplier__name'] for tx in test_transactions}
    
    correct_count = 0
    confidences = []
    details = []
    
    for result in results['results']:
        tx_id = result.get('transaction_id')
        predicted = result.get('best_match_supplier')
        confidence = result.get('similarity_score', 0)
        
        if tx_id not in true_suppliers:
            continue
            
        true_supplier = true_suppliers[tx_id]
        is_correct = predicted == true_supplier
        
        if is_correct:
            correct_count += 1
            
        confidences.append(confidence)
        
        # Record detailed results
        tx_desc = next((tx['description'] for tx in test_transactions if tx['id'] == tx_id), "Unknown")
        details.append({
            'transaction_id': tx_id,
            'description': tx_desc,
            'true_supplier': true_supplier,
            'predicted_supplier': predicted,
            'confidence': confidence,
            'correct': is_correct
        })
    
    # Calculate metrics
    accuracy = correct_count / len(test_transactions) if test_transactions else 0
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    return {
        'accuracy': accuracy,
        'avg_confidence': avg_confidence,
        'correct_count': correct_count,
        'total_count': len(test_transactions),
        'details': details
    }

def print_evaluation(method_name, evaluation, processing_time=None):
    """Print formatted evaluation results."""
    print("\n" + "=" * 80)
    print(f"RESULTS FOR: {method_name}")
    print("=" * 80)
    
    print(f"ACCURACY: {evaluation['accuracy'] * 100:.2f}%")
    print(f"CORRECT: {evaluation['correct_count']} / {evaluation['total_count']}")
    print(f"AVG CONFIDENCE: {evaluation['avg_confidence']:.2f}")
    
    if processing_time:
        print(f"PROCESSING TIME: {processing_time:.2f} seconds")
    
    print("\nDETAILED RESULTS:")
    print("-" * 80)
    
    # Sort by confidence (highest first)
    sorted_details = sorted(evaluation['details'], key=lambda x: x.get('confidence', 0), reverse=True)
    
    # Show first 5 results
    for detail in sorted_details[:5]:
        status = "✓" if detail['correct'] else "✗"
        print(f"{status} ID: {detail['transaction_id']}")
        print(f"  Description: {detail['description'][:80]}...")
        print(f"  True: {detail['true_supplier']}")
        print(f"  Predicted: {detail['predicted_supplier']} (Confidence: {detail['confidence']:.2f})")
        print("-" * 40)
    
    if len(sorted_details) > 5:
        print(f"... and {len(sorted_details) - 5} more results.")
    
    print("=" * 80)

def save_results(method_results):
    """Save test results to file for later analysis."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = "supplier_matching_results"
    os.makedirs(results_dir, exist_ok=True)
    
    filename = f"{results_dir}/comparison_{timestamp}.json"
    
    # Prepare data for saving
    save_data = {
        'timestamp': timestamp,
        'methods': {}
    }
    
    for method_name, data in method_results.items():
        save_data['methods'][method_name] = {
            'accuracy': data['evaluation']['accuracy'],
            'correct_count': data['evaluation']['correct_count'],
            'total_count': data['evaluation']['total_count'],
            'avg_confidence': data['evaluation']['avg_confidence'],
            'processing_time': data['time'],
            'details': data['evaluation']['details']
        }
    
    with open(filename, 'w') as f:
        json.dump(save_data, f, indent=2)
    
    logger.info(f"Results saved to {filename}")
    return filename

def find_best_matches(unmatched_transactions, reference_transactions, method='sequence_matcher'):
    """Find the best supplier match for each unmatched transaction using the specified method."""
    if method == 'sequence_matcher':
        results = method1_sequence_matcher(unmatched_transactions, reference_transactions)
    elif method == 'tfidf':
        results = method2_tfidf(unmatched_transactions, reference_transactions)
    elif method == 'ngram':
        results = method3_ngram(unmatched_transactions, reference_transactions)
    else:
        # Default to sequence matcher
        results = method1_sequence_matcher(unmatched_transactions, reference_transactions)
        
    return results['results'] if 'results' in results else []

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
    help = 'Match transactions without suppliers based on description similarity using different methods.'

    def add_arguments(self, parser):
        parser.add_argument('-a', '--apply', action='store_true', 
                          help='Apply matches to the database without prompting')
        parser.add_argument('-t', '--threshold', type=float, default=0.7,
                          help='Similarity threshold for matching (default: 0.7)')
        parser.add_argument('-l', '--limit', type=int, default=0,
                          help='Limit processing to N transactions (default: 0 = all transactions)')
        parser.add_argument('-d', '--display', type=int, default=20,
                          help='Number of results to display (default: 20)')
        parser.add_argument('-m', '--method', type=str, choices=['sequence_matcher', 'tfidf', 'ngram'],
                          default='sequence_matcher',
                          help='Method to use for matching (default: sequence_matcher)')
        parser.add_argument('--test', action='store_true',
                          help='Run in test mode to compare different methods')
        parser.add_argument('--test-size', type=int, default=200,
                          help='Number of transactions to use for testing (default: 200)')
        parser.add_argument('--save', action='store_true',
                          help='Save detailed test results to file')

    def handle(self, *args, **options):
        try:
            if options['test']:
                self.run_test_mode(options)
            else:
                self.run_regular_mode(options)
        except Exception as e:
            self.stderr.write(f"Error: {e}")
            import traceback
            traceback.print_exc()

    def run_test_mode(self, options):
        """Run in test mode to compare different methods."""
        test_size = options['test_size']
        self.stdout.write(f"Running test mode with {test_size} test transactions...")
        
        # Create test set
        test_set, training_set = create_test_set(test_size)
        
        if not test_set:
            self.stdout.write("Error: Could not create test set. Not enough suppliers with multiple transactions.")
            return
        
        # Run all methods
        method_results = {}
        
        # Method 1: SequenceMatcher (original method)
        results1 = method1_sequence_matcher(test_set, training_set)
        if 'error' not in results1:
            evaluation1 = evaluate_results(results1, test_set)
            method_results[results1['name']] = {
                'time': results1['time'],
                'evaluation': evaluation1
            }
            print_evaluation(results1['name'], evaluation1, results1['time'])
        
        # Method 2: TF-IDF + Cosine Similarity
        results2 = method2_tfidf(test_set, training_set)
        if 'error' not in results2:
            evaluation2 = evaluate_results(results2, test_set)
            method_results[results2['name']] = {
                'time': results2['time'],
                'evaluation': evaluation2
            }
            print_evaluation(results2['name'], evaluation2, results2['time'])
        
        # Method 3: N-gram Analysis
        results3 = method3_ngram(test_set, training_set)
        if 'error' not in results3:
            evaluation3 = evaluate_results(results3, test_set)
            method_results[results3['name']] = {
                'time': results3['time'],
                'evaluation': evaluation3
            }
            print_evaluation(results3['name'], evaluation3, results3['time'])
        
        # Determine best method
        if method_results:
            # Find method with highest accuracy
            best_method = max(method_results.items(), 
                             key=lambda x: x[1]['evaluation']['accuracy'])
            
            self.stdout.write(f"\n\nBEST METHOD: {best_method[0]}")
            self.stdout.write(f"ACCURACY: {best_method[1]['evaluation']['accuracy'] * 100:.2f}%")
            self.stdout.write(f"PROCESSING TIME: {best_method[1]['time']:.2f} seconds")
            
            # Save results if requested
            if options['save'] and method_results:
                save_file = save_results(method_results)
                self.stdout.write(f"Detailed results saved to {save_file}")
        else:
            self.stdout.write("No valid results from any method")
            
    def run_regular_mode(self, options):
        """Run in regular mode to match transactions."""
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
        
        # Find best matches using the specified method
        self.stdout.write(f"Processing matches using method: {options['method']}...")
        method_results = find_best_matches(unmatched_transactions, reference_transactions, options['method'])
        
        # Print results
        print_results(method_results, options['display'])
        
        # Apply matches to database if --apply flag is set
        if options['apply']:
            self.stdout.write(f"\nApplying matches to database with similarity threshold ≥ {options['threshold']}...")
            apply_matches_to_database(method_results, options['threshold'])
        else:
            self.stdout.write("\nRun with --apply flag to update the database with these matches.")
            self.stdout.write(f"Note: Only matches with similarity score ≥ {options['threshold']} will be applied.") 