#!/usr/bin/env python3
"""
Design Papers Crawler - A dedicated script to find the latest papers
on graphic design automation using AI/ML/LLM technologies.

Usage:
    python design_papers_crawler.py [--days 7] [--output design_papers.json]
"""

import os
import sys
import json
import argparse
import datetime
import logging
from typing import List, Dict, Any

# Add parent directory to path to import from sibling modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def main():
    """Main function to run the design papers crawler."""
    parser = argparse.ArgumentParser(description="Find the latest graphic design automation papers.")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--output", type=str, default="design_papers.json", help="Output file path")
    parser.add_argument("--categories", type=str, nargs="+", default=DEFAULT_CATEGORIES, 
                        help="arXiv categories to search")
    args = parser.parse_args()
    
    logger.info(f"Looking for design papers in the past {args.days} days")
    logger.info(f"Searching categories: {', '.join(args.categories)}")
    
    # DATA_DIR is already created by paths.py
    
    # Get design papers
    design_papers = get_design_papers(args.categories, args.days)
    
    logger.info(f"Found {len(design_papers)} design automation papers")
    
    # Print summary to console
    for paper in design_papers[:10]:  # Print top 10
        print_paper_summary(paper)
    
    if len(design_papers) > 10:
        print(f"...and {len(design_papers) - 10} more papers.")
    
    # Determine output path - ensure it's in DATA_DIR
    output_path = os.path.join(DATA_DIR, args.output) 
    
    # Save to file
    with open(output_path, "w") as f:
        json.dump(design_papers, f, indent=2)
    
    logger.info(f"Saved {len(design_papers)} papers to {output_path}")
    print(f"\nResults saved to {output_path}")

if __name__ == "__main__":
    main()