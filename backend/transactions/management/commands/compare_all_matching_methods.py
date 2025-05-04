#!/usr/bin/env python3
import os
import sys
import json
import random
import time
import numpy as np
import logging
from datetime import datetime
from collections import Counter, defaultdict
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

# Constants
MIN_TRANSACTIONS_PER_SUPPLIER = 2  # Minimum transactions per supplier for training
SIMILARITY_THRESHOLD = 0.7  # Default threshold for similarity matching
MAX_TEST_SIZE = 100  # Maximum test set size

def create_test_set(test_size=20):
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

def method1_embedding_nn(training_set, test_transactions):
    """
    Method 1: Text Embedding + Nearest Neighbor Search
    Uses sentence embeddings to find similar transactions
    """
    try:
        from sentence_transformers import SentenceTransformer, util
        import torch
    except ImportError:
        logger.error("Required packages not installed. Please run: pip install sentence-transformers torch")
        return {
            'name': "Method 1: Text Embedding + Nearest Neighbor Search",
            'error': "Missing required packages"
        }

    logger.info("Running Method 1: Text Embedding + Nearest Neighbor Search")
    
    # Load model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"Using device: {device}")
    model = model.to(device)
    
    # Prepare data structures
    supplier_info = []
    
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append(tx)
    
    # Create training embeddings
    all_descriptions = []
    for supplier_id, transactions in supplier_transactions.items():
        for tx in transactions:
            all_descriptions.append(tx['description'])
            supplier_info.append({
                'supplier_id': tx['supplier__id'],
                'supplier_name': tx['supplier__name'],
                'tx_id': tx['id'],
                'description': tx['description']
            })
    
    start_time = time.time()
    
    # Encode training descriptions
    logger.info(f"Encoding {len(all_descriptions)} training descriptions...")
    train_embeddings = model.encode(all_descriptions, convert_to_tensor=True)
    
    # Encode test descriptions
    test_descriptions = [tx['description'] for tx in test_transactions]
    logger.info(f"Encoding {len(test_descriptions)} test descriptions...")
    test_embeddings = model.encode(test_descriptions, convert_to_tensor=True)
    
    # Match each test transaction
    results = []
    for i, embedding in enumerate(test_embeddings):
        # Compute cosine similarity
        cosine_scores = util.cos_sim(embedding, train_embeddings)[0]
        
        # Get best match
        best_score, best_idx = torch.max(cosine_scores, dim=0)
        best_score = best_score.item()
        best_idx = best_idx.item()
        
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
        'name': "Method 1: Text Embedding + Nearest Neighbor Search",
        'results': results,
        'time': processing_time
    }

def method2_tfidf(training_set, test_transactions):
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
    for tx in training_set:
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
    test_descriptions = [tx['description'] for tx in test_transactions]
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
            'transaction_id': test_transactions[i]['id'],
            'best_match_supplier_name': match_info['supplier_name'],
            'confidence_level': int(best_score * 100)
        })
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    return {
        'name': "Method 2: TF-IDF + Cosine Similarity",
        'results': results,
        'time': processing_time
    }

def method3_levenshtein(training_set, test_transactions):
    """
    Method 3: Fuzzy Matching / String Similarity (Levenshtein)
    Uses Levenshtein distance to find similar transactions
    """
    try:
        import Levenshtein
        USE_THEFUZZ = False
    except ImportError:
        try:
            from thefuzz import fuzz
            USE_THEFUZZ = True
        except ImportError:
            logger.error("Required packages not installed. Please run: pip install python-Levenshtein OR pip install thefuzz")
            return {
                'name': "Method 3: Fuzzy Matching / String Similarity",
                'error': "Missing required packages"
            }

    logger.info("Running Method 3: Fuzzy Matching / String Similarity (Levenshtein)")
    
    # Prepare data structures
    train_descriptions = []
    supplier_info = []
    
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append(tx)
        train_descriptions.append(tx['description'])
        supplier_info.append({
            'supplier_id': tx['supplier__id'],
            'supplier_name': tx['supplier__name'],
            'tx_id': tx['id'],
            'description': tx['description']
        })
    
    start_time = time.time()
    
    # Match each test transaction
    results = []
    for test_tx in test_transactions:
        test_desc = test_tx['description']
        max_similarity = 0
        best_match_idx = 0
        
        # Compare with each training description
        for i, train_desc in enumerate(train_descriptions):
            # Calculate similarity based on Levenshtein distance
            if USE_THEFUZZ:
                # Using thefuzz similarity (0-100 scale)
                similarity = fuzz.ratio(test_desc, train_desc) / 100.0
            else:
                # Using Levenshtein distance normalized to 0-1 scale
                max_len = max(len(test_desc), len(train_desc))
                if max_len == 0:  # Handle empty strings
                    similarity = 1.0
                else:
                    distance = Levenshtein.distance(test_desc, train_desc)
                    similarity = 1.0 - (distance / max_len)
            
            if similarity > max_similarity:
                max_similarity = similarity
                best_match_idx = i
        
        match_info = supplier_info[best_match_idx]
        
        # Add to results
        results.append({
            'transaction_id': test_tx['id'],
            'best_match_supplier_name': match_info['supplier_name'],
            'confidence_level': int(max_similarity * 100)
        })
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    return {
        'name': "Method 3: Fuzzy Matching / String Similarity",
        'results': results,
        'time': processing_time
    }

def method4_embedding_reference_db(training_set, test_transactions):
    """
    Method 4: Our implementation from match_suppliers_with_embeddings.py
    Uses embedding reference database for faster matching
    """
    try:
        from sentence_transformers import SentenceTransformer, util
        import torch
    except ImportError:
        logger.error("Required packages not installed. Please run: pip install sentence-transformers torch")
        return {
            'name': "Method 4: Embedding Reference Database",
            'error': "Missing required packages"
        }

    logger.info("Running Method 4: Embedding Reference Database")
    
    # Load model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"Using device: {device}")
    model = model.to(device)
    
    # Globals to store embeddings and related data
    supplier_embeddings = []
    supplier_info = []
    
    start_time = time.time()
    
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append(tx)
    
    # Process each supplier
    for supplier_id, transactions in supplier_transactions.items():
        # Extract supplier name
        supplier_name = transactions[0]['supplier__name']
        
        # Get all descriptions
        descriptions = [tx['description'] for tx in transactions]
        
        # Encode descriptions
        embeddings = model.encode(descriptions, convert_to_tensor=True)
        
        # Add to reference database
        for i, embedding in enumerate(embeddings):
            supplier_embeddings.append(embedding)
            supplier_info.append({
                'supplier_id': supplier_id,
                'supplier_name': supplier_name,
                'description': descriptions[i]
            })
    
    # Convert list to tensor for faster processing
    supplier_embeddings = torch.stack(supplier_embeddings)
    
    # Process test transactions
    results = []
    
    # Get descriptions for the batch
    test_descriptions = [tx['description'] for tx in test_transactions]
    
    # Encode descriptions
    test_embeddings = model.encode(test_descriptions, convert_to_tensor=True)
    
    # Match against supplier embeddings
    for i, embedding in enumerate(test_embeddings):
        # Compute cosine similarity
        cosine_scores = util.cos_sim(embedding, supplier_embeddings)[0]
        
        # Get best match
        best_score, best_idx = torch.max(cosine_scores, dim=0)
        best_score = best_score.item()
        best_idx = best_idx.item()
        
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
        'name': "Method 4: Embedding Reference Database",
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
        predicted = result.get('best_match_supplier_name')
        confidence = result.get('confidence_level', 0)
        
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
    
    for detail in evaluation['details'][:5]:  # Show first 5 results
        status = "✓" if detail['correct'] else "✗"
        print(f"{status} ID: {detail['transaction_id']}")
        print(f"  Description: {detail['description'][:80]}...")
        print(f"  True: {detail['true_supplier']}")
        print(f"  Predicted: {detail['predicted_supplier']} (Confidence: {detail['confidence']})")
        print("-" * 40)
    
    if len(evaluation['details']) > 5:
        print(f"... and {len(evaluation['details']) - 5} more results.")
    
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

class Command(BaseCommand):
    help = 'Compare all supplier matching methods using transaction descriptions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-size', 
            type=int, 
            default=50,
            help='Number of transactions to use for testing (default: 50)'
        )
        parser.add_argument(
            '--methods', 
            type=str,
            default='1,2,3,4',
            help='Methods to test (comma-separated, 1-4)'
        )
        parser.add_argument(
            '--save', 
            action='store_true',
            help='Save detailed results to file'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=SIMILARITY_THRESHOLD,
            help=f'Similarity threshold for matching (default: {SIMILARITY_THRESHOLD})'
        )

    def handle(self, *args, **options):
        try:
            test_size = min(options['test_size'], MAX_TEST_SIZE)
            threshold = options['threshold']
            
            # Parse methods
            methods = [int(m.strip()) for m in options['methods'].split(',') if m.strip().isdigit()]
            if not methods:
                methods = [1, 2, 3, 4]  # Default to all methods
            
            self.stdout.write(f"Running comparison with {test_size} test transactions")
            self.stdout.write(f"Testing methods: {', '.join([str(m) for m in methods])}")
            
            # Create test set
            test_set, training_set = create_test_set(test_size)
            
            if not test_set:
                self.stdout.write("Error: Could not create test set. Not enough suppliers with multiple transactions.")
                return
            
            method_results = {}
            
            # Method 1: Text Embedding + Nearest Neighbor Search
            if 1 in methods:
                try:
                    results = method1_embedding_nn(training_set, test_set)
                    if 'error' not in results:
                        evaluation = evaluate_results(results, test_set)
                        method_results[results['name']] = {
                            'time': results['time'],
                            'evaluation': evaluation
                        }
                        print_evaluation(results['name'], evaluation, results['time'])
                    else:
                        self.stdout.write(f"Error with Method 1: {results['error']}")
                except Exception as e:
                    self.stderr.write(f"Error running Method 1: {e}")
            
            # Method 2: TF-IDF + Cosine Similarity
            if 2 in methods:
                try:
                    results = method2_tfidf(training_set, test_set)
                    if 'error' not in results:
                        evaluation = evaluate_results(results, test_set)
                        method_results[results['name']] = {
                            'time': results['time'],
                            'evaluation': evaluation
                        }
                        print_evaluation(results['name'], evaluation, results['time'])
                    else:
                        self.stdout.write(f"Error with Method 2: {results['error']}")
                except Exception as e:
                    self.stderr.write(f"Error running Method 2: {e}")
            
            # Method 3: Fuzzy Matching / String Similarity
            if 3 in methods:
                try:
                    results = method3_levenshtein(training_set, test_set)
                    if 'error' not in results:
                        evaluation = evaluate_results(results, test_set)
                        method_results[results['name']] = {
                            'time': results['time'],
                            'evaluation': evaluation
                        }
                        print_evaluation(results['name'], evaluation, results['time'])
                    else:
                        self.stdout.write(f"Error with Method 3: {results['error']}")
                except Exception as e:
                    self.stderr.write(f"Error running Method 3: {e}")
            
            # Method 4: Embedding Reference Database (from match_suppliers_with_embeddings.py)
            if 4 in methods:
                try:
                    results = method4_embedding_reference_db(training_set, test_set)
                    if 'error' not in results:
                        evaluation = evaluate_results(results, test_set)
                        method_results[results['name']] = {
                            'time': results['time'],
                            'evaluation': evaluation
                        }
                        print_evaluation(results['name'], evaluation, results['time'])
                    else:
                        self.stdout.write(f"Error with Method 4: {results['error']}")
                except Exception as e:
                    self.stderr.write(f"Error running Method 4: {e}")
            
            # Determine best method
            if method_results:
                # Find method with highest accuracy
                best_method = max(method_results.items(), 
                                 key=lambda x: x[1]['evaluation']['accuracy'])
                
                # If there's a tie, use processing time as tiebreaker
                best_methods = [
                    (name, data) for name, data in method_results.items() 
                    if data['evaluation']['accuracy'] == best_method[1]['evaluation']['accuracy']
                ]
                
                if len(best_methods) > 1:
                    best_method = min(best_methods, key=lambda x: x[1]['time'])
                
                self.stdout.write(f"\n\nBEST METHOD: {best_method[0]}")
                self.stdout.write(f"ACCURACY: {best_method[1]['evaluation']['accuracy'] * 100:.2f}%")
                self.stdout.write(f"PROCESSING TIME: {best_method[1]['time']:.2f} seconds")
                
                # Save results if requested
                if options['save'] and method_results:
                    save_file = save_results(method_results)
                    self.stdout.write(f"Detailed results saved to {save_file}")
                
                # Print table of results
                print("\nSUMMARY OF RESULTS:")
                print("-" * 100)
                print(f"{'Method':<40} {'Accuracy':<15} {'Confidence':<15} {'Time (s)':<15} {'Correct/Total'}")
                print("-" * 100)
                
                for name, data in method_results.items():
                    accuracy = data['evaluation']['accuracy'] * 100
                    confidence = data['evaluation']['avg_confidence']
                    time_taken = data['time']
                    correct = data['evaluation']['correct_count']
                    total = data['evaluation']['total_count']
                    
                    print(f"{name:<40} {accuracy:<15.2f} {confidence:<15.2f} {time_taken:<15.2f} {correct}/{total}")
                
                print("-" * 100)
            else:
                self.stdout.write("No valid results from any method")
            
        except Exception as e:
            self.stderr.write(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    pass 