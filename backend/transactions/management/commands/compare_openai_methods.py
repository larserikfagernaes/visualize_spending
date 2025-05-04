#!/usr/bin/env python3
import os
import sys
import json
import random
import time
from datetime import datetime
from collections import Counter, defaultdict
from django.core.management.base import BaseCommand
from dotenv import load_dotenv

# Set up environment
load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')

# Import Django after setting environment
import django
django.setup()

# Import models after Django setup
from transactions.models import Transaction, Supplier

# Import OpenAI
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Warning: OpenAI package not installed. Please install with 'pip install openai'")

# Try to import tiktoken
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    print("Note: tiktoken package not installed. Token counting will be estimated.")

# Constants
MAX_TOKENS = 100000
MAX_SUPPLIER_PROFILES = 50
MAX_PATTERNS_PER_SUPPLIER = 5

def estimate_tokens(text):
    """Estimate token count using tiktoken if available, or a simple heuristic."""
    if HAS_TIKTOKEN:
        enc = tiktoken.encoding_for_model("gpt-4-0125-preview")
        return len(enc.encode(text))
    else:
        # Fallback: ~4 characters per token on average
        return len(text) // 4

def create_test_set(test_size=20):
    """Create a test set of transactions with known suppliers."""
    print(f"Creating a test set of {test_size} transactions...")
    
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
        if len(txs) >= 2
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
    
    print(f"Created test set with {len(test_set)} transactions")
    print(f"Training set contains {len(training_set)} transactions")
    
    return test_set, training_set

def method1_basic_approach(training_set, test_transactions):
    """Method 1: Basic approach with just supplier names and descriptions."""
    # Group by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append({
            'description': tx['description']
        })

    # Create supplier profiles
    supplier_profiles = []
    for supplier_id, transactions in supplier_transactions.items():
        supplier_name = next((tx['supplier__name'] for tx in training_set 
                             if tx['supplier__id'] == supplier_id), f"Supplier {supplier_id}")
        
        profile = {
            'supplier_name': supplier_name,
            'description_patterns': list(set([tx['description'] for tx in transactions]))[:MAX_PATTERNS_PER_SUPPLIER]
        }
        supplier_profiles.append(profile)
    
    # Sort by number of patterns and limit
    supplier_profiles.sort(key=lambda x: len(x['description_patterns']), reverse=True)
    supplier_profiles = supplier_profiles[:MAX_SUPPLIER_PROFILES]
    
    # Format test transactions
    unmatched_list = [{
        "id": tx['id'],
        "description": tx['description']
    } for tx in test_transactions]
    
    # Define prompts
    system_prompt = """
You are a financial transaction classifier. Your task is to match bank transaction descriptions to the correct supplier based on patterns in the text.

You will receive:
1. SUPPLIER_PROFILES: List of suppliers with their typical transaction descriptions
2. UNMATCHED_TRANSACTIONS: New transactions that need classification

For each unmatched transaction:
1. Find the most likely supplier match based on the description patterns
2. Provide a confidence score based on pattern matching strength

Return results in JSON format with:
- transaction_id: The ID of the unmatched transaction
- best_match_supplier_name: The supplier name
- confidence_level: 0-100 score based on match strength
"""

    user_prompt = f"""
SUPPLIER_PROFILES (Known suppliers and their transaction patterns):
{json.dumps(supplier_profiles, indent=2)}

UNMATCHED_TRANSACTIONS (Transactions needing classification):
{json.dumps(unmatched_list, indent=2)}

Analyze each unmatched transaction and return a JSON array with your classifications.
"""

    return {
        'name': "Method 1: Basic Pattern Matching",
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'test_transactions': test_transactions
    }

def method2_word_analysis(training_set, test_transactions):
    """Method 2: Enhanced approach with word frequency analysis."""
    # Analyze description words
    all_descriptions = [tx['description'] for tx in training_set]
    word_frequencies = Counter()
    
    for desc in all_descriptions:
        words = desc.lower().split()
        word_frequencies.update(words)
    
    # Identify common words to exclude
    common_words = [word for word, count in word_frequencies.most_common(20) 
                   if count > len(training_set) / 10]
    
    # Group by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append({
            'description': tx['description']
        })

    # Create enhanced supplier profiles
    supplier_profiles = []
    for supplier_id, transactions in supplier_transactions.items():
        supplier_name = next((tx['supplier__name'] for tx in training_set 
                             if tx['supplier__id'] == supplier_id), f"Supplier {supplier_id}")
        
        # Extract unique descriptions
        descriptions = list(set([tx['description'] for tx in transactions]))
        
        # Extract key terms
        key_words = set()
        for desc in descriptions:
            words = desc.lower().split()
            # Filter out common words
            words = [w for w in words if w not in common_words]
            key_words.update(words)
        
        profile = {
            'supplier_name': supplier_name,
            'description_examples': descriptions[:MAX_PATTERNS_PER_SUPPLIER],
            'key_terms': list(key_words)[:10]  # Top 10 key terms
        }
        supplier_profiles.append(profile)
    
    # Sort by number of patterns and limit
    supplier_profiles.sort(key=lambda x: len(x['description_examples']), reverse=True)
    supplier_profiles = supplier_profiles[:MAX_SUPPLIER_PROFILES]
    
    # Format test transactions
    unmatched_list = [{
        "id": tx['id'],
        "description": tx['description']
    } for tx in test_transactions]
    
    # Define prompts
    system_prompt = """
You are a financial transaction classifier specializing in pattern recognition. Your task is to match bank transaction descriptions to suppliers by identifying distinctive patterns.

You will receive:
1. SUPPLIER_PROFILES: Suppliers with example descriptions and key terms
2. UNMATCHED_TRANSACTIONS: Transactions that need classification

For each unmatched transaction:
1. Analyze the text for distinctive patterns, business names, and key terms
2. Compare with the supplier profiles to find the best match
3. Consider partial matches, abbreviations, and business name variations
4. Assign confidence based on pattern distinctiveness

Return results in JSON format with:
- transaction_id: The ID of the unmatched transaction
- best_match_supplier_name: The supplier name
- confidence_level: 0-100 score based on match strength
"""

    user_prompt = f"""
SUPPLIER_PROFILES (Known suppliers with example descriptions and key terms):
{json.dumps(supplier_profiles, indent=2)}

UNMATCHED_TRANSACTIONS (Transactions needing classification):
{json.dumps(unmatched_list, indent=2)}

Analyze each unmatched transaction and return a JSON array with your classifications.
"""

    return {
        'name': "Method 2: Word Analysis & Pattern Recognition",
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'test_transactions': test_transactions
    }

def method3_few_shot_learning(training_set, test_transactions):
    """Method 3: Few-shot learning with examples."""
    # Group by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append({
            'description': tx['description'],
            'supplier_name': tx['supplier__name']
        })

    # Create examples for few-shot learning
    examples = []
    suppliers_used = set()
    
    for supplier_id, transactions in supplier_transactions.items():
        if len(transactions) >= 2 and supplier_id not in suppliers_used:
            # Get 2 transactions for this supplier
            example_txs = transactions[:2]
            
            # Create an example
            examples.append({
                "description": example_txs[0]['description'],
                "correct_supplier": example_txs[0]['supplier_name'],
                "reasoning": f"This matches the pattern of '{example_txs[0]['supplier_name']}' transactions"
            })
            
            suppliers_used.add(supplier_id)
            
            # Limit to 5 examples
            if len(examples) >= 5:
                break
    
    # Create supplier profiles
    supplier_profiles = []
    for supplier_id, transactions in supplier_transactions.items():
        if transactions:
            profile = {
                'supplier_name': transactions[0]['supplier_name'],
                'examples': list(set([tx['description'] for tx in transactions]))[:MAX_PATTERNS_PER_SUPPLIER]
            }
            supplier_profiles.append(profile)
    
    # Sort and limit
    supplier_profiles.sort(key=lambda x: len(x['examples']), reverse=True)
    supplier_profiles = supplier_profiles[:MAX_SUPPLIER_PROFILES]
    
    # Format test transactions
    unmatched_list = [{
        "id": tx['id'],
        "description": tx['description']
    } for tx in test_transactions]
    
    # Define prompts
    system_prompt = """
You are a financial transaction classifier. Your task is to match each bank transaction to the correct supplier based on the description text.

I'll provide you with examples of how to match transactions, along with a list of known suppliers and their typical transactions. Use these to classify the new transactions.
"""

    user_prompt = f"""
Here are examples of how to match transactions:

EXAMPLES:
{json.dumps(examples, indent=2)}

KNOWN SUPPLIERS:
{json.dumps(supplier_profiles, indent=2)}

TRANSACTIONS TO CLASSIFY:
{json.dumps(unmatched_list, indent=2)}

For each transaction, determine the most likely supplier match. Return your analysis as a JSON array with this format:
[
  {{
    "transaction_id": [ID],
    "best_match_supplier_name": [SUPPLIER NAME],
    "confidence_level": [0-100]
  }}
]
"""

    return {
        'name': "Method 3: Few-shot Learning",
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'test_transactions': test_transactions
    }

def process_with_openai(method_data):
    """Call OpenAI API with the specified method data."""
    if not HAS_OPENAI:
        raise ImportError("OpenAI package is required but not installed.")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    client = OpenAI(api_key=api_key)
    
    # Get prompts and data
    method_name = method_data['name']
    system_prompt = method_data['system_prompt']
    user_prompt = method_data['user_prompt']
    test_transactions = method_data['test_transactions']
    
    # Token estimates
    system_tokens = estimate_tokens(system_prompt)
    user_tokens = estimate_tokens(user_prompt)
    total_tokens = system_tokens + user_tokens
    
    print(f"\nProcessing with {method_name}")
    print(f"Token estimates: System: {system_tokens}, User: {user_tokens}, Total: {total_tokens}")
    
    if total_tokens > MAX_TOKENS * 0.8:
        print(f"WARNING: Prompt exceeds recommended token limit. Results may be affected.")
    
    try:
        print(f"Calling OpenAI API...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=4000,
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Extract and parse response
        response_text = response.choices[0].message.content
        
        try:
            # Find JSON part in response
            start_index = response_text.find('[')
            end_index = response_text.rfind(']') + 1
            
            if start_index >= 0 and end_index > start_index:
                json_str = response_text[start_index:end_index]
                results = json.loads(json_str)
                
                return {
                    'results': results,
                    'time': duration,
                    'tokens_in': total_tokens,
                    'tokens_out': estimate_tokens(response_text)
                }
            else:
                raise ValueError("Could not find JSON in response")
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            print(f"Response was: {response_text}")
            return None
            
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def evaluate_results(results, test_transactions):
    """Evaluate matching results against truth data."""
    if not results:
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
    
    for result in results:
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

def print_evaluation(method_name, evaluation, processing_info=None):
    """Print formatted evaluation results."""
    print("\n" + "=" * 80)
    print(f"RESULTS FOR: {method_name}")
    print("=" * 80)
    
    print(f"ACCURACY: {evaluation['accuracy'] * 100:.2f}%")
    print(f"CORRECT: {evaluation['correct_count']} / {evaluation['total_count']}")
    print(f"AVG CONFIDENCE: {evaluation['avg_confidence']:.2f}")
    
    if processing_info:
        print(f"PROCESSING TIME: {processing_info['time']:.2f} seconds")
        print(f"TOKENS IN: {processing_info['tokens_in']}")
        print(f"TOKENS OUT: {processing_info['tokens_out']}")
    
    print("\nDETAILED RESULTS:")
    print("-" * 80)
    
    for detail in evaluation['details']:
        status = "✓" if detail['correct'] else "✗"
        print(f"{status} ID: {detail['transaction_id']}")
        print(f"  Description: {detail['description'][:80]}...")
        print(f"  True: {detail['true_supplier']}")
        print(f"  Predicted: {detail['predicted_supplier']} (Confidence: {detail['confidence']})")
        print("-" * 40)
    
    print("=" * 80)

def save_results(method_results):
    """Save test results to file for later analysis."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = "method_comparison_results"
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
            'processing_time': data['processing']['time'],
            'tokens_in': data['processing']['tokens_in'],
            'tokens_out': data['processing']['tokens_out'],
            'details': data['evaluation']['details']
        }
    
    with open(filename, 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print(f"\nResults saved to {filename}")
    return filename

class Command(BaseCommand):
    help = 'Compare different OpenAI prompting methods for transaction supplier matching'

    def add_arguments(self, parser):
        parser.add_argument('--test-size', type=int, default=100,
                           help='Number of transactions to use for testing (default: 10)')
        parser.add_argument('--method', type=int, choices=[1, 2, 3],
                           help='Test only a specific method (1, 2, or 3)')
        parser.add_argument('--save', action='store_true',
                           help='Save detailed results to file')

    def handle(self, *args, **options):
        try:
            # Check for OpenAI
            if not HAS_OPENAI:
                self.stderr.write("OpenAI package is required. Please install with 'pip install openai'")
                return
                
            # Check for API key
            if not os.getenv("OPENAI_API_KEY"):
                self.stderr.write("OPENAI_API_KEY environment variable must be set.")
                return
            
            test_size = options['test_size']
            self.stdout.write(f"Running comparison with {test_size} test transactions")
            
            # Create test set
            test_set, training_set = create_test_set(test_size)
            
            # Determine which methods to test
            methods_to_test = []
            if options['method']:
                methods_to_test = [options['method']]
            else:
                methods_to_test = [1, 2, 3]  # Test all methods
            
            # Prepare methods
            method_data = {}
            if 1 in methods_to_test:
                method_data[1] = method1_basic_approach(training_set, test_set)
            if 2 in methods_to_test:
                method_data[2] = method2_word_analysis(training_set, test_set)
            if 3 in methods_to_test:
                method_data[3] = method3_few_shot_learning(training_set, test_set)
            
            # Process with OpenAI and evaluate
            method_results = {}
            
            for method_id, data in method_data.items():
                self.stdout.write(f"\nTesting {data['name']}...")
                
                # Call API
                results = process_with_openai(data)
                
                if results:
                    # Evaluate results
                    evaluation = evaluate_results(results['results'], test_set)
                    
                    # Store results
                    method_results[data['name']] = {
                        'processing': results,
                        'evaluation': evaluation
                    }
                    
                    # Print evaluation
                    print_evaluation(data['name'], evaluation, results)
                else:
                    self.stdout.write(f"No valid results for {data['name']}")
            
            # Determine best method
            if method_results:
                # Find method with highest accuracy
                best_method = max(method_results.items(), 
                                 key=lambda x: x[1]['evaluation']['accuracy'])
                
                self.stdout.write(f"\n\nBEST METHOD: {best_method[0]}")
                self.stdout.write(f"ACCURACY: {best_method[1]['evaluation']['accuracy'] * 100:.2f}%")
                
                # Save results if requested
                if options['save'] and method_results:
                    save_file = save_results(method_results)
                    self.stdout.write(f"Detailed results saved to {save_file}")
                
                # Recommend method for production
                if best_method[0] == "Method 1: Basic Pattern Matching":
                    self.stdout.write("Recommendation: Use the basic pattern matching approach")
                elif best_method[0] == "Method 2: Word Analysis & Pattern Recognition":
                    self.stdout.write("Recommendation: Use the word analysis and pattern recognition approach")
                elif best_method[0] == "Method 3: Few-shot Learning":
                    self.stdout.write("Recommendation: Use the few-shot learning approach")
            else:
                self.stdout.write("No valid results from any method")
            
        except Exception as e:
            self.stderr.write(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    pass 