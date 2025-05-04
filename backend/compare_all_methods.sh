#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Default values
TEST_SIZE=50
METHODS="1,2,3,4"
THRESHOLD=0.7
SAVE_RESULTS="false"

# Parse command line options
while [[ $# -gt 0 ]]; do
  case $1 in
    --test-size=*)
      TEST_SIZE="${1#*=}"
      shift
      ;;
    --methods=*)
      METHODS="${1#*=}"
      shift
      ;;
    --threshold=*)
      THRESHOLD="${1#*=}"
      shift
      ;;
    --save)
      SAVE_RESULTS="true"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--test-size=N] [--methods=1,2,3,4] [--threshold=0.N] [--save]"
      exit 1
      ;;
  esac
done

# Run the command with specified options
echo "Running comparison with the following options:"
echo "  Test size: $TEST_SIZE"
echo "  Methods to test: $METHODS"
echo "  Similarity threshold: $THRESHOLD"
echo "  Save results: $SAVE_RESULTS"

# Build command
CMD="python manage.py compare_all_matching_methods --test-size=$TEST_SIZE --methods=$METHODS --threshold=$THRESHOLD"
if [ "$SAVE_RESULTS" = "true" ]; then
  CMD="$CMD --save"
fi

# Run the command
echo "Executing: $CMD"
$CMD 