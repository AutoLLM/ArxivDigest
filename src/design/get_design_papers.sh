#!/bin/bash
# Legacy wrapper script for design papers finder - maintained for backward compatibility
# For new scripts, use find_design_papers.sh instead

# Show deprecation warning
echo "⚠️ Warning: get_design_papers.sh is deprecated and will be removed in a future version"
echo "⚠️ Please use find_design_papers.sh instead, which has more features and better output"
echo ""

# Default values
DAYS=7
OUTPUT="design_papers.json"
KEYWORD=""
ANALYZE=""

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --days)
      DAYS="$2"
      shift 2
      ;;
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    --keyword)
      KEYWORD="$2"
      shift 2
      ;;
    --analyze)
      ANALYZE="--analyze"
      shift
      ;;
    --email)
      # Ignore email parameter - email functionality is removed
      echo "Note: Email functionality has been removed. HTML report will be generated locally only."
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Run the crawler using the new script
echo "Searching for design papers from the last $DAYS days..."

# Build the command
CMD="./src/design/find_design_papers.sh --days $DAYS --output ./data/$OUTPUT --html ./digest/${OUTPUT%.json}.html"

# Add keyword if specified
if [ -n "$KEYWORD" ]; then
  CMD="$CMD --keyword \"$KEYWORD\""
fi

# Add analyze if specified
if [ -n "$ANALYZE" ]; then
  CMD="$CMD --analyze"
fi

# Execute the command
eval $CMD

echo "Done! View your results in ./digest/${OUTPUT%.json}.html"