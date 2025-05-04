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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')

# Import Django after setting environment
import django
django.setup()

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

# Import Django models after setup
from transactions.models import Transaction, Supplier, Category, CategorySupplierMap

# Import OpenAI
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Warning: OpenAI package not installed. Please install with 'pip install openai'")

# Try to import tiktoken but don't require it
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    print("Note: tiktoken package not installed. Token counting will be estimated.")

# Maximum tokens for context (for GPT-4 Turbo)
MAX_TOKENS = 100000
MAX_SUPPLIER_PROFILES = 100
MAX_PATTERNS_PER_SUPPLIER = 5
TEST_SET_SIZE = 100

def get_api_client():
    """Initialize and return the OpenAI API client."""
    global api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    return OpenAI(api_key=api_key)

def estimate_tokens(text):
    """Estimate token count for the text using tiktoken if available, otherwise use a simple heuristic."""
    if HAS_TIKTOKEN:
        # Use proper tokenization with tiktoken
        enc = tiktoken.encoding_for_model("gpt-4-0125-preview")
        return len(enc.encode(text))
    else:
        # Fallback to a simple estimate: ~4 characters per token on average
        return len(text) // 4

def create_test_set():
    """Create a test set of transactions with known suppliers."""
    # Get all transactions with suppliers and group by supplier
    all_matched = Transaction.objects.filter(
        supplier__isnull=False
    ).select_related('supplier').values(
        'id', 'description', 'supplier__name', 'supplier__id'
    )
    
    # Group by supplier
    supplier_transactions = defaultdict(list)
    for tx in all_matched:
        supplier_transactions[tx['supplier__id']].append(tx)
    
    # Get suppliers with at least 2 transactions (so we can use 1 for testing)
    eligible_suppliers = [
        supplier_id for supplier_id, txs in supplier_transactions.items()
        if len(txs) >= 2
    ]
    
    # Randomly select suppliers and take 1 transaction from each for testing
    test_set = []
    training_set = []
    
    if len(eligible_suppliers) >= TEST_SET_SIZE:
        # If we have enough suppliers, take one transaction from each
        selected_suppliers = random.sample(eligible_suppliers, TEST_SET_SIZE)
        
        for supplier_id in eligible_suppliers:
            txs = supplier_transactions[supplier_id]
            
            if supplier_id in selected_suppliers:
                # Add one random transaction to test set
                test_tx = random.choice(txs)
                test_set.append(test_tx)
                
                # Add remaining transactions to training set
                for tx in txs:
                    if tx['id'] != test_tx['id']:
                        training_set.append(tx)
            else:
                # Add all transactions to training set
                training_set.extend(txs)
    else:
        # If we don't have enough suppliers, take multiple from the same suppliers
        needed = TEST_SET_SIZE
        
        for supplier_id in eligible_suppliers:
            txs = supplier_transactions[supplier_id]
            
            # Determine how many we need from this supplier
            to_take = min(needed, len(txs) // 2)  # Take at most half
            if to_take == 0:
                to_take = 1
            
            # Randomly select transactions for test set
            test_txs = random.sample(txs, to_take)
            needed -= to_take
            
            # Add to test set
            for tx in test_txs:
                test_set.append(tx)
            
            # Add remaining to training set
            for tx in txs:
                if tx not in test_txs:
                    training_set.append(tx)
                    
            if needed <= 0:
                break
    
    print(f"Created test set of {len(test_set)} transactions")
    print(f"Training set contains {len(training_set)} transactions")
    
    return test_set, training_set

def prepare_method1(training_set, test_transactions):
    """
    Method 1: Basic approach - Just supplier names and descriptions
    """
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append({
            'description': tx['description']
        })

    # Create supplier profiles
    supplier_profiles = []
    for supplier_id, transactions in supplier_transactions.items():
        profile = {
            'supplier_name': transactions[0]['supplier_name'] if 'supplier_name' in transactions[0] else 
                          training_set[0]['supplier__name'] if training_set and supplier_id == training_set[0]['supplier__id'] else 
                          f"Supplier {supplier_id}",
            'description_patterns': list(set([tx['description'] for tx in transactions]))[:MAX_PATTERNS_PER_SUPPLIER]
        }
        supplier_profiles.append(profile)
    
    # Sort profiles by number of patterns and limit the number
    supplier_profiles.sort(key=lambda x: len(x['description_patterns']), reverse=True)
    supplier_profiles = supplier_profiles[:MAX_SUPPLIER_PROFILES]
    
    # Prepare test transactions
    unmatched_list = [{
        "id": tx['id'],
        "description": tx['description']
    } for tx in test_transactions]
    
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
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'test_transactions': test_transactions
    }

def prepare_method2(training_set, test_transactions):
    """
    Method 2: Enhanced approach - Include word frequencies and pattern extraction
    """
    # Analyze all descriptions to identify common patterns
    all_descriptions = [tx['description'] for tx in training_set]
    word_frequencies = Counter()
    
    # Extract words from descriptions
    for desc in all_descriptions:
        words = desc.lower().split()
        word_frequencies.update(words)
    
    # Get common words (to potentially exclude)
    common_words = [word for word, count in word_frequencies.most_common(20) if count > len(training_set) / 10]
    
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append({
            'description': tx['description']
        })

    # Create supplier profiles with enhanced pattern extraction
    supplier_profiles = []
    for supplier_id, transactions in supplier_transactions.items():
        # Extract unique descriptions
        descriptions = list(set([tx['description'] for tx in transactions]))
        
        # Extract key patterns
        key_words = set()
        for desc in descriptions:
            words = desc.lower().split()
            # Filter out very common words
            words = [w for w in words if w not in common_words]
            key_words.update(words)
        
        profile = {
            'supplier_name': transactions[0]['supplier_name'] if 'supplier_name' in transactions[0] else 
                          training_set[0]['supplier__name'] if training_set and supplier_id == training_set[0]['supplier__id'] else 
                          f"Supplier {supplier_id}",
            'description_examples': descriptions[:MAX_PATTERNS_PER_SUPPLIER],
            'key_terms': list(key_words)[:10]  # Top 10 key terms
        }
        supplier_profiles.append(profile)
    
    # Sort profiles and limit the number
    supplier_profiles.sort(key=lambda x: len(x['description_examples']), reverse=True)
    supplier_profiles = supplier_profiles[:MAX_SUPPLIER_PROFILES]
    
    # Prepare test transactions
    unmatched_list = [{
        "id": tx['id'],
        "description": tx['description']
    } for tx in test_transactions]
    
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
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'test_transactions': test_transactions
    }

def prepare_method3(training_set, test_transactions):
    """
    Method 3: Few-shot learning approach with explicit examples
    """
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append({
            'description': tx['description'],
            'supplier_name': tx['supplier__name']
        })

    # Create examples of successful matches
    examples = []
    suppliers_used = set()
    
    for supplier_id, transactions in supplier_transactions.items():
        if len(transactions) >= 2 and supplier_id not in suppliers_used:
            # Get 2 transactions for this supplier
            example_txs = transactions[:2]
            
            # Add example
            examples.append({
                "description": example_txs[0]['description'],
                "correct_supplier": example_txs[0]['supplier_name'],
                "reasoning": f"This matches the pattern of '{example_txs[0]['supplier_name']}' transactions"
            })
            
            suppliers_used.add(supplier_id)
            
            if len(examples) >= 5:  # Limit to 5 examples
                break
    
    # Create a simplified list of suppliers and their descriptions
    supplier_profiles = []
    for supplier_id, transactions in supplier_transactions.items():
        profile = {
            'supplier_name': transactions[0]['supplier_name'],
            'examples': list(set([tx['description'] for tx in transactions]))[:MAX_PATTERNS_PER_SUPPLIER]
        }
        supplier_profiles.append(profile)
    
    # Sort profiles and limit the number
    supplier_profiles.sort(key=lambda x: len(x['examples']), reverse=True)
    supplier_profiles = supplier_profiles[:MAX_SUPPLIER_PROFILES]
    
    # Prepare test transactions
    unmatched_list = [{
        "id": tx['id'],
        "description": tx['description']
    } for tx in test_transactions]
    
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
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'test_transactions': test_transactions
    }

def prepare_method4(training_set, test_transactions):
    """
    Method 4: Feature extraction and tokenization approach
    """
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append({
            'description': tx['description']
        })

    # Create supplier profiles with extracted features
    supplier_profiles = []
    for supplier_id, transactions in supplier_transactions.items():
        supplier_name = transactions[0]['supplier_name'] if 'supplier_name' in transactions[0] else \
                       next((tx['supplier__name'] for tx in training_set if tx['supplier__id'] == supplier_id), f"Supplier {supplier_id}")
        
        # Extract features from descriptions
        all_descriptions = list(set([tx['description'] for tx in transactions]))
        
        # Extract identifying tokens
        tokens = []
        prefixes = []
        numbers = []
        patterns = []
        
        for desc in all_descriptions:
            # Extract tokens (words)
            words = desc.lower().split()
            tokens.extend(words)
            
            # Extract prefixes (first few characters)
            if len(desc) > 3:
                prefixes.append(desc[:4].lower())
            
            # Extract numbers
            import re
            nums = re.findall(r'\d+', desc)
            if nums:
                numbers.extend(nums)
            
            # Look for patterns like XXX-XXX, reference codes
            patterns_found = re.findall(r'[A-Z0-9]{3,}[-\s][A-Z0-9]{3,}', desc)
            if patterns_found:
                patterns.extend(patterns_found)
        
        # Count token frequencies
        token_freq = Counter(tokens)
        most_common_tokens = [token for token, count in token_freq.most_common(5)]
        
        # Build profile
        profile = {
            'supplier_name': supplier_name,
            'examples': all_descriptions[:MAX_PATTERNS_PER_SUPPLIER],
            'identifying_tokens': most_common_tokens,
            'common_prefixes': list(set(prefixes))[:3],
            'number_patterns': list(set(numbers))[:3],
            'special_patterns': list(set(patterns))[:3]
        }
        supplier_profiles.append(profile)
    
    # Sort profiles and limit the number
    supplier_profiles.sort(key=lambda x: len(x['examples']), reverse=True)
    supplier_profiles = supplier_profiles[:MAX_SUPPLIER_PROFILES]
    
    # Prepare test transactions
    unmatched_list = [{
        "id": tx['id'],
        "description": tx['description']
    } for tx in test_transactions]
    
    system_prompt = """
You are an advanced financial transaction classifier specialized in natural language processing. Your task is to match bank transactions to the correct suppliers by analyzing various text features.

You'll receive:
1. SUPPLIER PROFILES with multiple feature sets:
   - Example descriptions
   - Identifying tokens (key words)
   - Common text prefixes
   - Number patterns
   - Special format patterns

2. UNMATCHED TRANSACTIONS that need classification

Apply this feature-based matching process:
1. Tokenize each transaction description
2. Extract features (tokens, prefixes, numbers, patterns)
3. Calculate similarity scores with each supplier profile
4. Select the supplier with highest feature overlap
5. Assign confidence based on feature match quality

Remember that different feature types have different weights:
- Exact pattern matches are strongest
- Special format patterns are very indicative
- Numbers can be important identifiers
- Common words have less discriminative power

Return a JSON array with your matches, following this format:
[
  {
    "transaction_id": 123,
    "best_match_supplier_name": "Example Supplier",
    "confidence_level": 85
  },
  ...
]
"""

    user_prompt = f"""
SUPPLIER PROFILES (with feature sets):
{json.dumps(supplier_profiles, indent=2)}

UNMATCHED TRANSACTIONS:
{json.dumps(unmatched_list, indent=2)}

Analyze the unmatched transactions using the feature-based approach. For each transaction, determine the best supplier match and return your results as a JSON array.
"""
    
    return {
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'test_transactions': test_transactions
    }

def prepare_method5(training_set, test_transactions):
    """
    Method 5: Chain-of-thought reasoning approach
    """
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append({
            'description': tx['description'],
            'supplier_name': tx['supplier__name']
        })

    # Create detailed supplier profiles
    supplier_profiles = []
    for supplier_id, transactions in supplier_transactions.items():
        if not transactions:
            continue
            
        # Get all descriptions for this supplier
        descriptions = list(set([tx['description'] for tx in transactions]))
        
        # Create a profile
        profile = {
            'supplier_name': transactions[0]['supplier_name'],
            'transaction_patterns': descriptions[:MAX_PATTERNS_PER_SUPPLIER]
        }
        supplier_profiles.append(profile)
    
    # Sort and limit supplier profiles
    supplier_profiles.sort(key=lambda x: len(x['transaction_patterns']), reverse=True)
    supplier_profiles = supplier_profiles[:MAX_SUPPLIER_PROFILES]
    
    # Prepare test transactions
    unmatched_list = [{
        "id": tx['id'],
        "description": tx['description']
    } for tx in test_transactions]
    
    # Create detailed examples with reasoning
    examples = []
    suppliers_used = set()
    
    for supplier_id, transactions in supplier_transactions.items():
        if len(transactions) >= 2 and supplier_id not in suppliers_used:
            example_tx = transactions[0]
            
            # Create a chain-of-thought example
            examples.append({
                "transaction": {
                    "id": "example-1",
                    "description": example_tx['description']
                },
                "reasoning_steps": [
                    "1. I'll analyze the key elements in this description: \"" + example_tx['description'] + "\"",
                    "2. Looking for business names, location indicators, or service patterns",
                    f"3. This description has patterns consistent with {example_tx['supplier_name']} transactions",
                    f"4. Comparing to known suppliers, this is likely a {example_tx['supplier_name']} transaction"
                ],
                "conclusion": {
                    "best_match_supplier_name": example_tx['supplier_name'],
                    "confidence_level": 90
                }
            })
            
            suppliers_used.add(supplier_id)
            
            if len(examples) >= 3:  # Limit to 3 examples to save tokens
                break
    
    system_prompt = """
You are a financial transaction analysis expert using chain-of-thought reasoning to match bank transactions to suppliers.

For each transaction, you'll carefully analyze the description and determine the most likely supplier by working through a systematic reasoning process.
"""

    user_prompt = f"""
I'll show you some examples of how to reason about transaction matching:

EXAMPLES (with detailed reasoning):
{json.dumps(examples, indent=2)}

KNOWN SUPPLIERS:
{json.dumps(supplier_profiles, indent=2)}

TRANSACTIONS TO CLASSIFY:
{json.dumps(unmatched_list, indent=2)}

For each unmatched transaction, follow these steps:
1. Analyze the description carefully
2. Break down key elements (business names, services, patterns)
3. Compare with known supplier patterns
4. Identify the most likely supplier match
5. Assign a confidence level based on match quality

Return your analysis as a JSON array in this format:
[
  {{
    "transaction_id": [ID],
    "best_match_supplier_name": [SUPPLIER NAME],
    "confidence_level": [0-100]
  }}
]
"""
    
    return {
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'test_transactions': test_transactions
    }

def prepare_method6(training_set, test_transactions):
    """
    Method 6: Similarity-based approach with reference vectors
    """
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append({
            'description': tx['description']
        })

    # Create reference vectors (simplified representation) for each supplier
    reference_vectors = []
    
    for supplier_id, transactions in supplier_transactions.items():
        # Get supplier name
        supplier_name = transactions[0]['supplier_name'] if 'supplier_name' in transactions[0] else \
                       next((tx['supplier__name'] for tx in training_set if tx['supplier__id'] == supplier_id), f"Supplier {supplier_id}")
        
        # Get unique descriptions
        descriptions = list(set([tx['description'] for tx in transactions]))[:MAX_PATTERNS_PER_SUPPLIER]
        
        # Extract distinctive word sets
        all_words = []
        for desc in descriptions:
            # Simple preprocessing - lowercase and split
            words = set(word.lower() for word in desc.split())
            all_words.append(words)
        
        # Find words that appear in multiple descriptions
        common_words = set()
        if len(all_words) > 1:
            for i, words1 in enumerate(all_words[:-1]):
                for words2 in all_words[i+1:]:
                    common_words.update(words1.intersection(words2))
        elif len(all_words) == 1:
            common_words = all_words[0]
        
        # Create vector reference
        vector = {
            'supplier_name': supplier_name,
            'examples': descriptions,
            'distinctive_words': list(common_words)[:10],  # Top 10 distinctive words
            'word_weights': {word: 1.0 for word in common_words}  # Simple weighting for now
        }
        
        reference_vectors.append(vector)
    
    # Sort and limit reference vectors
    reference_vectors.sort(key=lambda x: len(x['examples']), reverse=True)
    reference_vectors = reference_vectors[:MAX_SUPPLIER_PROFILES]
    
    # Prepare test transactions
    unmatched_list = [{
        "id": tx['id'],
        "description": tx['description']
    } for tx in test_transactions]
    
    system_prompt = """
You are an AI specializing in semantic text matching and vector similarity analysis. Your task is to match bank transactions to suppliers using a similarity-based approach.

You'll be given:
1. REFERENCE VECTORS for each supplier, containing:
   - Example transaction descriptions
   - Distinctive words that characterize this supplier
   - Word importance weights

2. UNMATCHED TRANSACTIONS to classify

For each transaction, follow this similarity-matching process:
1. Create a semantic representation of the transaction description
2. Calculate similarity scores with each supplier's reference vector
   - Consider word overlap
   - Consider word weights
   - Consider semantic similarity
3. Assign the transaction to the supplier with highest similarity score
4. Calculate confidence level based on similarity strength

IMPORTANT: Think of this as finding the closest semantic match between the unmatched transaction and the supplier references.
"""

    user_prompt = f"""
REFERENCE VECTORS:
{json.dumps(reference_vectors, indent=2)}

UNMATCHED TRANSACTIONS:
{json.dumps(unmatched_list, indent=2)}

For each unmatched transaction, find the most semantically similar supplier. Return your classifications as a JSON array with this format:
[
  {{
    "transaction_id": [ID],
    "best_match_supplier_name": [SUPPLIER NAME],
    "confidence_level": [0-100]
  }}
]
"""
    
    return {
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'test_transactions': test_transactions
    }

def prepare_method7(training_set, test_transactions):
    """
    Method 7: Combined chain-of-thought reasoning with vector similarity approach
    """
    # Group training transactions by supplier
    supplier_transactions = defaultdict(list)
    for tx in training_set:
        supplier_transactions[tx['supplier__id']].append({
            'description': tx['description'],
            'supplier_name': tx['supplier__name']
        })

    # Create detailed supplier profiles with semantic vectors
    supplier_profiles = []
    for supplier_id, transactions in supplier_transactions.items():
        if not transactions:
            continue
            
        # Get unique descriptions
        descriptions = list(set([tx['description'] for tx in transactions]))[:MAX_PATTERNS_PER_SUPPLIER]
        
        # Extract distinctive word sets
        all_words = []
        for desc in descriptions:
            # Simple preprocessing - lowercase and split
            words = set(word.lower() for word in desc.split())
            all_words.append(words)
        
        # Find words that appear in multiple descriptions
        common_words = set()
        if len(all_words) > 1:
            for i, words1 in enumerate(all_words[:-1]):
                for words2 in all_words[i+1:]:
                    common_words.update(words1.intersection(words2))
        elif len(all_words) == 1:
            common_words = all_words[0]
        
        # Build profile with combined approach
        profile = {
            'supplier_name': transactions[0]['supplier_name'],
            'transaction_examples': descriptions[:MAX_PATTERNS_PER_SUPPLIER],
            'key_patterns': list(common_words)[:10],  # Top 10 key words
            'typical_markers': []  # We'll extract these below
        }
        
        # Extract typical patterns/markers
        all_text = " ".join(descriptions).lower()
        
        # Look for common prefixes, payment processors, reference numbers, etc.
        if 'visa vare' in all_text:
            profile['typical_markers'].append('VISA payment')
        if 'nok' in all_text:
            profile['typical_markers'].append('Norwegian currency')
        if 'usd' in all_text:
            profile['typical_markers'].append('US Dollar currency')
        if 'eur' in all_text:
            profile['typical_markers'].append('Euro currency')
        if 'gbp' in all_text:
            profile['typical_markers'].append('British Pound currency')
        if 'kurs' in all_text:
            profile['typical_markers'].append('Currency exchange')
        if 'debit card' in all_text:
            profile['typical_markers'].append('Debit card purchase')
        if '00giro' in all_text:
            profile['typical_markers'].append('Giro payment')
        
        supplier_profiles.append(profile)
    
    # Sort profiles and limit the number
    supplier_profiles.sort(key=lambda x: len(x['transaction_examples']), reverse=True)
    supplier_profiles = supplier_profiles[:MAX_SUPPLIER_PROFILES]
    
    # Create examples with detailed reasoning for chain-of-thought approach
    examples = []
    suppliers_used = set()
    
    for supplier_id, transactions in supplier_transactions.items():
        if len(transactions) >= 2 and supplier_id not in suppliers_used and len(examples) < 3:
            example_tx = transactions[0]
            supplier_name = example_tx['supplier_name']
            
            # Get the profile for this supplier
            supplier_profile = next((p for p in supplier_profiles if p['supplier_name'] == supplier_name), None)
            if not supplier_profile:
                continue
                
            # Extract key features from description
            description = example_tx['description']
            key_features = []
            
            # Add important tokens
            tokens = description.lower().split()
            for key_pattern in supplier_profile['key_patterns']:
                if key_pattern in tokens:
                    key_features.append(f"Contains key token '{key_pattern}'")
            
            # Add pattern matches
            for marker in supplier_profile['typical_markers']:
                key_features.append(f"Matches pattern '{marker}'")
                
            # Add similarity to examples
            key_features.append(f"Similar to other {supplier_name} transactions")
            
            # Create reasoning example
            examples.append({
                "transaction": {
                    "id": "example-1",
                    "description": description
                },
                "analysis": {
                    "semantic_features": key_features[:3],
                    "pattern_matching": f"Description contains distinctive elements of {supplier_name} transactions",
                    "vector_similarity": "High lexical and semantic similarity to reference transactions"
                },
                "conclusion": {
                    "best_match_supplier_name": supplier_name,
                    "confidence_level": 90,
                    "reasoning": f"Strong pattern and semantic vector match with {supplier_name} transactions"
                }
            })
            
            suppliers_used.add(supplier_id)
    
    # Prepare test transactions
    unmatched_list = [{
        "id": tx['id'],
        "description": tx['description']
    } for tx in test_transactions]
    
    system_prompt = """
You are a financial transaction classifier that combines advanced semantic analysis with chain-of-thought reasoning. Your task is to match bank transaction descriptions to the correct suppliers.

You use a hybrid approach that combines:
1. Semantic vector similarity analysis
2. Pattern recognition and feature extraction
3. Chain-of-thought reasoning to explain your matching process

This combined approach achieves higher accuracy than using any single method alone.
"""

    user_prompt = f"""
I'll show you examples of how to analyze transactions using the combined approach:

EXAMPLES (with detailed analysis):
{json.dumps(examples, indent=2)}

SUPPLIER PROFILES (with transaction examples and semantic features):
{json.dumps(supplier_profiles, indent=2)}

TRANSACTIONS TO CLASSIFY:
{json.dumps(unmatched_list, indent=2)}

For each unmatched transaction, follow this hybrid analysis process:
1. Extract key semantic features from the description
2. Calculate vector similarity with each supplier profile
3. Look for distinctive patterns and markers
4. Use chain-of-thought reasoning to identify the best match
5. Assign a confidence score based on the strength of evidence

Return your classifications as a JSON array with this format:
[
  {{
    "transaction_id": [ID],
    "best_match_supplier_name": [SUPPLIER NAME], 
    "confidence_level": [0-100]
  }}
]
"""
    
    return {
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'test_transactions': test_transactions
    }

def process_with_openai(method_data, method_name):
    """Process test transactions using OpenAI API for a given method."""
    if not HAS_OPENAI:
        raise ImportError("OpenAI package is required but not installed.")
    
    client = get_api_client()
    
    system_prompt = method_data['system_prompt']
    user_prompt = method_data['user_prompt']
    test_transactions = method_data['test_transactions']
    
    # Print token estimates
    system_tokens = estimate_tokens(system_prompt)
    user_tokens = estimate_tokens(user_prompt)
    total_tokens = system_tokens + user_tokens
    print(f"\nToken estimates for {method_name}: System: {system_tokens}, User: {user_tokens}, Total: {total_tokens}")
    
    if total_tokens > MAX_TOKENS * 0.8:
        print(f"WARNING: Prompt for {method_name} exceeds recommended token limit. Skipping.")
        return None
    
    # Print the prompts
    print(f"\nSystem Prompt for {method_name}:")
    print("=" * 80)
    print(system_prompt)
    print(f"\nUser Prompt for {method_name}:")
    print("=" * 80)
    print(user_prompt)
    print("=" * 80)
    
    try:
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
        
        # Extract the response content
        response_text = response.choices[0].message.content
        
        # Parse the JSON response
        try:
            start_index = response_text.find('[')
            end_index = response_text.rfind(']') + 1
            if start_index >= 0 and end_index > start_index:
                json_str = response_text[start_index:end_index]
                results = json.loads(json_str)
                return {
                    'results': results,
                    'time': end_time - start_time,
                    'tokens': total_tokens
                }
            else:
                raise ValueError("Could not find valid JSON in response")
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response for {method_name}: {e}")
            print(f"Response was: {response_text}")
            return None
            
    except Exception as e:
        print(f"Error calling OpenAI API for {method_name}: {e}")
        return None

def evaluate_results(results, test_transactions):
    """Evaluate the matching results against the true labels."""
    if not results:
        return {
            'accuracy': 0,
            'avg_confidence': 0,
            'correct_count': 0,
            'total_count': len(test_transactions)
        }
    
    correct_count = 0
    confidences = []
    
    # Create a map of transaction IDs to true suppliers
    true_suppliers = {tx['id']: tx['supplier__name'] for tx in test_transactions}
    
    for result in results:
        tx_id = result.get('transaction_id')
        predicted_supplier = result.get('best_match_supplier_name')
        confidence = result.get('confidence_level', 0)
        
        # Skip if transaction not found
        if tx_id not in true_suppliers:
            continue
        
        true_supplier = true_suppliers[tx_id]
        
        # Check if prediction is correct
        if predicted_supplier == true_supplier:
            correct_count += 1
        
        confidences.append(confidence)
    
    # Calculate metrics
    accuracy = correct_count / len(test_transactions) if test_transactions else 0
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    return {
        'accuracy': accuracy,
        'avg_confidence': avg_confidence,
        'correct_count': correct_count,
        'total_count': len(test_transactions)
    }

def print_evaluation(evaluation, method_name, process_time=None, token_count=None):
    """Print the evaluation results in a formatted way."""
    print("\n" + "=" * 80)
    print(f"Results for {method_name}")
    print("=" * 80)
    print(f"Accuracy: {evaluation['accuracy'] * 100:.2f}%")
    print(f"Correct matches: {evaluation['correct_count']} / {evaluation['total_count']}")
    print(f"Average confidence: {evaluation['avg_confidence']:.2f}")
    
    if process_time:
        print(f"Processing time: {process_time:.2f} seconds")
    
    if token_count:
        print(f"Token usage: {token_count} tokens")
    
    print("=" * 80)

class Command(BaseCommand):
    help = 'Test different prompting methods for OpenAI supplier matching on a test set.'
    
    def add_arguments(self, parser):
        parser.add_argument('--test-size', type=int, default=TEST_SET_SIZE,
                          help=f'Size of the test set (default: {TEST_SET_SIZE})')
        parser.add_argument('--save-prompts', action='store_true',
                          help='Save prompts to files without making API calls')
        parser.add_argument('--method', type=int, choices=[1, 2, 3, 4, 5, 6, 7], default=None,
                          help='Test only a specific method (1, 2, 3, 4, 5, 6, or 7)')
    
    def handle(self, *args, **options):
        try:
            # Check for OpenAI package
            if not HAS_OPENAI and not options['save_prompts']:
                self.stderr.write("OpenAI package is required but not installed. Please install with 'pip install openai'")
                return
                
            # Check for API key only if not in save-prompts mode
            if not options['save_prompts'] and not os.getenv("OPENAI_API_KEY"):
                self.stderr.write("OPENAI_API_KEY environment variable must be set.")
                return
            
            # Set test set size
            global TEST_SET_SIZE
            TEST_SET_SIZE = options['test_size']
            
            # Create test set
            self.stdout.write("Creating test set...")
            test_set, training_set = create_test_set()
            
            # Determine which methods to test
            methods_to_test = []
            if options['method'] is not None:
                methods_to_test = [options['method']]
            else:
                methods_to_test = [1, 2, 3, 4, 5, 6, 7]  # Test all methods
            
            method_data = {}
            method_results = {}
            
            # Prepare data for selected methods
            for method in methods_to_test:
                if method == 1:
                    self.stdout.write("Preparing data for Method 1...")
                    method_data[1] = prepare_method1(training_set, test_set)
                elif method == 2:
                    self.stdout.write("Preparing data for Method 2...")
                    method_data[2] = prepare_method2(training_set, test_set)
                elif method == 3:
                    self.stdout.write("Preparing data for Method 3...")
                    method_data[3] = prepare_method3(training_set, test_set)
                elif method == 4:
                    self.stdout.write("Preparing data for Method 4...")
                    method_data[4] = prepare_method4(training_set, test_set)
                elif method == 5:
                    self.stdout.write("Preparing data for Method 5...")
                    method_data[5] = prepare_method5(training_set, test_set)
                elif method == 6:
                    self.stdout.write("Preparing data for Method 6...")
                    method_data[6] = prepare_method6(training_set, test_set)
                elif method == 7:
                    self.stdout.write("Preparing data for Method 7...")
                    method_data[7] = prepare_method7(training_set, test_set)
            
            # Save prompts if requested
            if options['save_prompts']:
                os.makedirs('prompt_tests', exist_ok=True)
                for method in methods_to_test:
                    method_name = f"Method{method}"
                    with open(f"prompt_tests/{method_name}_system_prompt.txt", 'w') as f:
                        f.write(method_data[method]['system_prompt'])
                    with open(f"prompt_tests/{method_name}_user_prompt.txt", 'w') as f:
                        f.write(method_data[method]['user_prompt'])
                    # Save test transactions for verification
                    with open(f"prompt_tests/{method_name}_test_transactions.json", 'w') as f:
                        json.dump(test_set, f, indent=2)
                
                self.stdout.write("Prompts saved to prompt_tests/ directory. No API calls made.")
                return
            
            # Process with OpenAI for selected methods
            for method in methods_to_test:
                method_name = f"Method {method}"
                self.stdout.write(f"Processing with {method_name}...")
                method_results[method] = process_with_openai(method_data[method], method_name)
            
            # Evaluate results for methods that succeeded
            method_evals = {}
            for method in methods_to_test:
                if method in method_results and method_results[method]:
                    method_evals[method] = evaluate_results(method_results[method]['results'], test_set)
                    print_evaluation(
                        method_evals[method], 
                        f"Method {method}", 
                        method_results[method]['time'], 
                        method_results[method]['tokens']
                    )
            
            # Determine which method performed best
            best_method = None
            best_accuracy = 0
            
            for method in methods_to_test:
                if method in method_evals:
                    method_acc = method_evals[method]['accuracy']
                    if method_acc > best_accuracy:
                        best_accuracy = method_acc
                        best_method = f"Method {method}"
            
            # Print conclusion
            if best_method:
                self.stdout.write(f"\nBest performing method: {best_method} with {best_accuracy * 100:.2f}% accuracy")
                self.stdout.write(f"To use this method in production, update find_transaction_supplier_open_ai.py with the approach from {best_method}")
            else:
                self.stdout.write("\nNo method produced valid results. Please check the logs for errors.")
            
        except Exception as e:
            self.stderr.write(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main() 