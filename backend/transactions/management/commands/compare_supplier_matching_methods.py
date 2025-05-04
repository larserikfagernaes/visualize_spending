#!/usr/bin/env python3
import os
import sys
import json
import random
import time
import numpy as np
from datetime import datetime
from collections import Counter, defaultdict
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
import logging
import re

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
from transactions.models import Transaction, Supplier, CategorySupplierMap, Category

# Constants
MIN_TRANSACTIONS_PER_SUPPLIER = 2  # Minimum transactions per supplier for training
SIMILARITY_THRESHOLD = 0.7  # Default threshold for similarity matching


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


def create_test_set(test_size=20):
    """Create a test set of transactions with known suppliers."""
    logger.info(f"Creating a test set of {test_size} transactions...")
    
    # Get transactions with suppliers for training
    all_matched = Transaction.objects.filter(
        supplier__isnull=False
    ).select_related('supplier')
    
    # Create a list to hold expanded transaction data
    expanded_transactions = []
    
    for tx in all_matched:
        # Get descriptions from groupedPostings in raw_data
        additional_descriptions = []
        try:
            if tx.raw_data and isinstance(tx.raw_data, dict) and 'value' in tx.raw_data:
                value = tx.raw_data['value']
                if isinstance(value, dict) and 'groupedPostings' in value:
                    grouped_postings = value['groupedPostings']
                    if isinstance(grouped_postings, list):
                        for posting in grouped_postings:
                            if isinstance(posting, dict) and 'description' in posting and posting['description']:
                                desc = posting['description'].strip()
                                if desc:
                                    # Apply preprocessing to grouped posting descriptions
                                    additional_descriptions.append(preprocess_description(desc))
        except Exception as e:
            # If any error occurs, just continue
            logger.warning(f"Error extracting groupedPostings descriptions: {str(e)}")
        
        # Apply preprocessing to the main description
        preprocessed_description = preprocess_description(tx.description)
        
        # Add to expanded list
        expanded_transactions.append({
            'id': tx.id,
            'description': preprocessed_description,
            'original_description': tx.description,  # Keep original for display purposes
            'supplier__name': tx.supplier.name,
            'supplier__id': tx.supplier.id,
            'grouped_posting_descriptions': additional_descriptions
        })
    
    # Group by supplier
    supplier_transactions = defaultdict(list)
    for tx in expanded_transactions:
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


def ngram_supplier_matching(training_set, test_transactions):
    """
    N-gram Analysis for Supplier Matching
    Uses character n-grams to find similar transactions
    Enhanced with descriptions from groupedPostings in raw_data
    Descriptions are preprocessed to remove numbers
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.error("Required packages not installed. Please run: pip install scikit-learn")
        return {
            'name': "N-gram Supplier Matching with GroupedPosting Descriptions",
            'error': "Missing required packages"
        }

    logger.info("Running N-gram Supplier Matching with GroupedPosting Descriptions")
    
    # Prepare data structures
    train_descriptions = []
    supplier_info = []
    
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append(tx)
        
        # Combine main description with grouped posting descriptions
        # Note: descriptions are already preprocessed
        combined_description = tx['description']
        if tx.get('grouped_posting_descriptions'):
            combined_description = f"{combined_description} | {' | '.join(tx['grouped_posting_descriptions'])}"
        
        train_descriptions.append(combined_description)
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
        min_df=2  # Ignore n-grams that appear in less than 2 documents
    )
    
    # Fit and transform training descriptions
    train_vectors = vectorizer.fit_transform(train_descriptions)
    
    # Transform test descriptions
    test_combined_descriptions = []
    for tx in test_transactions:
        # Note: descriptions are already preprocessed
        combined_description = tx['description']
        if tx.get('grouped_posting_descriptions'):
            combined_description = f"{combined_description} | {' | '.join(tx['grouped_posting_descriptions'])}"
        test_combined_descriptions.append(combined_description)
    
    test_vectors = vectorizer.transform(test_combined_descriptions)
    
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
            'transaction_id': test_transactions[i]['id'],
            'best_match_supplier_name': match_info['supplier_name'],
            'confidence_level': int(best_score * 100)
        })
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    return {
        'name': "N-gram Supplier Matching with GroupedPosting Descriptions",
        'results': results,
        'time': processing_time
    }


def ngram_best_match_method(training_set, test_transactions):
    """
    Best Match N-gram Method:
    Run N-gram separately on transaction description and GroupedPosting descriptions,
    then keep prediction with highest confidence.
    Descriptions are preprocessed to remove numbers
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.error("Required packages not installed. Please run: pip install scikit-learn")
        return {
            'name': "Best Match N-gram Method",
            'error': "Missing required packages"
        }

    logger.info("Running Best Match N-gram Method")
    
    # Prepare data structures
    train_descriptions = []
    supplier_info = []
    
    # Process training data
    for tx in training_set:
        # Note: tx['description'] is already preprocessed
        train_descriptions.append(tx['description'])
        supplier_info.append({
            'supplier_id': tx['supplier__id'],
            'supplier_name': tx['supplier__name'],
            'tx_id': tx['id']
        })
    
    start_time = time.time()
    
    # Create TF-IDF vectorizer using character n-grams
    vectorizer = TfidfVectorizer(
        analyzer='char',
        ngram_range=(3, 5),
        lowercase=True,
        min_df=2
    )
    
    # Fit and transform training descriptions
    train_vectors = vectorizer.fit_transform(train_descriptions)
    
    # Process each test transaction
    results = []
    
    for i, test_tx in enumerate(test_transactions):
        # First, match based on main transaction description
        # Note: test_tx['description'] is already preprocessed
        main_desc_vector = vectorizer.transform([test_tx['description']])
        main_cosine_scores = cosine_similarity(main_desc_vector, train_vectors).flatten()
        main_best_idx = np.argmax(main_cosine_scores)
        main_best_score = main_cosine_scores[main_best_idx]
        main_match_info = supplier_info[main_best_idx]
        
        # Store best match from main description
        best_match = {
            'transaction_id': test_tx['id'],
            'best_match_supplier_name': main_match_info['supplier_name'],
            'confidence_level': int(main_best_score * 100),
            'from_source': 'main_description'
        }
        
        # Second, check if there are any GroupedPosting descriptions
        gp_descriptions = test_tx.get('grouped_posting_descriptions', [])
        
        # If there are GroupedPosting descriptions, check each one
        for j, gp_desc in enumerate(gp_descriptions):
            # Note: gp_desc is already preprocessed
            gp_vector = vectorizer.transform([gp_desc])
            gp_cosine_scores = cosine_similarity(gp_vector, train_vectors).flatten()
            gp_best_idx = np.argmax(gp_cosine_scores)
            gp_best_score = gp_cosine_scores[gp_best_idx]
            gp_match_info = supplier_info[gp_best_idx]
            
            # Update best match if this GroupedPosting has a higher confidence
            if gp_best_score > main_best_score:
                best_match = {
                    'transaction_id': test_tx['id'],
                    'best_match_supplier_name': gp_match_info['supplier_name'],
                    'confidence_level': int(gp_best_score * 100),
                    'from_source': f'grouped_posting_{j}'
                }
                main_best_score = gp_best_score  # Update for further comparisons
        
        results.append(best_match)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    # Count the source of best matches
    source_counts = Counter([result['from_source'] for result in results])
    logger.info(f"Best match sources: {dict(source_counts)}")
    
    return {
        'name': "Best Match N-gram Method",
        'results': results,
        'time': processing_time,
        'source_counts': dict(source_counts)
    }


def tfidf_best_match_method(training_set, test_transactions):
    """
    TF-IDF with Word Tokens + Cosine Similarity Method
    Run separately on transaction description and GroupedPosting descriptions,
    then keep prediction with highest confidence.
    Descriptions are preprocessed to remove numbers
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.error("Required packages not installed. Please run: pip install scikit-learn")
        return {
            'name': "TF-IDF Word Token Best Match Method",
            'error': "Missing required packages"
        }

    logger.info("Running TF-IDF Word Token Best Match Method")
    
    # Prepare data structures
    train_descriptions = []
    supplier_info = []
    
    # Process training data
    for tx in training_set:
        # Note: tx['description'] is already preprocessed
        train_descriptions.append(tx['description'])
        supplier_info.append({
            'supplier_id': tx['supplier__id'],
            'supplier_name': tx['supplier__name'],
            'tx_id': tx['id']
        })
    
    start_time = time.time()
    
    # Create TF-IDF vectorizer using word tokens instead of character n-grams
    vectorizer = TfidfVectorizer(
        analyzer='word',
        tokenizer=lambda x: re.findall(r'\w+', x.lower()),
        lowercase=True,
        min_df=1,
        max_features=5000
    )
    
    # Fit and transform training descriptions
    train_vectors = vectorizer.fit_transform(train_descriptions)
    
    # Process each test transaction
    results = []
    
    for i, test_tx in enumerate(test_transactions):
        # First, match based on main transaction description
        # Note: test_tx['description'] is already preprocessed
        main_desc_vector = vectorizer.transform([test_tx['description']])
        main_cosine_scores = cosine_similarity(main_desc_vector, train_vectors).flatten()
        main_best_idx = np.argmax(main_cosine_scores)
        main_best_score = main_cosine_scores[main_best_idx]
        main_match_info = supplier_info[main_best_idx]
        
        # Store best match from main description
        best_match = {
            'transaction_id': test_tx['id'],
            'best_match_supplier_name': main_match_info['supplier_name'],
            'confidence_level': int(main_best_score * 100),
            'from_source': 'main_description'
        }
        
        # Second, check if there are any GroupedPosting descriptions
        gp_descriptions = test_tx.get('grouped_posting_descriptions', [])
        
        # If there are GroupedPosting descriptions, check each one
        for j, gp_desc in enumerate(gp_descriptions):
            # Note: gp_desc is already preprocessed
            gp_vector = vectorizer.transform([gp_desc])
            gp_cosine_scores = cosine_similarity(gp_vector, train_vectors).flatten()
            gp_best_idx = np.argmax(gp_cosine_scores)
            gp_best_score = gp_cosine_scores[gp_best_idx]
            gp_match_info = supplier_info[gp_best_idx]
            
            # Update best match if this GroupedPosting has a higher confidence
            if gp_best_score > main_best_score:
                best_match = {
                    'transaction_id': test_tx['id'],
                    'best_match_supplier_name': gp_match_info['supplier_name'],
                    'confidence_level': int(gp_best_score * 100),
                    'from_source': f'grouped_posting_{j}'
                }
                main_best_score = gp_best_score  # Update for further comparisons
        
        results.append(best_match)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    # Count the source of best matches
    source_counts = Counter([result['from_source'] for result in results])
    logger.info(f"Best match sources: {dict(source_counts)}")
    
    return {
        'name': "TF-IDF Word Token Best Match Method",
        'results': results,
        'time': processing_time,
        'source_counts': dict(source_counts)
    }


def fuzzy_best_match_method(training_set, test_transactions):
    """
    Fuzzy Matching Method
    Run separately on transaction description and GroupedPosting descriptions,
    then keep prediction with highest confidence.
    Descriptions are preprocessed to remove numbers
    """
    try:
        from thefuzz import fuzz
        from thefuzz import process
    except ImportError:
        logger.error("Required packages not installed. Please run: pip install thefuzz")
        return {
            'name': "Fuzzy Best Match Method",
            'error': "Missing required packages"
        }

    logger.info("Running Fuzzy Best Match Method")
    
    # Prepare data structures
    train_descriptions = []
    supplier_info = []
    supplier_lookup = {}
    
    # Process training data
    for tx in training_set:
        # Note: tx['description'] is already preprocessed and lowercase
        clean_desc = tx['description']
        train_descriptions.append((clean_desc, tx['supplier__name']))
        
        # Create a lookup by supplier name for efficient processing
        if tx['supplier__name'] not in supplier_lookup:
            supplier_lookup[tx['supplier__name']] = []
        supplier_lookup[tx['supplier__name']].append(clean_desc)
    
    start_time = time.time()
    
    # Process each test transaction
    results = []
    
    for i, test_tx in enumerate(test_transactions):
        # First, match based on main transaction description
        # Note: test_tx['description'] is already preprocessed
        main_desc = test_tx['description']
        
        # Find best supplier match using fuzzy matching
        best_suppliers = {}
        
        # For each supplier, find best match against any of its descriptions
        for supplier_name, descriptions in supplier_lookup.items():
            best_score = 0
            for desc in descriptions:
                # Use token_sort_ratio to handle word order differences
                score = fuzz.token_sort_ratio(main_desc, desc)
                if score > best_score:
                    best_score = score
            
            best_suppliers[supplier_name] = best_score
        
        # Find the supplier with the highest score
        main_best_supplier = max(best_suppliers.items(), key=lambda x: x[1])
        main_best_name = main_best_supplier[0]
        main_best_score = main_best_supplier[1]
        
        # Store best match from main description
        best_match = {
            'transaction_id': test_tx['id'],
            'best_match_supplier_name': main_best_name,
            'confidence_level': main_best_score,
            'from_source': 'main_description'
        }
        
        # Second, check if there are any GroupedPosting descriptions
        gp_descriptions = test_tx.get('grouped_posting_descriptions', [])
        
        # If there are GroupedPosting descriptions, check each one
        for j, gp_desc in enumerate(gp_descriptions):
            # Note: gp_desc is already preprocessed
            
            # For each supplier, find best match against any of its descriptions
            gp_best_suppliers = {}
            for supplier_name, descriptions in supplier_lookup.items():
                best_score = 0
                for desc in descriptions:
                    score = fuzz.token_sort_ratio(gp_desc, desc)
                    if score > best_score:
                        best_score = score
                
                gp_best_suppliers[supplier_name] = best_score
            
            # Find the supplier with the highest score
            gp_best_supplier = max(gp_best_suppliers.items(), key=lambda x: x[1])
            gp_best_name = gp_best_supplier[0]
            gp_best_score = gp_best_supplier[1]
            
            # Update best match if this GroupedPosting has a higher confidence
            if gp_best_score > main_best_score:
                best_match = {
                    'transaction_id': test_tx['id'],
                    'best_match_supplier_name': gp_best_name,
                    'confidence_level': gp_best_score,
                    'from_source': f'grouped_posting_{j}'
                }
                main_best_score = gp_best_score  # Update for further comparisons
        
        results.append(best_match)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    # Count the source of best matches
    source_counts = Counter([result['from_source'] for result in results])
    logger.info(f"Best match sources: {dict(source_counts)}")
    
    return {
        'name': "Fuzzy Best Match Method",
        'results': results,
        'time': processing_time,
        'source_counts': dict(source_counts)
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
        predicted = result.get('best_match_supplier_name')
        confidence = result.get('confidence_level', 0)
        from_source = result.get('from_source', 'unknown')
        
        if tx_id not in true_suppliers:
            continue
            
        true_supplier = true_suppliers[tx_id]
        is_correct = predicted == true_supplier
        
        if is_correct:
            correct_count += 1
            
        confidences.append(confidence)
        
        # Record detailed results
        # Use original_description for display if available, otherwise use processed description
        tx_desc = next((tx.get('original_description', tx['description']) 
                        for tx in test_transactions if tx['id'] == tx_id), "Unknown")
        
        details.append({
            'transaction_id': tx_id,
            'description': tx_desc,
            'true_supplier': true_supplier,
            'predicted_supplier': predicted,
            'confidence': confidence,
            'correct': is_correct,
            'from_source': from_source
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


def print_incorrect_matches(evaluation):
    """Print all incorrect matches."""
    print("\n" + "=" * 80)
    print("INCORRECT MATCHES:")
    print("=" * 80)
    
    incorrect_matches = [detail for detail in evaluation['details'] if not detail['correct']]
    
    if not incorrect_matches:
        print("No incorrect matches found!")
        return
    
    print(f"Found {len(incorrect_matches)} incorrect matches out of {len(evaluation['details'])} total.")
    print("-" * 80)
    
    for i, detail in enumerate(incorrect_matches):
        print(f"Incorrect Match #{i+1}:")
        print(f"  Transaction ID: {detail['transaction_id']}")
        print(f"  Description: {detail['description']}")  # This is now the original description
        print(f"  True Supplier: {detail['true_supplier']}")
        print(f"  Predicted (Wrong) Supplier: {detail['predicted_supplier']}")
        print(f"  Confidence: {detail['confidence']}%")
        if 'from_source' in detail:
            print(f"  Source: {detail['from_source']}")
        print("-" * 80)


def apply_to_unmatched_transactions(threshold=SIMILARITY_THRESHOLD, use_best_match=False, method='ngram'):
    """
    Apply supplier matching to unmatched transactions in the database.
    Only updates transactions if confidence is above threshold.
    """
    # Get all transactions without suppliers
    unmatched_txs = Transaction.objects.filter(
        supplier__isnull=True,
        is_internal_transfer=False,  # Skip internal transfers
        is_wage_transfer=False,      # Skip wage transfers
        is_tax_transfer=False,       # Skip tax transfers
        is_forbidden=False,          # Skip forbidden transactions
    )
    
    logger.info(f"Found {unmatched_txs.count()} transactions without suppliers")
    
    if not unmatched_txs.exists():
        return 0
    
    # Create expanded transaction data with GroupedPosting descriptions
    expanded_unmatched = []
    for tx in unmatched_txs:
        # Get descriptions from groupedPostings in raw_data
        additional_descriptions = []
        try:
            if tx.raw_data and isinstance(tx.raw_data, dict) and 'value' in tx.raw_data:
                value = tx.raw_data['value']
                if isinstance(value, dict) and 'groupedPostings' in value:
                    grouped_postings = value['groupedPostings']
                    if isinstance(grouped_postings, list):
                        for posting in grouped_postings:
                            if isinstance(posting, dict) and 'description' in posting and posting['description']:
                                desc = posting['description'].strip()
                                if desc:
                                    # Apply preprocessing to grouped posting descriptions
                                    additional_descriptions.append(preprocess_description(desc))
        except Exception as e:
            pass
        
        # Apply preprocessing to the main description
        preprocessed_description = preprocess_description(tx.description)
        
        expanded_unmatched.append({
            'id': tx.id,
            'description': preprocessed_description,
            'original_description': tx.description,  # Keep original for reference
            'grouped_posting_descriptions': additional_descriptions
        })
    
    # Get all transactions with suppliers for training
    all_matched = Transaction.objects.filter(
        supplier__isnull=False
    ).select_related('supplier')
    
    # Create expanded training data
    expanded_training = []
    for tx in all_matched:
        additional_descriptions = []
        try:
            if tx.raw_data and isinstance(tx.raw_data, dict) and 'value' in tx.raw_data:
                value = tx.raw_data['value']
                if isinstance(value, dict) and 'groupedPostings' in value:
                    grouped_postings = value['groupedPostings']
                    if isinstance(grouped_postings, list):
                        for posting in grouped_postings:
                            if isinstance(posting, dict) and 'description' in posting and posting['description']:
                                desc = posting['description'].strip()
                                if desc:
                                    # Apply preprocessing to grouped posting descriptions
                                    additional_descriptions.append(preprocess_description(desc))
        except Exception as e:
            pass
        
        # Apply preprocessing to the main description
        preprocessed_description = preprocess_description(tx.description)
        
        expanded_training.append({
            'id': tx.id,
            'description': preprocessed_description,
            'original_description': tx.description,  # Keep original for reference
            'supplier__name': tx.supplier.name,
            'supplier__id': tx.supplier.id,
            'grouped_posting_descriptions': additional_descriptions
        })
    
    # Run the matching with selected method
    if method == 'tfidf':
        results = tfidf_best_match_method(expanded_training, expanded_unmatched)
    elif method == 'fuzzy':
        results = fuzzy_best_match_method(expanded_training, expanded_unmatched)
    elif use_best_match:
        results = ngram_best_match_method(expanded_training, expanded_unmatched)
    else:
        results = ngram_supplier_matching(expanded_training, expanded_unmatched)
    
    if 'error' in results:
        logger.error(f"Error running matching: {results['error']}")
        return 0
    
    # Process results
    matched_count = 0
    for result in results['results']:
        tx_id = result['transaction_id']
        supplier_name = result['best_match_supplier_name']
        confidence = result['confidence_level']
        
        if confidence >= threshold * 100:
            # Look up supplier id
            try:
                supplier = Supplier.objects.get(name=supplier_name)
                
                # Update transaction
                tx = Transaction.objects.get(id=tx_id)
                tx.supplier = supplier
                
                # Also look for a suitable category based on this supplier's past transactions
                category_ids = Transaction.objects.filter(
                    supplier=supplier, 
                    category__isnull=False
                ).values_list('category_id', flat=True)
                
                if category_ids:
                    # Find the most common category for this supplier
                    most_common_category_id = Counter(category_ids).most_common(1)[0][0]
                    tx.category_id = most_common_category_id
                    
                    # Update the supplier-category mapping
                    CategorySupplierMap.objects.get_or_create(
                        supplier=supplier,
                        category_id=most_common_category_id
                    )
                
                # Save the transaction
                tx.save()
                matched_count += 1
                
                logger.info(f"Matched transaction {tx_id} to {supplier_name} (confidence: {confidence})")
                
            except Supplier.DoesNotExist:
                logger.error(f"Supplier not found: {supplier_name}")
            except Transaction.DoesNotExist:
                logger.error(f"Transaction not found: {tx_id}")
    
    logger.info(f"Updated {matched_count} transactions with suppliers")
    return matched_count


class Command(BaseCommand):
    help = 'Match suppliers to transactions using different text matching methods'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-size', 
            type=int, 
            default=50,
            help='Number of transactions to use for testing (default: 50)'
        )
        parser.add_argument(
            '--save', 
            action='store_true',
            help='Save detailed results to file'
        )
        parser.add_argument(
            '--apply', 
            action='store_true',
            help='Apply supplier matching to unmatched transactions in database'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=SIMILARITY_THRESHOLD,
            help=f'Similarity threshold for matching (default: {SIMILARITY_THRESHOLD})'
        )
        
        # Method selection arguments
        method_group = parser.add_mutually_exclusive_group()
        method_group.add_argument(
            '--best-match',
            action='store_true',
            help='Use the Best Match N-gram method (separate match for each description)'
        )
        method_group.add_argument(
            '--tfidf',
            action='store_true',
            help='Use TF-IDF word token method instead of character n-grams'
        )
        method_group.add_argument(
            '--fuzzy',
            action='store_true',
            help='Use Fuzzy string matching instead of vector methods'
        )
        
        # Comparison options
        parser.add_argument(
            '--compare',
            action='store_true',
            help='Compare all methods'
        )
        parser.add_argument(
            '--compare-best',
            action='store_true',
            help='Compare all best-match methods (n-gram, tfidf, fuzzy)'
        )

    def handle(self, *args, **options):
        try:
            test_size = options['test_size']
            threshold = options['threshold']
            use_best_match = options['best_match']
            use_tfidf = options['tfidf']
            use_fuzzy = options['fuzzy']
            should_compare = options['compare']
            compare_best = options['compare_best']
            
            # Determine which method to use
            method = 'ngram'
            if use_tfidf:
                method = 'tfidf'
            elif use_fuzzy:
                method = 'fuzzy'
            
            # If apply flag is set, apply matching to unmatched transactions
            if options['apply']:
                self.stdout.write(f"Applying supplier matching to unmatched transactions using {method} method...")
                matched_count = apply_to_unmatched_transactions(threshold, use_best_match, method)
                self.stdout.write(f"Updated {matched_count} transactions with suppliers")
                return
            
            # Otherwise, run test mode
            self.stdout.write(f"Running supplier matching test with {test_size} test transactions")
            
            # Create test set
            test_set, training_set = create_test_set(test_size)
            
            if not test_set:
                self.stdout.write("Error: Could not create test set. Not enough suppliers with multiple transactions.")
                return
            
            results = None
            evaluation = None
            
            # Run the selected method or multiple methods if comparing
            if should_compare:
                # Run all methods for comparison
                combined_results = ngram_supplier_matching(training_set, test_set)
                combined_evaluation = evaluate_results(combined_results, test_set)
                
                ngram_best_results = ngram_best_match_method(training_set, test_set)
                ngram_best_evaluation = evaluate_results(ngram_best_results, test_set)
                
                tfidf_results = tfidf_best_match_method(training_set, test_set)
                tfidf_evaluation = evaluate_results(tfidf_results, test_set)
                
                fuzzy_results = fuzzy_best_match_method(training_set, test_set)
                fuzzy_evaluation = evaluate_results(fuzzy_results, test_set)
                
                # Print results for each method
                print("\n" + "=" * 80)
                print(f"RESULTS FOR: {combined_results['name']}")
                print("=" * 80)
                print(f"ACCURACY: {combined_evaluation['accuracy'] * 100:.2f}%")
                print(f"CORRECT: {combined_evaluation['correct_count']} / {combined_evaluation['total_count']}")
                print(f"AVG CONFIDENCE: {combined_evaluation['avg_confidence']:.2f}")
                print(f"PROCESSING TIME: {combined_results['time']:.2f} seconds")
                
                print("\n" + "=" * 80)
                print(f"RESULTS FOR: {ngram_best_results['name']}")
                print("=" * 80)
                print(f"ACCURACY: {ngram_best_evaluation['accuracy'] * 100:.2f}%")
                print(f"CORRECT: {ngram_best_evaluation['correct_count']} / {ngram_best_evaluation['total_count']}")
                print(f"AVG CONFIDENCE: {ngram_best_evaluation['avg_confidence']:.2f}")
                print(f"PROCESSING TIME: {ngram_best_results['time']:.2f} seconds")
                print(f"BEST MATCH SOURCES: {ngram_best_results.get('source_counts', {})}")
                
                print("\n" + "=" * 80)
                print(f"RESULTS FOR: {tfidf_results['name']}")
                print("=" * 80)
                print(f"ACCURACY: {tfidf_evaluation['accuracy'] * 100:.2f}%")
                print(f"CORRECT: {tfidf_evaluation['correct_count']} / {tfidf_evaluation['total_count']}")
                print(f"AVG CONFIDENCE: {tfidf_evaluation['avg_confidence']:.2f}")
                print(f"PROCESSING TIME: {tfidf_results['time']:.2f} seconds")
                print(f"BEST MATCH SOURCES: {tfidf_results.get('source_counts', {})}")
                
                print("\n" + "=" * 80)
                print(f"RESULTS FOR: {fuzzy_results['name']}")
                print("=" * 80)
                print(f"ACCURACY: {fuzzy_evaluation['accuracy'] * 100:.2f}%")
                print(f"CORRECT: {fuzzy_evaluation['correct_count']} / {fuzzy_evaluation['total_count']}")
                print(f"AVG CONFIDENCE: {fuzzy_evaluation['avg_confidence']:.2f}")
                print(f"PROCESSING TIME: {fuzzy_results['time']:.2f} seconds")
                print(f"BEST MATCH SOURCES: {fuzzy_results.get('source_counts', {})}")
                
                # Select best method
                methods = [
                    ('Combined N-gram', combined_evaluation['accuracy'], combined_results, combined_evaluation),
                    ('Best Match N-gram', ngram_best_evaluation['accuracy'], ngram_best_results, ngram_best_evaluation),
                    ('TF-IDF Word Token', tfidf_evaluation['accuracy'], tfidf_results, tfidf_evaluation),
                    ('Fuzzy Matching', fuzzy_evaluation['accuracy'], fuzzy_results, fuzzy_evaluation)
                ]
                
                best_method = max(methods, key=lambda x: x[1])
                
                print("\n" + "=" * 80)
                print("COMPARISON RESULTS")
                print("=" * 80)
                print(f"Best performing method: {best_method[0]} with accuracy {best_method[1] * 100:.2f}%")
                
                # Use the best method for incorrect match analysis
                results = best_method[2]
                evaluation = best_method[3]
                
            elif compare_best:
                # Compare only the best-match variants
                ngram_best_results = ngram_best_match_method(training_set, test_set)
                ngram_best_evaluation = evaluate_results(ngram_best_results, test_set)
                
                tfidf_results = tfidf_best_match_method(training_set, test_set)
                tfidf_evaluation = evaluate_results(tfidf_results, test_set)
                
                fuzzy_results = fuzzy_best_match_method(training_set, test_set)
                fuzzy_evaluation = evaluate_results(fuzzy_results, test_set)
                
                # Print results for each method
                print("\n" + "=" * 80)
                print(f"RESULTS FOR: {ngram_best_results['name']}")
                print("=" * 80)
                print(f"ACCURACY: {ngram_best_evaluation['accuracy'] * 100:.2f}%")
                print(f"CORRECT: {ngram_best_evaluation['correct_count']} / {ngram_best_evaluation['total_count']}")
                print(f"AVG CONFIDENCE: {ngram_best_evaluation['avg_confidence']:.2f}")
                print(f"PROCESSING TIME: {ngram_best_results['time']:.2f} seconds")
                print(f"BEST MATCH SOURCES: {ngram_best_results.get('source_counts', {})}")
                
                print("\n" + "=" * 80)
                print(f"RESULTS FOR: {tfidf_results['name']}")
                print("=" * 80)
                print(f"ACCURACY: {tfidf_evaluation['accuracy'] * 100:.2f}%")
                print(f"CORRECT: {tfidf_evaluation['correct_count']} / {tfidf_evaluation['total_count']}")
                print(f"AVG CONFIDENCE: {tfidf_evaluation['avg_confidence']:.2f}")
                print(f"PROCESSING TIME: {tfidf_results['time']:.2f} seconds")
                print(f"BEST MATCH SOURCES: {tfidf_results.get('source_counts', {})}")
                
                print("\n" + "=" * 80)
                print(f"RESULTS FOR: {fuzzy_results['name']}")
                print("=" * 80)
                print(f"ACCURACY: {fuzzy_evaluation['accuracy'] * 100:.2f}%")
                print(f"CORRECT: {fuzzy_evaluation['correct_count']} / {fuzzy_evaluation['total_count']}")
                print(f"AVG CONFIDENCE: {fuzzy_evaluation['avg_confidence']:.2f}")
                print(f"PROCESSING TIME: {fuzzy_results['time']:.2f} seconds")
                print(f"BEST MATCH SOURCES: {fuzzy_results.get('source_counts', {})}")
                
                # Select best method
                methods = [
                    ('Best Match N-gram', ngram_best_evaluation['accuracy'], ngram_best_results, ngram_best_evaluation),
                    ('TF-IDF Word Token', tfidf_evaluation['accuracy'], tfidf_results, tfidf_evaluation),
                    ('Fuzzy Matching', fuzzy_evaluation['accuracy'], fuzzy_results, fuzzy_evaluation)
                ]
                
                best_method = max(methods, key=lambda x: x[1])
                
                print("\n" + "=" * 80)
                print("COMPARISON RESULTS")
                print("=" * 80)
                print(f"Best performing method: {best_method[0]} with accuracy {best_method[1] * 100:.2f}%")
                
                # Use the best method for incorrect match analysis
                results = best_method[2]
                evaluation = best_method[3]
                
            else:
                # Run only one method based on the options
                if use_tfidf:
                    results = tfidf_best_match_method(training_set, test_set)
                elif use_fuzzy:
                    results = fuzzy_best_match_method(training_set, test_set)
                elif use_best_match:
                    results = ngram_best_match_method(training_set, test_set)
                else:
                    results = ngram_supplier_matching(training_set, test_set)
                
                if 'error' in results:
                    self.stdout.write(f"Error with matching method: {results['error']}")
                    return
                    
                # Evaluate results
                evaluation = evaluate_results(results, test_set)
                
                # Print summary
                print("\n" + "=" * 80)
                print(f"RESULTS FOR: {results['name']}")
                print("=" * 80)
                
                print(f"ACCURACY: {evaluation['accuracy'] * 100:.2f}%")
                print(f"CORRECT: {evaluation['correct_count']} / {evaluation['total_count']}")
                print(f"AVG CONFIDENCE: {evaluation['avg_confidence']:.2f}")
                print(f"PROCESSING TIME: {results['time']:.2f} seconds")
                
                if 'source_counts' in results:
                    print(f"BEST MATCH SOURCES: {results['source_counts']}")
            
            # Print all incorrect matches for the final selected method
            if evaluation:
                print_incorrect_matches(evaluation)
            
            # Save results if requested
            if options['save'] and results and evaluation:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                results_dir = "supplier_matching_results"
                os.makedirs(results_dir, exist_ok=True)
                
                method_name = "unknown"
                if use_tfidf:
                    method_name = "tfidf"
                elif use_fuzzy:
                    method_name = "fuzzy"
                elif use_best_match:
                    method_name = "best_match"
                else:
                    method_name = "combined"
                
                if should_compare:
                    method_name = "comparison"
                elif compare_best:
                    method_name = "best_methods_comparison"
                
                filename = f"{results_dir}/{method_name}_{timestamp}.json"
                
                save_data = {
                    'timestamp': timestamp,
                    'method': results['name'],
                    'accuracy': evaluation['accuracy'],
                    'correct_count': evaluation['correct_count'],
                    'total_count': evaluation['total_count'],
                    'avg_confidence': evaluation['avg_confidence'],
                    'processing_time': results['time'],
                    'details': evaluation['details']
                }
                
                if 'source_counts' in results:
                    save_data['source_counts'] = results['source_counts']
                
                with open(filename, 'w') as f:
                    json.dump(save_data, f, indent=2)
                
                self.stdout.write(f"Results saved to {filename}")
                
        except Exception as e:
            self.stderr.write(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    pass 