#!/usr/bin/env python3
"""
Standalone Design Papers Crawler - A simple script to find the latest papers 
on graphic design automation using AI/ML/LLM technologies.

This version has minimal dependencies and doesn't require the full model setup.

Usage:
    python find_design_papers.py [--days 7] [--output design_papers.json]
"""

import os
import sys
import json
import argparse
import datetime
import logging
import re
import urllib.request
import time
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup as bs

# Add parent directory to path to allow imports from sibling modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import DATA_DIR, DIGEST_DIR
from model_manager import model_manager, ModelProvider

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
    "cs.MM"   # Multimedia
]

# Design automation keywords for paper filtering
DESIGN_AUTOMATION_KEYWORDS = [
    "design automation", "layout generation", "visual design", "graphic design",
    "creative AI", "generative design", "UI generation", "UX automation",
    "design system", "composition", "creative workflow", "automated design",
    "design tool", "design assistant", "design optimization", "content-aware",
    "user interface generation", "visual layout", "image composition"
]

def download_papers(category: str, date_str: str = None) -> List[Dict[str, Any]]:
    """
    Download papers for a specific category and date.
    
    Args:
        category: arXiv category code
        date_str: Date string in arXiv format (default: today)
        
    Returns:
        List of paper dictionaries
    """
    if not date_str:
        date = datetime.datetime.now()
        date_str = date.strftime("%a, %d %b %y")
    
    # Data directory is already created by paths.py
    pass
    
    # Check if we already have this data
    file_path = os.path.join(DATA_DIR, f"{category}_{date_str}.jsonl")
    if os.path.exists(file_path):
        papers = []
        with open(file_path, "r") as f:
            for line in f:
                papers.append(json.loads(line))
        return papers
    
    # Download new papers
    logger.info(f"Downloading papers for {category} on {date_str}")
    NEW_SUB_URL = f'https://arxiv.org/list/{category}/new'
    
    try:
        # Add user-agent header to appear more like a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }
        req = urllib.request.Request(NEW_SUB_URL, headers=headers)
        page = urllib.request.urlopen(req)
    except Exception as e:
        logger.error(f"Error downloading from {NEW_SUB_URL}: {e}")
        return []
    
    soup = bs(page, 'html.parser')
    content = soup.body.find("div", {'id': 'content'})
    
    # Find the date heading
    h3 = content.find("h3").text   # e.g: New submissions for Wed, 10 May 23
    date_from_page = h3.replace("New submissions for", "").strip()
    
    # Find all papers
    dt_list = content.dl.find_all("dt")
    dd_list = content.dl.find_all("dd")
    arxiv_base = "https://arxiv.org/abs/"
    arxiv_html = "https://arxiv.org/html/"
    
    papers = []
    for i in range(len(dt_list)):
        try:
            paper = {}
            ahref = dt_list[i].find('a', href=re.compile(r'[/]([a-z]|[A-Z])\w+')).attrs['href']
            paper_number = ahref.strip().replace("/abs/", "")
            
            paper['main_page'] = arxiv_base + paper_number
            paper['pdf'] = arxiv_base.replace('abs', 'pdf') + paper_number
            
            paper['title'] = dd_list[i].find("div", {"class": "list-title mathjax"}).text.replace("Title:\n", "").strip()
            paper['authors'] = dd_list[i].find("div", {"class": "list-authors"}).text.replace("Authors:\n", "").replace("\n", "").strip()
            paper['subjects'] = dd_list[i].find("div", {"class": "list-subjects"}).text.replace("Subjects:\n", "").strip()
            paper['abstract'] = dd_list[i].find("p", {"class": "mathjax"}).text.replace("\n", " ").strip()
            
            # Get a short excerpt of content (optional)
            try:
                # Add user-agent header to appear more like a browser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
                }
                req = urllib.request.Request(arxiv_html + paper_number + "v1", headers=headers)
                html = urllib.request.urlopen(req)
                soup_content = bs(html, 'html.parser')
                content_div = soup_content.find('div', attrs={'class': 'ltx_page_content'})
                if content_div:
                    para_list = content_div.find_all("div", attrs={'class': 'ltx_para'})
                    excerpt = ' '.join([p.text.strip() for p in para_list[:3]])  # Get first 3 paragraphs
                    paper['content_excerpt'] = excerpt[:1000] + "..." if len(excerpt) > 1000 else excerpt
                else:
                    paper['content_excerpt'] = "Content not available"
            except Exception as e:
                paper['content_excerpt'] = f"Error extracting content: {str(e)}"
            
            papers.append(paper)
        except Exception as e:
            logger.warning(f"Error processing paper {i}: {e}")
    
    # Save papers to file
    with open(file_path, "w") as f:
        for paper in papers:
            f.write(json.dumps(paper) + "\n")
    
    return papers

def is_design_automation_paper(paper: Dict[str, Any]) -> bool:
    """
    Check if a paper is related to design automation based on keywords.
    
    Args:
        paper: Dictionary with paper details
        
    Returns:
        Boolean indicating if paper is related to design automation
    """
    text = (
        (paper.get("title", "") + " " + 
         paper.get("abstract", "") + " " + 
         paper.get("subjects", "")).lower()
    )
    
    return any(keyword.lower() in text for keyword in DESIGN_AUTOMATION_KEYWORDS)

def categorize_design_paper(paper: Dict[str, Any]) -> str:
    """
    Categorize design automation paper into subcategories.
    
    Args:
        paper: Dictionary with paper details
        
    Returns:
        Category name string
    """
    text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
    
    categories = {
        "Layout Generation": ["layout", "composition", "arrange", "grid"],
        "UI/UX Design": ["user interface", "ui", "ux", "interface design", "website"],
        "Graphic Design": ["graphic design", "poster", "visual design", "typography"],
        "Image Manipulation": ["image editing", "photo", "manipulation", "style transfer"],
        "Design Tools": ["tool", "assistant", "workflow", "productivity"],
        "3D Design": ["3d", "modeling", "cad", "product design"],
        "Multimodal Design": ["multimodal", "text-to-image", "image-to-code"]
    }
    
    matches = []
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            matches.append(category)
    
    if matches:
        return ", ".join(matches)
    return "General Design Automation"

def analyze_design_techniques(paper: Dict[str, Any]) -> List[str]:
    """
    Extract AI/ML techniques used for design automation in the paper.
    
    Args:
        paper: Dictionary with paper details
        
    Returns:
        List of techniques
    """
    text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
    
    techniques = []
    technique_keywords = {
        "Generative Adversarial Networks": ["gan", "generative adversarial"],
        "Diffusion Models": ["diffusion", "ddpm", "stable diffusion"],
        "Transformers": ["transformer", "attention mechanism"],
        "Reinforcement Learning": ["reinforcement learning", "rl"],
        "Computer Vision": ["computer vision", "vision", "cnn"],
        "Graph Neural Networks": ["graph neural", "gnn"],
        "Large Language Models": ["llm", "large language model", "gpt"],
        "Neural Style Transfer": ["style transfer", "neural style"],
        "Evolutionary Algorithms": ["genetic algorithm", "evolutionary"]
    }
    
    for technique, keywords in technique_keywords.items():
        if any(keyword in text for keyword in keywords):
            techniques.append(technique)
    
    return techniques

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

def generate_html_report(papers: List[Dict[str, Any]], output_file: str, keyword: str = None, days_back: int = 7) -> None:
    """
    Generate an HTML report from papers.
    
    Args:
        papers: List of paper dictionaries
        output_file: Path to output HTML file
        keyword: Optional keyword used for filtering
        days_back: Number of days searched
    """
    # Ensure the output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    # Create a title that includes any keywords and date
    title_date = datetime.datetime.now().strftime("%B %d, %Y")
    page_title = "Design Automation Papers"
    if keyword:
        page_title = f"Design Automation Papers - {keyword.title()} - {title_date}"
    else:
        page_title = f"Design Automation Papers - {title_date}"
        
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{page_title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; max-width: 1200px; margin: 0 auto; }}
            .paper {{ margin-bottom: 40px; border-bottom: 2px solid #ddd; padding-bottom: 30px; }}
            .title {{ font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
            .authors {{ font-style: italic; margin: 8px 0; color: #34495e; }}
            .categories {{ color: #3498db; margin-bottom: 10px; }}
            .abstract {{ margin: 15px 0; line-height: 1.5; }}
            .techniques {{ color: #16a085; margin: 10px 0; }}
            .score {{ font-weight: bold; color: #e74c3c; margin: 10px 0; font-size: 16px; }}
            .reason {{ background-color: #f9f9f9; padding: 15px; border-left: 3px solid #2ecc71; margin: 10px 0; }}
            a {{ color: #2980b9; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .stats {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
            .footer {{ margin-top: 40px; font-size: 12px; color: #7f8c8d; text-align: center; }}
            .section {{ margin: 15px 0; padding: 10px; background-color: #f8f9fa; border-radius: 5px; }}
            .section-title {{ font-weight: bold; color: #2c3e50; }}
            .links {{ margin-top: 15px; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
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
        html += f"""
        <div class="paper">
            <div class="title"><a href="{paper.get("main_page", "#")}" target="_blank">{paper.get("title", "No title")}</a></div>
            <div class="authors">{paper.get("authors", "Unknown authors")}</div>
            <div class="categories">Category: {paper.get("design_category", "General")} | Subject: {paper.get("subjects", "N/A")}</div>
            <div class="techniques">Techniques: {', '.join(paper.get("design_techniques", ["None identified"]))}</div>
        """
        
        # Add relevancy score and reasons if available
        if "Relevancy score" in paper:
            html += f'<div class="score">Relevancy Score: {paper.get("Relevancy score", "N/A")}</div>'
        
        if "Reasons for match" in paper:
            html += f'<div class="reason"><b>Reason:</b> {paper.get("Reasons for match", "")}</div>'
            
        # Add abstract 
        if "abstract" in paper:
            html += f'<div class="abstract"><b>Abstract:</b> {paper.get("abstract", "")}</div>'
            
        # Add all the additional analysis sections
        for key, value in paper.items():
            if key in ["title", "authors", "subjects", "main_page", "Relevancy score", "Reasons for match", 
                      "design_category", "design_techniques", "content", "abstract"]:
                continue
            
            if isinstance(value, str) and value.strip():
                html += f'<div class="section"><div class="section-title">{key}:</div> {value}</div>'
        
        # Add links
        html += f"""
            <div class="links">
                <a href="{paper.get("pdf", paper.get("main_page", "#") + ".pdf")}" target="_blank">PDF</a> | 
                <a href="{paper.get("main_page", "#")}" target="_blank">arXiv</a>
            </div>
        </div>
        """
    
    html += f"""
        <div class="footer">
            <p>Generated by ArXiv Design Papers Finder on {datetime.datetime.now().strftime("%Y-%m-%d")}</p>
            <p>Search period: Last {days_back} days</p>
            {f'<p>Keyword filter: {keyword}</p>' if keyword else ''}
        </div>
    </body>
    </html>
    """
    
    with open(output_file, "w") as f:
        f.write(html)
    
    logger.info(f"HTML report generated: {output_file}")

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
    print(f"\nABSTRACT: {paper.get('abstract', 'No abstract')[:500]}...")
    print(f"{'=' * 80}\n")

def analyze_papers_with_llm(papers: List[Dict[str, Any]], research_interest: str) -> List[Dict[str, Any]]:
    """
    Analyze papers using LLM to provide detailed analysis
    
    Args:
        papers: List of paper dictionaries
        research_interest: Description of research interests
        
    Returns:
        Enhanced list of papers with detailed analysis
    """
    if not papers:
        return papers
        
    # Check if model_manager is properly initialized
    if not model_manager.is_provider_available(ModelProvider.OPENAI):
        # Try to get OpenAI key from environment
        import os
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            model_manager.register_openai(openai_key)
        else:
            logger.warning("No OpenAI API key available. Skipping detailed analysis.")
            return papers
            
    logger.info(f"Analyzing {len(papers)} papers with LLM...")
    
    # Default research interest for design papers if none provided
    if not research_interest:
        research_interest = """
        I'm interested in papers that use AI/ML for design automation, including:
        1. Generative design systems for graphics, UI/UX, and layouts
        2. ML-enhanced creative tools and design assistants
        3. Novel techniques for automating design processes
        4. Human-AI collaborative design workflows
        5. Applications of LLMs, diffusion models, and GANs to design tasks
        """
    
    # Analyze papers using model_manager
    try:
        analyzed_papers, _ = model_manager.analyze_papers(
            papers,
            query={"interest": research_interest},
            providers=[ModelProvider.OPENAI],
            model_names={ModelProvider.OPENAI: "gpt-3.5-turbo-16k"},
            threshold_score=0  # Include all papers, even low scored ones
        )
        return analyzed_papers
    except Exception as e:
        logger.error(f"Error during LLM analysis: {e}")
        return papers

def pre_filter_category(category: str, keyword: str = None) -> bool:
    """
    Check if a category is likely to contain design-related papers
    to avoid downloading irrelevant categories.
    
    Args:
        category: arXiv category code
        keyword: Optional search keyword
        
    Returns:
        Boolean indicating whether to include this category
    """
    # Always include these categories as they're highly relevant
    high_relevance = ["cs.GR", "cs.HC", "cs.CV", "cs.MM", "cs.SD"]
    
    if category in high_relevance:
        return True
        
    # If we have a keyword, we need to be less strict to avoid missing papers
    if keyword:
        return True
        
    # Medium relevance categories - include for comprehensive searches
    medium_relevance = ["cs.AI", "cs.LG", "cs.CL", "cs.RO", "cs.CY"]
    return category in medium_relevance

def main():
    parser = argparse.ArgumentParser(description="Find the latest graphic design automation papers.")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--output", type=str, help="Output JSON file path (date will be added automatically)")
    parser.add_argument("--html", type=str, help="HTML output file path (date will be added automatically)")
    parser.add_argument("--categories", type=str, nargs="+", default=DEFAULT_CATEGORIES, 
                      help="arXiv categories to search")
    parser.add_argument("--keyword", type=str, help="Additional keyword to filter papers")
    parser.add_argument("--analyze", action="store_true", help="Use LLM to perform detailed analysis of papers")
    parser.add_argument("--interest", type=str, help="Research interest description for LLM analysis")
    parser.add_argument("--model", type=str, default="gpt-3.5-turbo-16k", help="Model to use for analysis")
    parser.add_argument("--no-date", action="store_true", help="Disable adding date to filenames")
    args = parser.parse_args()
    
    # Generate date string for filenames
    current_date = datetime.datetime.now().strftime("%Y%m%d")
    
    # Set default filenames with dates if not provided
    if args.output is None:
        base_filename = "design_papers"
        if args.keyword:
            # Add keyword to filename if provided
            base_filename = f"design_papers_{args.keyword.lower().replace(' ', '_')}"
            
        if not args.no_date:
            args.output = os.path.join(DATA_DIR, f"{base_filename}_{current_date}.json")
        else:
            args.output = os.path.join(DATA_DIR, f"{base_filename}.json")
    
    if args.html is None:
        base_filename = "design_papers"
        if args.keyword:
            # Add keyword to filename if provided
            base_filename = f"design_papers_{args.keyword.lower().replace(' ', '_')}"
            
        if not args.no_date:
            args.html = os.path.join(DIGEST_DIR, f"{base_filename}_{current_date}.html")
        else:
            args.html = os.path.join(DIGEST_DIR, f"{base_filename}.html")
    
    logger.info(f"Looking for design papers in the past {args.days} days")
    
    # Apply pre-filtering to categories
    filtered_categories = [cat for cat in args.categories if pre_filter_category(cat, args.keyword)]
    logger.info(f"Pre-filtered categories: {', '.join(filtered_categories)}")
    
    # Get papers for each category and date
    dates = get_date_range(args.days)
    all_papers = []
    
    for category in filtered_categories:
        for date_str in dates:
            try:
                papers = download_papers(category, date_str)
                # Apply keyword filter immediately if provided
                if args.keyword:
                    keyword = args.keyword.lower()
                    papers = [
                        p for p in papers 
                        if keyword in p.get("title", "").lower() or 
                           keyword in p.get("abstract", "").lower() or
                           keyword in p.get("subjects", "").lower()
                    ]
                    logger.info(f"Found {len(papers)} papers matching keyword '{args.keyword}' in {category}")
                
                all_papers.extend(papers)
                # Avoid hitting arXiv rate limits
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error downloading papers for {category} on {date_str}: {e}")
    
    # Remove duplicates (papers can appear in multiple categories)
    unique_papers = {}
    for paper in all_papers:
        paper_id = paper.get("main_page", "").split("/")[-1]
        if paper_id and paper_id not in unique_papers:
            unique_papers[paper_id] = paper
    
    all_papers = list(unique_papers.values())
    
    # Filter for design automation papers
    design_papers = []
    for paper in all_papers:
        if is_design_automation_paper(paper):
            paper["design_category"] = categorize_design_paper(paper)
            paper["design_techniques"] = analyze_design_techniques(paper)
            design_papers.append(paper)
    
    # Sort by date
    design_papers.sort(key=lambda p: p.get("main_page", ""), reverse=True)
    logger.info(f"Found {len(design_papers)} design automation papers")
    
    # Add detailed analysis with LLM if requested
    if args.analyze and design_papers:
        design_papers = analyze_papers_with_llm(design_papers, args.interest)
        logger.info("Completed LLM analysis of papers")
        
        # Debug: Print out the analysis fields for the first paper
        if design_papers:
            logger.info(f"Paper analysis fields: {list(design_papers[0].keys())}")
            # If 'Key innovations' is present, it confirms we have the detailed analysis
            if 'Key innovations' in design_papers[0]:
                logger.info("Detailed analysis fields present!")
            else:
                logger.warning("Detailed analysis fields missing!")
    
    # Print summary to console
    for paper in design_papers[:10]:  # Print top 10
        print_paper_summary(paper)
    
    if len(design_papers) > 10:
        print(f"...and {len(design_papers) - 10} more papers.")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    # Save to file
    with open(args.output, "w") as f:
        json.dump(design_papers, f, indent=2)
    
    # Generate HTML report
    generate_html_report(design_papers, args.html, args.keyword, args.days)
    
    logger.info(f"Saved {len(design_papers)} papers to {args.output}")
    print(f"\nResults saved to {args.output} and {args.html}")
    
    if args.analyze:
        print("\nPapers have been analyzed with LLM for detailed information.")
        print("The HTML report includes comprehensive analysis of each paper.")

if __name__ == "__main__":
    main()