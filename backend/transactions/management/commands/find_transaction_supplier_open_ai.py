#!/usr/bin/env python3
import os
import sys
import json
from django.core.management.base import BaseCommand
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

# Set up environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')

# Import Django after setting environment
import django
django.setup()


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
MAX_TOKENS = 100000  # Limited context window
BATCH_SIZE = 150  # Adjusted batch size for limited context
MAX_SUPPLIER_PROFILES = 100  # Maximum number of supplier profiles to include
MAX_EXAMPLES_PER_SUPPLIER = 3  # Maximum number of recent examples per supplier
MAX_PATTERNS_PER_SUPPLIER = 5  # Maximum number of unique patterns per supplier

def get_api_client():
    """Initialize and return the OpenAI API client."""
    global api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    return OpenAI(api_key=api_key)

def get_unmatched_transactions():
    """Retrieves all transactions without a supplier."""
    return Transaction.objects.filter(
        supplier__isnull=True
    ).order_by('-date', '-id').values('id', 'description')

def get_matched_transactions():
    """Retrieves all transactions with a supplier for reference."""
    return Transaction.objects.exclude(
        supplier__isnull=True
    ).select_related(
        'supplier',
        'category'
    ).order_by('-date').values(
        'id',
        'description',
        'supplier__name',
        'supplier__id',
        'category__name',
        'amount',
        'date'
    )

def prepare_openai_input(reference_transactions, unmatched_transactions, batch_size=BATCH_SIZE):
    """
    Prepare batches of data for OpenAI processing with enhanced context.
    Uses Method 4 approach with feature extraction and tokenization.
    Ensures total tokens stay within MAX_TOKENS limit.
    """
    # Group reference transactions by supplier
    supplier_transactions = {}
    for tx in reference_transactions:
        supplier_id = tx['supplier__id']
        if supplier_id not in supplier_transactions:
            supplier_transactions[supplier_id] = []
        supplier_transactions[supplier_id].append({
            'description': tx['description']
        })

    # Create supplier profiles with extracted features
    supplier_profiles = []
    for supplier_id, transactions in supplier_transactions.items():
        supplier_name = reference_transactions.filter(supplier__id=supplier_id).first()['supplier__name']
        
        # Extract unique descriptions
        all_descriptions = list(set([tx['description'] for tx in transactions]))
        
        # Extract identifying tokens, prefixes, numbers, and patterns
        tokens = []
        prefixes = []
        numbers = []
        patterns = []
        
        import re
        for desc in all_descriptions:
            # Extract tokens (words)
            words = desc.lower().split()
            tokens.extend(words)
            
            # Extract prefixes (first few characters)
            if len(desc) > 3:
                prefixes.append(desc[:4].lower())
            
            # Extract numbers
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
    
    # Split unmatched transactions into batches
    batches = []
    for i in range(0, len(unmatched_transactions), batch_size):
        batch_txs = unmatched_transactions[i:i+batch_size]
        
        # Prepare unmatched transactions for this batch
        unmatched_list = [{
            "id": tx['id'],
            "description": tx['description']
        } for tx in batch_txs]
        
        # Create system and user prompts
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

Return results in JSON format with:
- transaction_id: The ID of the unmatched transaction
- best_match_supplier_name: The supplier name (or "no_match" if no confident match)
- confidence_level: 0-100 score based on match strength
"""

        user_prompt = f"""
SUPPLIER PROFILES (with feature sets):
{json.dumps(supplier_profiles, indent=2)}

UNMATCHED TRANSACTIONS:
{json.dumps(unmatched_list, indent=2)}

Analyze the unmatched transactions using the feature-based approach. For each transaction, determine the best supplier match and return your results as a JSON array.
"""
        
        # Estimate tokens for this batch
        system_tokens = estimate_tokens(system_prompt)
        user_tokens = estimate_tokens(user_prompt)
        total_tokens = system_tokens + user_tokens
        
        # If this batch would exceed token limit, reduce batch size and try again
        if total_tokens > MAX_TOKENS * 0.8:
            # Calculate a new batch size that would fit within limits
            reduction_factor = (MAX_TOKENS * 0.8) / total_tokens
            new_batch_size = int(len(batch_txs) * reduction_factor)
            print(f"Reducing batch size from {len(batch_txs)} to {new_batch_size} to fit token limit")
            
            # Recursively call with smaller batch size
            return prepare_openai_input(reference_transactions, unmatched_transactions, new_batch_size)
        
        batches.append({
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'unmatched_ids': [tx['id'] for tx in batch_txs]
        })
    
    return batches

def estimate_tokens(text):
    """Estimate token count for the text using tiktoken if available, otherwise use a simple heuristic."""
    if HAS_TIKTOKEN:
        # Use proper tokenization with tiktoken
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return len(enc.encode(text))
    else:
        # Fallback to a simple estimate: ~4 characters per token on average
        return len(text) // 4

def process_with_openai(batches):
    """Process batches of transactions using OpenAI API."""
    if not HAS_OPENAI:
        raise ImportError("OpenAI package is required but not installed.")
    
    client = get_api_client()
    all_results = []
    
    for i, batch in enumerate(batches):
        print(f"\nProcessing batch {i+1} of {len(batches)} ({len(batch['unmatched_ids'])} transactions)...")
        
        # Print token estimates
        system_tokens = estimate_tokens(batch['system_prompt'])
        user_tokens = estimate_tokens(batch['user_prompt'])
        total_tokens = system_tokens + user_tokens
        print(f"Token estimates: System prompt: {system_tokens}, User prompt: {user_tokens}, Total: {total_tokens}")
        
        if total_tokens > MAX_TOKENS * 0.8:
            print(f"WARNING: Batch {i+1} exceeds recommended token limit. Skipping to avoid errors.")
            continue
        
        # Print the prompts
        print("\nSystem Prompt:")
        print("=" * 80)
        print(batch['system_prompt'])
        print("\nUser Prompt:")
        print("=" * 80)
        print(batch['user_prompt'])
        print("=" * 80)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4-0125-preview",  # Using GPT-4 Turbo
                messages=[
                    {"role": "system", "content": batch['system_prompt']},
                    {"role": "user", "content": batch['user_prompt']}
                ],
                temperature=0.2,  # Lower temperature for more deterministic results
                max_tokens=4000,  # Reduced for token control
            )
            
            # Extract the response content
            response_text = response.choices[0].message.content
            
            # Parse the JSON response
            try:
                # Sometimes the model might include markdown formatting or extra text
                # Extract just the JSON part
                start_index = response_text.find('[')
                end_index = response_text.rfind(']') + 1
                if start_index >= 0 and end_index > start_index:
                    json_str = response_text[start_index:end_index]
                    batch_results = json.loads(json_str)
                else:
                    raise ValueError("Could not find valid JSON in response")
                
                all_results.extend(batch_results)
                print(f"Successfully processed {len(batch_results)} transactions in batch {i+1}")
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                print(f"Response was: {response_text}")
                # Continue with next batch instead of failing completely
                
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
    
    return all_results

def print_results(results, limit=20):
    """Print the matching results in a readable format."""
    print(f"\nMatching Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Found {len(results)} unmatched transactions")
    print("-" * 80)
    
    # Sort by confidence score (highest first)
    sorted_results = sorted(results, key=lambda x: x.get('confidence_level', 0), reverse=True)
    
    # Show top matches first (limit if there are many)
    display_results = sorted_results[:limit] if len(sorted_results) > limit else sorted_results
    
    for result in display_results:
        tx_id = result.get('transaction_id')
        confidence = result.get('confidence_level', 0)
        
        # Get the transaction description
        try:
            tx = Transaction.objects.get(id=tx_id)
            tx_desc = tx.description
        except Transaction.DoesNotExist:
            tx_desc = "Unknown transaction"
            
        print(f"Transaction ID: {tx_id}")
        print(f"  Description: '{tx_desc}'")
        
        if result.get('best_match_supplier_name') != "no_match" and confidence > 0:
            print(f"  Proposed Match: Supplier '{result.get('best_match_supplier_name')}'")
            print(f"  Confidence Score: {confidence}")
        else:
            print("  No suitable match found.")
            
        print("-" * 80)
    
    if len(sorted_results) > limit:
        print(f"Showing top {limit} results of {len(sorted_results)} total matches.")

def apply_matches_to_database(results, confidence_threshold=70):
    """Apply the matches to the database if they meet the confidence threshold, and infer category from supplier's previous transactions."""
    applied_count = 0
    skipped_count = 0
    
    for result in results:
        if (result.get('confidence_level', 0) >= confidence_threshold and 
            result.get('best_match_supplier_name') != "no_match"):
            
            # Get the transaction and supplier objects
            try:
                transaction = Transaction.objects.get(id=result['transaction_id'])
                supplier = Supplier.objects.get(name=result['best_match_supplier_name'])
                
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
                    most_common_category_id, _ = Counter(prev_categories).most_common(1)[0]
                    category = Category.objects.filter(id=most_common_category_id).first()
                    if category:
                        transaction.category = category
                        print(f"  → Set category to '{category.name}' (ID: {category.id}) based on supplier's previous transactions.")
                        # Optionally, update or create CategorySupplierMap
                        CategorySupplierMap.objects.get_or_create(supplier=supplier, category=category)
                
                # If raw_data contains matchType, update it
                if transaction.raw_data and isinstance(transaction.raw_data, dict):
                    transaction.raw_data['matchType'] = 'openai_matched'
                
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
    help = 'Match transactions without suppliers using OpenAI API to analyze description patterns.'

    def add_arguments(self, parser):
        parser.add_argument('-a', '--apply', action='store_true', 
                          help='Apply matches to the database without prompting')
        parser.add_argument('-t', '--threshold', type=float, default=70,
                          help='Confidence threshold for matching (default: 70)')
        parser.add_argument('-l', '--limit', type=int, default=0,
                          help='Limit processing to N transactions (default: 0 = all transactions)')
        parser.add_argument('-d', '--display', type=int, default=20,
                          help='Number of results to display (default: 20)')
        parser.add_argument('-b', '--batch-size', type=int, default=BATCH_SIZE,
                          help=f'Number of transactions per API call (default: {BATCH_SIZE})')

    def handle(self, *args, **options):
        try:
            # Check for OpenAI package
            if not HAS_OPENAI:
                self.stderr.write("OpenAI package is required but not installed. Please install with 'pip install openai'")
                return
                
            # Check for API key
            if not os.getenv("OPENAI_API_KEY"):
                self.stderr.write("OPENAI_API_KEY environment variable must be set.")
                return
            
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
            
            # Update batch size if specified
            batch_size = options.get('batch_size', BATCH_SIZE)
            
            # Prepare batches for OpenAI processing
            self.stdout.write("Preparing data for OpenAI processing...")
            batches = prepare_openai_input(reference_transactions, unmatched_transactions, batch_size)
            self.stdout.write(f"Prepared {len(batches)} batches for processing")
            
            # Process with OpenAI
            self.stdout.write("Processing with OpenAI API...")
            results = process_with_openai(batches)
            
            # Print results
            print_results(results, options['display'])
            
            # Apply matches to database if --apply flag is set
            if options['apply']:
                self.stdout.write(f"\nApplying matches to database with confidence threshold ≥ {options['threshold']}...")
                apply_matches_to_database(results, options['threshold'])
            else:
                self.stdout.write("\nRun with --apply flag to update the database with these matches.")
                self.stdout.write(f"Note: Only matches with confidence level ≥ {options['threshold']} will be applied.")
            
        except Exception as e:
            self.stderr.write(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main() 