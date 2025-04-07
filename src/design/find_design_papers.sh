#!/bin/bash
# Design papers finder script
# Searches arXiv for design automation papers and generates reports
# For full documentation, see ./README.md

# Add help/usage function
show_help() {
  echo "Usage: ./find_design_papers.sh [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --days N              Search papers from the last N days (default: 7)"
  echo "  --keyword TERM        Filter papers containing this keyword"
  echo "  --analyze             Use LLM to perform detailed analysis of papers"
  echo "  --interest \"TEXT\"     Custom research interest description for LLM"
  echo "  --model MODEL         Model to use for analysis (default: gpt-3.5-turbo-16k)"
  echo "  --no-date             Don't add date to output filenames"
  echo "  --output FILE         Custom JSON output path (default: data/design_papers_DATE.json)"
  echo "  --html FILE           Custom HTML output path (default: digest/design_papers_DATE.html)"
  echo "  --help                Show this help message"
  echo ""
  echo "Examples:"
  echo "  ./find_design_papers.sh"
  echo "  ./find_design_papers.sh --keyword \"layout\" --days 14"
  echo "  ./find_design_papers.sh --analyze --interest \"UI/UX automation\""
}

# Show help if requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
  show_help
  exit 0
fi

# Run the design papers finder with all arguments passed through
python -m src.design.find_design_papers "$@"

# Show success message
if [ $? -eq 0 ]; then
  echo "✓ Design papers finder completed successfully!"
  echo "  Open the HTML report in your browser to view results"
else
  echo "✗ Design papers finder encountered an error"
fi
