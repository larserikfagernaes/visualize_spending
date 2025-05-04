#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Default values
LIMIT=500
BATCH=50
THRESHOLD=0.75
MIN_EXAMPLES=2
DRY_RUN=""

# Parse command line options
while [[ $# -gt 0 ]]; do
  case $1 in
    --limit=*)
      LIMIT="${1#*=}"
      shift
      ;;
    --batch=*)
      BATCH="${1#*=}"
      shift
      ;;
    --threshold=*)
      THRESHOLD="${1#*=}"
      shift
      ;;
    --min-examples=*)
      MIN_EXAMPLES="${1#*=}"
      shift
      ;;
    --dry-run)
      DRY_RUN="--dry-run"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--limit=N] [--batch=N] [--threshold=0.N] [--min-examples=N] [--dry-run]"
      exit 1
      ;;
  esac
done

# Run the command with specified options
echo "Running supplier matching with the following options:"
echo "  Limit: $LIMIT"
echo "  Batch size: $BATCH"
echo "  Similarity threshold: $THRESHOLD"
echo "  Min examples per supplier: $MIN_EXAMPLES"
echo "  Dry run: ${DRY_RUN:+Yes}"

python manage.py match_suppliers_with_embeddings \
  --limit="$LIMIT" \
  --batch="$BATCH" \
  --threshold="$THRESHOLD" \
  --min-examples="$MIN_EXAMPLES" \
  $DRY_RUN 