# Supplier Matching Methods Comparison

This Django management command compares different methods for automatically matching transactions to suppliers based on transaction descriptions. It implements and evaluates four different algorithms:

1. **Enhanced TF-IDF + Cosine Similarity** - Uses improved TF-IDF vectorization with preprocessing and supplier-aware grouping
2. **Fuzzy Matching / String Similarity (Levenshtein)** - Uses string edit distance for matching
3. **TF-IDF + Fuzzy Matching Hybrid** - Uses a weighted combination of TF-IDF and fuzzy matching
4. **N-gram Analysis** - Uses character n-grams (3-5 characters) to find similar transactions

## Requirements

Different methods require different Python packages:

### For Methods 1, 3, and 4 (Enhanced TF-IDF, Hybrid, N-gram)
```bash
pip install scikit-learn
```

### For Methods 2 and 3 (Levenshtein, Hybrid)
Either:
```bash
pip install python-Levenshtein
```
Or:
```bash
pip install thefuzz
```

### For running all methods
Install all required packages:
```bash
pip install scikit-learn thefuzz
```

## How it Works

The script:
1. Creates a test set of transactions with known suppliers
2. Creates a training set from the remaining transactions
3. Applies each of the methods to predict suppliers for the test set
4. Evaluates the accuracy and performance of each method
5. Optionally applies the best method to transactions without suppliers in the database

## Methods Details

### Method 1: Enhanced TF-IDF + Cosine Similarity
Uses term frequency-inverse document frequency (TF-IDF) vectorization with several improvements:
- **Text preprocessing**: Normalizes text with lowercase conversion and special character removal
- **Stopwords removal**: Filters out common transaction words that don't help with supplier identification
- **N-gram analysis**: Uses both single words and word pairs to capture phrases like company names
- **Supplier-aware grouping**: Considers multiple matches from the same supplier for more robust matching
- **Top-K matching**: Examines multiple top matches instead of just the highest-scoring one

This enhanced approach significantly improves matching accuracy compared to basic TF-IDF.

### Method 2: Fuzzy Matching / String Similarity (Levenshtein)
Uses Levenshtein distance (edit distance) to measure the similarity between transaction descriptions. This method is good at handling typos, word reordering, and small variations in text.

### Method 3: TF-IDF + Fuzzy Matching Hybrid
Combines both approaches for better results. This method:
1. Calculates TF-IDF similarity scores
2. Calculates fuzzy matching similarity scores
3. Combines these scores using weighted average (default: 60% TF-IDF, 40% fuzzy)
This hybrid approach often outperforms either method alone.

### Method 4: N-gram Analysis
Uses character n-grams (sequences of 3-5 characters) instead of words. This approach is particularly good at handling variations in spelling, word boundaries, and abbreviations.

## Usage

```bash
# Activate the virtual environment
cd backend
source venv/bin/activate

# Run all methods with default parameters
python manage.py compare_supplier_matching_methods

# Run with a specific test size (number of transactions to test)
python manage.py compare_supplier_matching_methods --test-size 100

# Run only a specific method (1: Enhanced TF-IDF, 2: Levenshtein, 3: Hybrid, 4: N-gram)
python manage.py compare_supplier_matching_methods --method 3

# Save detailed results to a file
python manage.py compare_supplier_matching_methods --save

# Apply the best method to update transactions in the database
python manage.py compare_supplier_matching_methods --apply

# Specify a custom similarity threshold (0.0-1.0)
python manage.py compare_supplier_matching_methods --threshold 0.8
```

## Results Format

The script will output something like:

```
RESULTS FOR: Method 1: Enhanced TF-IDF + Cosine Similarity
================================================================================
ACCURACY: 95.00%
CORRECT: 48 / 50
AVG CONFIDENCE: 88.72
PROCESSING TIME: 0.89 seconds

DETAILED RESULTS:
--------------------------------------------------------------------------------
✓ ID: 12345
  Description: PAYMENT TO ACME INC #12345...
  True: ACME INC
  Predicted: ACME INC (Confidence: 95)
...
```

## Direct Application

You can also directly apply a specific method to your database without testing first:

```bash
# Apply the hybrid method to all unmatched transactions
python manage.py auto_match_suppliers

# Use a specific method
python manage.py auto_match_suppliers --method 1

# Limit the number of transactions to process
python manage.py auto_match_suppliers --limit 100

# Do a dry run without updating the database
python manage.py auto_match_suppliers --dry-run
```

## Applying Results

If you use the `--apply` flag, the script will apply the highest-performing method to match transactions without suppliers in the database. It will:

1. Find all transactions without suppliers
2. Use the best method to match them against transactions with known suppliers
3. Update transactions with the matched supplier if the confidence is above the threshold
4. Also set the category based on the supplier's most common transaction category

## Recommended Workflow

1. Run the script without the `--apply` flag to see which method performs best
2. Review the detailed results to confirm the accuracy
3. If satisfied, run again with the `--apply` flag to update your database
4. Adjust the threshold with `--threshold` if needed to balance precision and recall

## Example

```bash
# First, test the methods
python manage.py compare_supplier_matching_methods --test-size 100 --save

# Then apply the best method with a stricter threshold
python manage.py compare_supplier_matching_methods --apply --threshold 0.85

# Or directly apply the enhanced TF-IDF method with a custom threshold
python manage.py auto_match_suppliers --method 1 --threshold 0.75
``` 