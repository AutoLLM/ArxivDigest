"""
Module for analyzing papers related to AI/ML for graphic design automation.
This module helps identify and analyze papers on automated design, layout generation,
creative AI tools, and related topics.
"""
import logging
import json
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Design automation keywords for paper filtering
DESIGN_AUTOMATION_KEYWORDS = [
    "design automation", "layout generation", "visual design", "graphic design",
    "creative AI", "generative design", "UI generation", "UX automation",
    "design system", "composition", "creative workflow", "automated design",
    "design tool", "design assistant", "design optimization", "content-aware",
    "user interface generation", "visual layout", "image composition"
]

DESIGN_AUTOMATION_PROMPT = """
You are a specialized research assistant focused on AI/ML for graphic design automation.

Analyze this paper from the perspective of AI for graphic design and creative automation:

Title: {title}
Authors: {authors}
Abstract: {abstract}
Content: {content}

Please provide a detailed analysis covering:

1. Design automation focus: What aspect of design does this paper attempt to automate or enhance?
2. Technical approach: What AI/ML techniques are used in the paper for design automation?
3. Visual outputs: What kind of visual artifacts does the system generate?
4. Designer interaction: How does the system interact with human designers?
5. Data requirements: What data does the system use for training or operation?
6. Evaluation metrics: How is the system's design quality evaluated?
7. Real-world applicability: How practical is this approach for professional design workflows?
8. Novelty: What makes this approach unique compared to other design automation systems?
9. Limitations: What are the current limitations of this approach?
10. Future directions: What improvements or extensions are suggested?

Format your response as JSON with these fields.
"""

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
        if any(keyword.lower() in text for keyword in keywords):
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

def extract_design_metrics(paper: Dict[str, Any]) -> List[str]:
    """
    Extract evaluation metrics used for design quality assessment.
    
    Args:
        paper: Dictionary with paper details
        
    Returns:
        List of metrics
    """
    text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
    
    metrics = []
    metric_keywords = {
        "User Studies": ["user study", "user evaluation", "human evaluation"],
        "Aesthetic Measures": ["aesthetic", "beauty", "visual quality"],
        "Design Principles": ["design principle", "balance", "harmony", "contrast"],
        "Technical Metrics": ["fid", "inception score", "clip score", "psnr"],
        "Efficiency Metrics": ["time", "speed", "efficiency"],
        "Usability": ["usability", "user experience", "ux", "ease of use"]
    }
    
    for metric, keywords in metric_keywords.items():
        if any(keyword in text for keyword in keywords):
            metrics.append(metric)
    
    return metrics

def get_related_design_papers(paper_id: str, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Find papers related to a specific design automation paper.
    
    Args:
        paper_id: ID of the target paper
        papers: List of paper dictionaries
        
    Returns:
        List of related papers
    """
    target_paper = next((p for p in papers if p.get("main_page", "").endswith(paper_id)), None)
    if not target_paper:
        return []
    
    # Get techniques used in target paper
    target_techniques = analyze_design_techniques(target_paper)
    target_category = categorize_design_paper(target_paper)
    
    related_papers = []
    for paper in papers:
        if paper.get("main_page", "") == target_paper.get("main_page", ""):
            continue
            
        # Check if paper is on design automation
        if not is_design_automation_paper(paper):
            continue
            
        # Check if techniques or categories overlap
        paper_techniques = analyze_design_techniques(paper)
        paper_category = categorize_design_paper(paper)
        
        technique_overlap = len(set(target_techniques) & set(paper_techniques))
        category_match = paper_category == target_category
        
        if technique_overlap > 0 or category_match:
            paper["relevance_reason"] = []
            
            if technique_overlap > 0:
                paper["relevance_reason"].append(f"Uses similar techniques: {', '.join(set(target_techniques) & set(paper_techniques))}")
                
            if category_match:
                paper["relevance_reason"].append(f"Same design category: {paper_category}")
                
            paper["relevance_score"] = (technique_overlap * 2) + (2 if category_match else 0)
            related_papers.append(paper)
    
    # Sort by relevance score
    related_papers.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return related_papers[:5]  # Return top 5 related papers

def create_design_analysis_prompt(paper: Dict[str, Any]) -> str:
    """
    Create a prompt for analyzing a design automation paper.
    
    Args:
        paper: Dictionary with paper details
        
    Returns:
        Formatted prompt string
    """
    return DESIGN_AUTOMATION_PROMPT.format(
        title=paper.get("title", ""),
        authors=paper.get("authors", ""),
        abstract=paper.get("abstract", ""),
        content=paper.get("content", "")[:10000]  # Limit content length
    )

def extract_design_capabilities(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract specific design capabilities from an analysis.
    
    Args:
        analysis: Dictionary with design paper analysis
        
    Returns:
        Dictionary of design capabilities
    """
    capabilities = {}
    
    # Extract design areas
    if "Design automation focus" in analysis:
        capabilities["design_areas"] = analysis["Design automation focus"]
    
    # Extract tools that could be replaced
    tools = []
    tools_keywords = {
        "Adobe Photoshop": ["photoshop", "photo editing", "image manipulation"],
        "Adobe Illustrator": ["illustrator", "vector", "illustration"],
        "Figma": ["figma", "ui design", "interface design"],
        "Sketch": ["sketch", "ui design", "interface design"],
        "InDesign": ["indesign", "layout", "publishing"],
        "Canva": ["canva", "simple design", "templates"]
    }
    
    for text_field in ["Technical approach", "Design automation focus", "Real-world applicability"]:
        if text_field in analysis:
            text = analysis[text_field].lower()
            for tool, keywords in tools_keywords.items():
                if any(keyword in text for keyword in keywords):
                    tools.append(tool)
    
    capabilities["replaceable_tools"] = list(set(tools))
    
    # Extract human-in-the-loop vs fully automated
    if "Designer interaction" in analysis:
        text = analysis["Designer interaction"].lower()
        if "fully automated" in text or "automatic" in text or "without human" in text:
            capabilities["automation_level"] = "Fully automated"
        elif "human-in-the-loop" in text or "collaboration" in text or "assists" in text:
            capabilities["automation_level"] = "Human-in-the-loop"
        else:
            capabilities["automation_level"] = "Hybrid"
    
    # Extract if it's ready for production
    if "Real-world applicability" in analysis:
        text = analysis["Real-world applicability"].lower()
        if "production ready" in text or "commercially viable" in text or "can be used in real" in text:
            capabilities["production_ready"] = True
        elif "prototype" in text or "proof of concept" in text or "research" in text or "limitations" in text:
            capabilities["production_ready"] = False
        else:
            capabilities["production_ready"] = "Unclear"
    
    return capabilities