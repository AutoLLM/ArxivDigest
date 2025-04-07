# 🎨 Design Paper Discovery

This module specializes in finding and analyzing papers related to AI/ML for design automation. It crawls arXiv for design-related papers and provides detailed reports on recent research at the intersection of AI and design.

## Features

- **Smart Paper Finding**: Automatically finds papers related to design automation and creative AI
- **Multi-Category Search**: Searches across Computer Vision, Graphics, HCI, and other relevant arXiv categories
- **Intelligent Categorization**: Sorts papers into design subcategories (UI/UX, Layout, Graphic Design, etc.)
- **Technique Analysis**: Identifies AI techniques used (GANs, Diffusion Models, LLMs, etc.)
- **LLM-Powered Analysis**: Optional in-depth analysis using OpenAI, Gemini, or Claude models
- **HTML Reports**: Generates clean, organized HTML reports with paper statistics and details
- **JSON Export**: Saves all paper data in structured JSON format for further processing

## Quick Start

Run the main script from the project root directory:

```bash
# Basic usage - find design papers from the last 7 days
./src/design/find_design_papers.sh

# With keyword filtering - find design papers about layout generation
./src/design/find_design_papers.sh --keyword "layout"

# With longer timeframe - find design papers from the last month
./src/design/find_design_papers.sh --days 30
```

## Advanced Usage

```bash
# With LLM analysis for comprehensive paper details
./src/design/find_design_papers.sh --analyze

# Customize research interests for analysis
./src/design/find_design_papers.sh --analyze --interest "I'm looking for papers on UI/UX automation and layout generation with neural networks"

# Change the model used for analysis
./src/design/find_design_papers.sh --analyze --model "gpt-4o"

# Combined example with all major features
./src/design/find_design_papers.sh --days 14 --keyword "diffusion" --analyze --model "gpt-4o" --interest "I'm researching diffusion models for design applications"

# Output files include the current date by default:
# - data/design_papers_diffusion_20250406.json
# - digest/design_papers_diffusion_20250406.html

# Disable date in filenames if needed
./src/design/find_design_papers.sh --keyword "layout" --no-date
```

## Parameters Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--days N` | Number of days to search back | 7 |
| `--keyword TERM` | Filter papers containing this keyword | none |
| `--analyze` | Use LLM to perform detailed analysis | false |
| `--interest "TEXT"` | Custom research interest for LLM | Design automation focus |
| `--model MODEL` | Model to use for analysis | gpt-3.5-turbo-16k |
| `--no-date` | Don't add date to output filenames | false |
| `--output FILE` | Custom JSON output path | data/design_papers_DATE.json |
| `--html FILE` | Custom HTML output path | digest/design_papers_DATE.html |
| `--help` | Show help message | |

## Implementation Details

The design paper discovery consists of these main components:

1. **find_design_papers.sh**: Main shell script interface with help and options
2. **find_design_papers.py**: Core Python implementation for arXiv discovery and analysis
3. **design_finder.py**: Alternative implementation with minimal dependencies
4. **get_design_papers.sh**: Legacy script (maintained for backward compatibility)

## Example Output

The HTML report includes:
- Summary statistics and paper counts by category and technique
- Detailed paper listings with titles, authors, and abstracts
- AI analysis sections when using the `--analyze` flag
- Links to arXiv pages and PDF downloads
