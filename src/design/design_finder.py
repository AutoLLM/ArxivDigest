#!/usr/bin/env python3
"""
Design Finder - A self-contained script to find AI/ML design automation papers on arXiv.

This script requires only Python standard libraries and BeautifulSoup, making it very easy to run
without complex dependencies.

Usage:
    python design_finder.py [--days 7] [--output design_papers.json]
"""

import os
import sys
import json
import argparse
import datetime
import re
import time
import urllib.request
from typing import List, Dict, Any

# Check for BeautifulSoup
try:
    from bs4 import BeautifulSoup as bs
except ImportError:
    print("BeautifulSoup not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup as bs

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
    "user interface generation", "visual layout", "image composition", "AI design"
]

class DesignPaperFinder:
    def __init__(self, days_back=7, categories=None, output_file="design_papers.json", 
                 html_file="design_papers.html", keyword=None, verbose=True):
        self.days_back = days_back
        self.categories = categories or DEFAULT_CATEGORIES
        self.output_file = output_file
        self.html_file = html_file
        self.keyword = keyword
        self.verbose = verbose
        self.papers = []
        
        # Data directory is already created by paths.py module
        
    def log(self, message):
        """Print a message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def get_date_range(self) -> List[str]:
        """Get list of dates to search in arXiv format."""
        today = datetime.datetime.now()
        dates = []
        
        for i in range(self.days_back):
            date = today - datetime.timedelta(days=i)
            date_str = date.strftime("%a, %d %b %y")
            dates.append(date_str)
            
        return dates
    
    def download_papers(self, category: str, date_str: str) -> List[Dict[str, Any]]:
        """Download papers for a specific category and date."""
        # Check if we already have this data
        # Import data directory at runtime to avoid circular imports
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from paths import DATA_DIR
        file_path = os.path.join(DATA_DIR, f"{category}_{date_str}.jsonl")
        if os.path.exists(file_path):
            self.log(f"Loading cached papers for {category} on {date_str}")
            papers = []
            with open(file_path, "r") as f:
                for line in f:
                    papers.append(json.loads(line))
            return papers
        
        # Download new papers
        self.log(f"Downloading papers for {category} on {date_str}")
        NEW_SUB_URL = f'https://arxiv.org/list/{category}/new'
        
        try:
            page = urllib.request.urlopen(NEW_SUB_URL)
        except Exception as e:
            self.log(f"Error downloading from {NEW_SUB_URL}: {e}")
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
                    html = urllib.request.urlopen(arxiv_html + paper_number + "v1")
                    soup_content = bs(html, 'html.parser')
                    content_div = soup_content.find('div', attrs={'class': 'ltx_page_content'})
                    if content_div:
                        para_list = content_div.find_all("div", attrs={'class': 'ltx_para'})
                        excerpt = ' '.join([p.text.strip() for p in para_list[:3]])  # Get first 3 paragraphs
                        paper['content_excerpt'] = excerpt[:1000] + "..." if len(excerpt) > 1000 else excerpt
                    else:
                        paper['content_excerpt'] = "Content not available"
                except Exception:
                    paper['content_excerpt'] = ""
                
                papers.append(paper)
            except Exception as e:
                if self.verbose:
                    self.log(f"Error processing paper {i}: {e}")
        
        # Save papers to file
        with open(file_path, "w") as f:
            for paper in papers:
                f.write(json.dumps(paper) + "\n")
        
        return papers
    
    def is_design_automation_paper(self, paper: Dict[str, Any]) -> bool:
        """Check if a paper is related to design automation based on keywords."""
        text = (
            (paper.get("title", "") + " " + 
             paper.get("abstract", "") + " " + 
             paper.get("subjects", "")).lower()
        )
        
        return any(keyword.lower() in text for keyword in DESIGN_AUTOMATION_KEYWORDS)
    
    def categorize_design_paper(self, paper: Dict[str, Any]) -> str:
        """Categorize design automation paper into subcategories."""
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
    
    def analyze_design_techniques(self, paper: Dict[str, Any]) -> List[str]:
        """Extract AI/ML techniques used for design automation in the paper."""
        text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
        
        techniques = []
        technique_keywords = {
            "Generative Adversarial Networks": ["gan", "generative adversarial"],
            "Diffusion Models": ["diffusion", "ddpm", "stable diffusion"],
            "Transformers": ["transformer", "attention mechanism"],
            "Reinforcement Learning": ["reinforcement learning", "rl"],
            "Computer Vision": ["computer vision", "vision", "cnn"],
            "Graph Neural Networks": ["graph neural", "gnn"],
            "Large Language Models": ["llm", "large language model", "gpt", "chatgpt"],
            "Neural Style Transfer": ["style transfer", "neural style"],
            "Evolutionary Algorithms": ["genetic algorithm", "evolutionary"]
        }
        
        for technique, keywords in technique_keywords.items():
            if any(keyword in text for keyword in keywords):
                techniques.append(technique)
        
        return techniques
    
    def find_papers(self):
        """Find design automation papers from arXiv."""
        self.log(f"Looking for design papers in the past {self.days_back} days")
        self.log(f"Searching categories: {', '.join(self.categories)}")
        
        # Get papers for each category and date
        dates = self.get_date_range()
        all_papers = []
        
        for category in self.categories:
            for date_str in dates:
                try:
                    papers = self.download_papers(category, date_str)
                    all_papers.extend(papers)
                    # Avoid hitting arXiv rate limits
                    time.sleep(3)
                except Exception as e:
                    self.log(f"Error downloading papers for {category} on {date_str}: {e}")
        
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
            if self.is_design_automation_paper(paper):
                paper["design_category"] = self.categorize_design_paper(paper)
                paper["design_techniques"] = self.analyze_design_techniques(paper)
                design_papers.append(paper)
        
        # Additional keyword filtering if specified
        if self.keyword:
            keyword = self.keyword.lower()
            design_papers = [
                p for p in design_papers 
                if keyword in p.get("title", "").lower() or 
                   keyword in p.get("abstract", "").lower()
            ]
        
        # Sort by date
        design_papers.sort(key=lambda p: p.get("main_page", ""), reverse=True)
        
        self.papers = design_papers
        self.log(f"Found {len(design_papers)} design automation papers")
        return design_papers
    
    def print_paper_summary(self, paper: Dict[str, Any]):
        """Print a nice summary of a paper to the console."""
        print(f"\n{'=' * 80}")
        print(f"TITLE: {paper.get('title', 'No title')}")
        print(f"AUTHORS: {paper.get('authors', 'No authors')}")
        print(f"URL: {paper.get('main_page', 'No URL')}")
        print(f"DESIGN CATEGORY: {paper.get('design_category', 'Unknown')}")
        print(f"TECHNIQUES: {', '.join(paper.get('design_techniques', []))}")
        print(f"\nABSTRACT: {paper.get('abstract', 'No abstract')[:500]}...")
        print(f"{'=' * 80}\n")
    
    def generate_html_report(self):
        """Generate an HTML report from papers."""
        if not self.papers:
            self.log("No papers to generate HTML report from")
            return
            
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
                a {{ color: #2980b9; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .stats {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #7f8c8d; text-align: center; }}
                h1 {{ color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
                .nav {{ position: fixed; top: 10px; right: 10px; background: white; border: 1px solid #ddd; 
                        padding: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .nav a {{ display: block; margin: 5px 0; }}
            </style>
        </head>
        <body>
            <h1>Design Automation Papers</h1>
            <div class="nav">
                <a href="#stats">Statistics</a>
                <a href="#papers">All Papers</a>
            </div>
            <div class="stats">
                <p>Found {len(self.papers)} papers related to graphic design automation with AI/ML</p>
                <p>Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p>Keywords: {', '.join(DESIGN_AUTOMATION_KEYWORDS[:5])}...</p>
            </div>
        """
        
        # Count categories and techniques
        categories = {}
        techniques = {}
        
        for paper in self.papers:
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
        html += '<div class="stats" id="stats"><h2>Summary Statistics</h2>'
        
        html += "<h3>Categories:</h3><ul>"
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            html += f"<li>{category}: {count} papers</li>"
        html += "</ul>"
        
        html += "<h3>Techniques:</h3><ul>"
        for technique, count in sorted(techniques.items(), key=lambda x: x[1], reverse=True):
            html += f"<li>{technique}: {count} papers</li>"
        html += "</ul></div>"
        
        # Add papers
        html += '<h2 id="papers">Papers</h2>'
        for paper in self.papers:
            html += f"""
            <div class="paper">
                <div class="title"><a href="{paper.get("main_page", "#")}" target="_blank">{paper.get("title", "No title")}</a></div>
                <div class="authors">{paper.get("authors", "Unknown authors")}</div>
                <div class="categories">Category: {paper.get("design_category", "General")} | Subject: {paper.get("subjects", "N/A")}</div>
                <div class="techniques">Techniques: {', '.join(paper.get("design_techniques", ["None identified"]))}</div>
                <div class="abstract"><strong>Abstract:</strong> {paper.get("abstract", "No abstract available")}</div>
                <div>
                    <a href="{paper.get("pdf", "#")}" target="_blank">PDF</a> | 
                    <a href="{paper.get("main_page", "#")}" target="_blank">arXiv</a>
                </div>
            </div>
            """
        
        html += """
            <div class="footer">
                <p>Generated by Design Papers Finder</p>
            </div>
        </body>
        </html>
        """
        
        with open(self.html_file, "w") as f:
            f.write(html)
        
        self.log(f"HTML report generated: {self.html_file}")
    
    def save_json(self):
        """Save papers to JSON file."""
        if not self.papers:
            self.log("No papers to save")
            return
            
        with open(self.output_file, "w") as f:
            json.dump(self.papers, f, indent=2)
        
        self.log(f"Saved {len(self.papers)} papers to {self.output_file}")
    
    def run(self):
        """Run the full paper finding process."""
        self.find_papers()
        
        if not self.papers:
            print("No design automation papers found.")
            return
        
        # Print summary of top papers
        for paper in self.papers[:10]:  # Print top 10
            self.print_paper_summary(paper)
        
        if len(self.papers) > 10:
            print(f"...and {len(self.papers) - 10} more papers.")
        
        # Save outputs
        self.save_json()
        self.generate_html_report()
        
        print(f"\nResults saved to {self.output_file} and {self.html_file}")
        print(f"Open {self.html_file} in your browser to view the report.")

def main():
    parser = argparse.ArgumentParser(description="Find the latest graphic design automation papers.")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--output", type=str, default="design_papers.json", help="Output file path")
    parser.add_argument("--html", type=str, default="design_papers.html", help="HTML output file path")
    parser.add_argument("--categories", type=str, nargs="+", default=DEFAULT_CATEGORIES, 
                      help="arXiv categories to search")
    parser.add_argument("--keyword", type=str, help="Additional keyword to filter papers")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress messages")
    args = parser.parse_args()
    
    finder = DesignPaperFinder(
        days_back=args.days,
        categories=args.categories,
        output_file=args.output,
        html_file=args.html,
        keyword=args.keyword,
        verbose=not args.quiet
    )
    
    finder.run()

if __name__ == "__main__":
    main()