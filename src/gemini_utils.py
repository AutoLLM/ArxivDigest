"""
Gemini API integration for ArxivDigest.
This module provides functions to work with Google's Gemini API for paper analysis.
"""
import os
import json
import logging
import time
from typing import List, Dict, Any, Optional

try:
    import google.generativeai as genai
    from google.api_core.exceptions import GoogleAPIError
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiConfig:
    """Configuration for Gemini API calls."""
    def __init__(
        self,
        temperature: float = 0.4,
        max_output_tokens: int = 2048,
        top_p: float = 0.95,
        top_k: int = 40
    ):
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.top_p = top_p
        self.top_k = top_k

def setup_gemini_api(api_key: str) -> bool:
    """
    Setup the Gemini API with the provided API key.
    
    Args:
        api_key: Gemini API key
        
    Returns:
        bool: True if setup was successful, False otherwise
    """
    if not GEMINI_AVAILABLE:
        logger.error("Gemini package not installed. Run 'pip install google-generativeai'")
        return False
        
    if not api_key:
        logger.error("No Gemini API key provided")
        return False
        
    try:
        genai.configure(api_key=api_key)
        # Test API connection
        models = genai.list_models()
        logger.info(f"Successfully connected to Gemini API. Available models: {[m.name for m in models if 'generateContent' in m.supported_generation_methods]}")
        return True
    except Exception as e:
        logger.error(f"Failed to setup Gemini API: {e}")
        return False

def get_gemini_model(model_name: str = "gemini-1.5-flash"):
    """
    Get a Gemini model by name.
    
    Args:
        model_name: Name of the Gemini model
        
    Returns:
        Model object or None if not available
    """
    if not GEMINI_AVAILABLE:
        return None
        
    try:
        model = genai.GenerativeModel(model_name)
        return model
    except Exception as e:
        logger.error(f"Failed to get Gemini model: {e}")
        return None

def analyze_papers_with_gemini(
    papers: List[Dict[str, Any]], 
    query: Dict[str, str],
    config: Optional[GeminiConfig] = None,
    model_name: str = "gemini-1.5-flash"
) -> List[Dict[str, Any]]:
    """
    Analyze papers using the Gemini model.
    
    Args:
        papers: List of paper dictionaries
        query: Dictionary with 'interest' key describing research interests
        config: GeminiConfig object
        model_name: Name of the Gemini model to use
        
    Returns:
        List of papers with added analysis
    """
    if not GEMINI_AVAILABLE:
        logger.error("Gemini package not installed. Cannot analyze papers.")
        return papers
        
    if not config:
        config = GeminiConfig()
        
    model = get_gemini_model(model_name)
    if not model:
        return papers
        
    analyzed_papers = []
    
    for paper in papers:
        try:
            # Prepare prompt
            prompt = f"""
            You are a research assistant analyzing academic papers in AI and ML.
            
            Analyze this paper and provide insights based on the user's research interests.
            
            Research interests: {query['interest']}
            
            Paper details:
            Title: {paper['title']}
            Authors: {paper['authors']}
            Abstract: {paper['abstract']}
            Content: {paper['content'][:5000]}
            
            Please provide your response as a single JSON object with the following structure:
            {{
              "Relevancy score": 1-10 (higher = more relevant),
              "Reasons for match": "Detailed explanation of why this paper matches the interests",
              "Key innovations": "List the main contributions of the paper",
              "Critical analysis": "Evaluate strengths and weaknesses",
              "Goal": "What problem does the paper address?",
              "Data": "Description of datasets used",
              "Methodology": "Technical approach and methods",
              "Implementation details": "Model architecture, hyperparameters, etc.",
              "Experiments & Results": "Key findings and comparisons",
              "Discussion & Next steps": "Limitations and future work",
              "Related work": "Connection to similar research",
              "Practical applications": "Real-world uses of this research",
              "Key takeaways": ["Point 1", "Point 2", "Point 3"]
            }}
            
            Format your response as a valid JSON object and nothing else.
            """
            
            # Just log that we're sending a prompt to Gemini
            print(f"Sending prompt to Gemini for paper: {paper['title'][:50]}...")
            
            generation_config = {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "max_output_tokens": config.max_output_tokens,
            }
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract and parse the response
            response_text = response.text
            
            # Try to extract JSON
            try:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    gemini_analysis = json.loads(json_str)
                    
                    # Add Gemini analysis to paper
                    paper['gemini_analysis'] = gemini_analysis
                    
                    # Directly copy fields to paper
                    for key, value in gemini_analysis.items():
                        paper[key] = value
                else:
                    logger.warning(f"Could not extract JSON from Gemini response for paper {paper['title']}")
                    paper['gemini_analysis'] = {"error": "Failed to parse response"}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Gemini response as JSON for paper {paper['title']}")
                paper['gemini_analysis'] = {"error": "Failed to parse response"}
                
            analyzed_papers.append(paper)
            
            # Avoid rate limiting
            time.sleep(1)
            
        except GoogleAPIError as e:
            logger.error(f"Gemini API error: {e}")
            paper['gemini_analysis'] = {"error": f"Gemini API error: {str(e)}"}
            analyzed_papers.append(paper)
            
        except Exception as e:
            logger.error(f"Error analyzing paper with Gemini: {e}")
            paper['gemini_analysis'] = {"error": f"Error: {str(e)}"}
            analyzed_papers.append(paper)
            
    return analyzed_papers

def get_topic_clustering(papers: List[Dict[str, Any]], model_name: str = "gemini-1.5-flash"):
    """
    Cluster papers by topic using Gemini.
    
    Args:
        papers: List of paper dictionaries
        model_name: Name of the Gemini model to use
        
    Returns:
        Dictionary with topic clusters
    """
    if not GEMINI_AVAILABLE:
        logger.error("Gemini package not installed. Cannot cluster papers.")
        return {}
        
    model = get_gemini_model(model_name)
    if not model:
        return {}
        
    # Create a condensed representation of the papers
    paper_summaries = []
    for i, paper in enumerate(papers):
        paper_summaries.append(f"{i+1}. Title: {paper['title']}\nAbstract: {paper['abstract'][:300]}...")
    
    paper_text = "\n\n".join(paper_summaries)
    
    prompt = f"""
    You are a research librarian organizing academic papers into topic clusters.
    
    Analyze these papers and group them into 3-7 thematic clusters:
    
    {paper_text}
    
    For each cluster:
    1. Provide a descriptive name for the cluster
    2. List the paper numbers that belong to this cluster
    3. Explain why these papers belong together
    
    Format your response as JSON with these fields: "clusters" (an array of objects with "name", "papers", and "description" fields).
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Try to extract JSON
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                cluster_data = json.loads(json_str)
                return cluster_data
            else:
                logger.warning("Could not extract JSON from Gemini clustering response")
                return {"error": "Failed to parse clustering response"}
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini clustering response as JSON")
            return {"error": "Failed to parse clustering response"}
            
    except Exception as e:
        logger.error(f"Error clustering papers with Gemini: {e}")
        return {"error": f"Clustering error: {str(e)}"}