#!/bin/bash
# Root-level wrapper script for the design papers finder

# Show deprecation warning
echo "ℹ️ Note: This script is a wrapper for ./src/design/find_design_papers.sh"
echo "ℹ️ Consider using ./src/design/find_design_papers.sh directly for best results"
echo ""

# Simply forward all arguments to the actual script
./src/design/find_design_papers.sh "$@"

# The exit code will propagate from the called script
exit $?