"""
Main module for design_finder.
Run with: python -m src.design_finder
"""
import os
import sys
import json
import argparse
import datetime
import logging
from typing import List, Dict, Any

# Add parent directory to path to import from sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from src.download_new_papers import get_papers, _download_new_papers
from src.design_automation import (
    is_design_automation_paper,
    categorize_design_paper,
    analyze_design_techniques,
    extract_design_metrics
)
from src.paths import DATA_DIR, DIGEST_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default arXiv categories to search
DEFAULT_CATEGORIES = [
    "cs.CV",  # Computer Vision
    "cs.GR",  # Graphics
    "cs.HC",  # Human-Computer Interaction
    "cs.AI",  # Artificial Intelligence
    "cs.LG",  # Machine Learning
    "cs.CL",  # Computation and Language (NLP)
    "cs.MM",  # Multimedia
    "cs.SD",  # Sound
    "cs.RO",  # Robotics (for interactive design)
    "cs.CY"   # Computers and Society
]

def get_date_range(days_back: int = 7) -> List[str]:
    """
    Get a list of dates for the past N days in arXiv format.
    
    Args:
        days_back: Number of days to look back
        
    Returns:
        List of date strings in arXiv format
    """
    today = datetime.datetime.now()
    dates = []
    
    for i in range(days_back):
        date = today - datetime.timedelta(days=i)
        date_str = date.strftime("%a, %d %b %y")
        dates.append(date_str)
        
    return dates

def ensure_data_files(categories: List[str], days_back: int = 7) -> None:
    """
    Make sure data files exist for the specified categories and date range.
    
    Args:
        categories: List of arXiv category codes
        days_back: Number of days to look back
    """
    dates = get_date_range(days_back)
    
    for category in categories:
        for date_str in dates:
            # Add a delay between requests to avoid being blocked
            time.sleep(1)
            file_path = os.path.join(DATA_DIR, f"{category}_{date_str}.jsonl")
            
            if not os.path.exists(file_path):
                logger.info(f"Downloading papers for {category} on {date_str}")
                try:
                    _download_new_papers(category)
                except Exception as e:
                    logger.error(f"Error downloading {category} papers for {date_str}: {e}")

def get_design_papers(categories: List[str], days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Get design automation papers from specified categories over a date range.
    
    Args:
        categories: List of arXiv category codes
        days_back: Number of days to look back
        
    Returns:
        List of design automation papers
    """
    # Ensure data files exist
    ensure_data_files(categories, days_back)
    
    # Collect papers
    all_papers = []
    dates = get_date_range(days_back)
    
    for category in categories:
        for date_str in dates:
            try:
                papers = get_papers(category)
                all_papers.extend(papers)
            except Exception as e:
                logger.warning(f"Could not get papers for {category} on {date_str}: {e}")
    
    # Remove duplicates (papers can appear in multiple categories)
    unique_papers = {}
    for paper in all_papers:
        paper_id = paper.get("main_page", "").split("/")[-1]
        if paper_id and paper_id not in unique_papers:
            unique_papers[paper_id] = paper
    
    # Filter design automation papers
    design_papers = []
    for paper_id, paper in unique_papers.items():
        if is_design_automation_paper(paper):
            paper["paper_id"] = paper_id
            paper["design_category"] = categorize_design_paper(paper)
            paper["design_techniques"] = analyze_design_techniques(paper)
            paper["design_metrics"] = extract_design_metrics(paper)
            design_papers.append(paper)
    
    # Sort by date (newest first)
    design_papers.sort(key=lambda p: p.get("main_page", ""), reverse=True)
    
    return design_papers

def print_paper_summary(paper: Dict[str, Any]) -> None:
    """
    Print a nice summary of a paper to the console.
    
    Args:
        paper: Paper dictionary
    """
    print(f"\n{'=' * 80}")
    print(f"TITLE: {paper.get('title', 'No title')}")
    print(f"AUTHORS: {paper.get('authors', 'No authors')}")
    print(f"URL: {paper.get('main_page', 'No URL')}")
    print(f"DESIGN CATEGORY: {paper.get('design_category', 'Unknown')}")
    print(f"TECHNIQUES: {', '.join(paper.get('design_techniques', []))}")
    print(f"METRICS: {', '.join(paper.get('design_metrics', []))}")
    print(f"\nABSTRACT: {paper.get('abstract', 'No abstract')[:500]}...")
    print(f"{'=' * 80}\n")

def generate_html_report(papers: List[Dict[str, Any]], output_file: str) -> None:
    """
    Generate an HTML report from papers.
    
    Args:
        papers: List of paper dictionaries
        output_file: Path to output HTML file
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Design Automation Papers</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            .paper {{ margin-bottom: 30px; border-bottom: 1px solid #ddd; padding-bottom: 20px; }}
            .title {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
            .authors {{ font-style: italic; margin: 5px 0; }}
            .categories {{ color: #3498db; margin-bottom: 10px; }}
            .abstract {{ margin-top: 10px; }}
            .techniques {{ margin-top: 10px; color: #16a085; }}
            .metrics {{ margin-top: 5px; color: #8e44ad; }}
            a {{ color: #2980b9; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .stats {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #7f8c8d; text-align: center; }}
            .date {{ color: #95a5a6; font-size: 14px; }}
        </style>
    </head>
    <body>
        <h1>Design Automation Papers</h1>
        <div class="stats">
            <p>Found {len(papers)} papers related to graphic design automation with AI/ML</p>
            <p>Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    """
    
    # Count categories and techniques
    categories = {}
    techniques = {}
    
    for paper in papers:
        category = paper.get("design_category", "Uncategorized")
        if category in categories:
            categories[category] += 1
        else:
            categories[category] = 1
            
        for technique in paper.get("design_techniques", []):
            if technique in techniques:
                techniques[technique] += 1
            else:
                techniques[technique] = 1
    
    # Add summary statistics
    html += "<div class='stats'><h2>Summary Statistics</h2>"
    
    html += "<h3>Categories:</h3><ul>"
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        html += f"<li>{category}: {count} papers</li>"
    html += "</ul>"
    
    html += "<h3>Techniques:</h3><ul>"
    for technique, count in sorted(techniques.items(), key=lambda x: x[1], reverse=True):
        html += f"<li>{technique}: {count} papers</li>"
    html += "</ul></div>"
    
    # Add papers
    for paper in papers:
        publish_date = paper.get("main_page", "").split("/")[-1][:4]  # Extract YYMM from id
        
        html += f"""
        <div class="paper">
            <div class="title"><a href="{paper.get("main_page", "#")}">{paper.get("title", "No title")}</a></div>
            <div class="authors">{paper.get("authors", "Unknown authors")}</div>
            <div class="date">arXiv ID: {paper.get("paper_id", "Unknown")}</div>
            <div class="categories">Category: {paper.get("design_category", "General")} | Subject: {paper.get("subjects", "N/A")}</div>
            <div class="techniques">Techniques: {', '.join(paper.get("design_techniques", ["None identified"]))}</div>
            <div class="metrics">Evaluation metrics: {', '.join(paper.get("design_metrics", ["None identified"]))}</div>
            <div class="abstract"><strong>Abstract:</strong> {paper.get("abstract", "No abstract available")}</div>
        </div>
        """
    
    html += """
        <div class="footer">
            <p>Generated by ArxivDigest Design Finder</p>
        </div>
    </body>
    </html>
    """
    
    with open(output_file, "w") as f:
        f.write(html)
    
    logger.info(f"HTML report generated: {output_file}")

def main():
    """Main function for the design finder module."""
    parser = argparse.ArgumentParser(description="Find the latest graphic design automation papers.")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--output", type=str, default="design_papers.json", help="Output JSON file path")
    parser.add_argument("--html", type=str, default="design_papers.html", help="Output HTML file path")
    parser.add_argument("--categories", type=str, nargs="+", default=DEFAULT_CATEGORIES, 
                        help="arXiv categories to search")
    parser.add_argument("--keyword", type=str, help="Additional keyword to filter papers")
    parser.add_argument("--technique", type=str, help="Filter by specific technique")
    parser.add_argument("--category", type=str, help="Filter by specific design category")
    args = parser.parse_args()
    
    logger.info(f"Looking for design papers in the past {args.days} days")
    logger.info(f"Searching categories: {', '.join(args.categories)}")
    
    # DATA_DIR is already created by paths.py
    
    # Get design papers
    design_papers = get_design_papers(args.categories, args.days)
    
    # Apply additional filters if specified
    if args.keyword:
        keyword = args.keyword.lower()
        design_papers = [
            p for p in design_papers 
            if keyword in p.get("title", "").lower() or 
               keyword in p.get("abstract", "").lower()
        ]
        logger.info(f"Filtered by keyword '{args.keyword}': {len(design_papers)} papers remaining")
        
    if args.technique:
        technique = args.technique.lower()
        design_papers = [
            p for p in design_papers 
            if any(technique in t.lower() for t in p.get("design_techniques", []))
        ]
        logger.info(f"Filtered by technique '{args.technique}': {len(design_papers)} papers remaining")
        
    if args.category:
        category = args.category.lower()
        design_papers = [
            p for p in design_papers 
            if category in p.get("design_category", "").lower()
        ]
        logger.info(f"Filtered by category '{args.category}': {len(design_papers)} papers remaining")
    
    logger.info(f"Found {len(design_papers)} design automation papers")
    
    # Print summary to console
    for paper in design_papers[:10]:  # Print top 10
        print_paper_summary(paper)
    
    if len(design_papers) > 10:
        print(f"...and {len(design_papers) - 10} more papers.")
    
    # Save to JSON file in data directory
    output_path = os.path.join(DATA_DIR, args.output)
    with open(output_path, "w") as f:
        json.dump(design_papers, f, indent=2)
    
    logger.info(f"Saved {len(design_papers)} papers to {output_path}")
    
    # Generate HTML report in digest directory
    html_path = os.path.join(DIGEST_DIR, args.html)
    generate_html_report(design_papers, html_path)
    
    print(f"\nResults saved to {output_path} and {html_path}")

if __name__ == "__main__":
    main()