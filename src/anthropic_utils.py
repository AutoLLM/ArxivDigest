"""
Anthropic/Claude API integration for ArxivDigest.
This module provides functions to work with Anthropic's Claude API for paper analysis.
"""
import os
import json
import logging
import time
from typing import List, Dict, Any, Optional

try:
    import anthropic
    from anthropic.types import MessageParam
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaudeConfig:
    """Configuration for Claude API calls."""
    def __init__(
        self,
        temperature: float = 0.5,
        max_tokens: int = 4000,
        top_p: float = 0.95,
        top_k: int = 40
    ):
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.top_k = top_k

def setup_anthropic_api(api_key: str) -> bool:
    """
    Setup the Anthropic API with the provided API key.
    
    Args:
        api_key: Anthropic API key
        
    Returns:
        bool: True if setup was successful, False otherwise
    """
    if not ANTHROPIC_AVAILABLE:
        logger.error("Anthropic package not installed. Run 'pip install anthropic'")
        return False
        
    if not api_key:
        logger.error("No Anthropic API key provided")
        return False
        
    try:
        # Initialize client to test connection
        client = anthropic.Anthropic(api_key=api_key)
        # Test API connection by listing models
        models = client.models.list()
        available_models = [model.id for model in models.data]
        logger.info(f"Successfully connected to Anthropic API. Available models: {available_models}")
        return True
    except Exception as e:
        logger.error(f"Failed to setup Anthropic API: {e}")
        return False

def get_claude_client(api_key: str) -> Optional[anthropic.Anthropic]:
    """
    Get an Anthropic client with the given API key.
    
    Args:
        api_key: Anthropic API key
        
    Returns:
        Anthropic client or None if not available
    """
    if not ANTHROPIC_AVAILABLE:
        return None
        
    try:
        client = anthropic.Anthropic(api_key=api_key)
        return client
    except Exception as e:
        logger.error(f"Failed to get Anthropic client: {e}")
        return None

def analyze_papers_with_claude(
    papers: List[Dict[str, Any]], 
    query: Dict[str, str],
    config: Optional[ClaudeConfig] = None,
    model_name: str = "claude-3.5-sonnet-20240620",
    api_key: str = None
) -> List[Dict[str, Any]]:
    """
    Analyze papers using Claude.
    
    Args:
        papers: List of paper dictionaries
        query: Dictionary with 'interest' key describing research interests
        config: ClaudeConfig object
        model_name: Name of the Claude model to use
        api_key: Anthropic API key (optional if already configured elsewhere)
        
    Returns:
        List of papers with added analysis
    """
    if not ANTHROPIC_AVAILABLE:
        logger.error("Anthropic package not installed. Cannot analyze papers.")
        return papers
        
    if not config:
        config = ClaudeConfig()
        
    # Get client
    if api_key:
        client = get_claude_client(api_key)
    else:
        # Try to get from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.error("No Anthropic API key provided")
            return papers
        client = get_claude_client(api_key)
        
    if not client:
        return papers
        
    analyzed_papers = []
    
    for paper in papers:
        try:
            # Prepare system prompt
            system_prompt = f"""
            You are a research assistant analyzing academic papers in AI and ML.
            You provide comprehensive, accurate and unbiased analysis based on the user's research interests.
            Your responses should be well-structured and factual, focusing on the paper's strengths, weaknesses, and relevance.
            """
            
            # Prepare user prompt
            user_prompt = f"""
            Analyze this paper and provide insights based on the following research interests:
            
            Research interests: {query['interest']}
            
            Paper details:
            Title: {paper['title']}
            Authors: {paper['authors']}
            Abstract: {paper['abstract']}
            Content: {paper['content'][:5000] if 'content' in paper else 'Not available'}
            
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
            
            # Just log that we're sending a prompt to Claude
            print(f"Sending prompt to Claude for paper: {paper['title'][:50]}...")
            
            # Create message
            messages: List[MessageParam] = [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
            
            # Call the API
            response = client.messages.create(
                model=model_name,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system=system_prompt,
                messages=messages
            )
            
            # Extract and parse the response
            response_text = response.content[0].text if response.content else ""
            
            # Try to extract JSON
            try:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    claude_analysis = json.loads(json_str)
                    
                    # Add Claude analysis to paper
                    paper['claude_analysis'] = claude_analysis
                    
                    # Directly copy fields to paper
                    for key, value in claude_analysis.items():
                        paper[key] = value
                else:
                    logger.warning(f"Could not extract JSON from Claude response for paper {paper['title']}")
                    paper['claude_analysis'] = {"error": "Failed to parse response"}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Claude response as JSON for paper {paper['title']}")
                paper['claude_analysis'] = {"error": "Failed to parse response"}
                
            analyzed_papers.append(paper)
            
            # Avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            paper['claude_analysis'] = {"error": f"Claude API error: {str(e)}"}
            analyzed_papers.append(paper)
            
    return analyzed_papers

def get_claude_interpretability_analysis(paper: Dict[str, Any], model_name: str = "claude-3.5-sonnet-20240620", api_key: str = None) -> Dict[str, Any]:
    """
    Get specialized mechanistic interpretability analysis for a paper using Claude.
    
    Args:
        paper: Paper dictionary
        model_name: Claude model to use
        api_key: Anthropic API key (optional if already configured elsewhere)
        
    Returns:
        Dictionary with interpretability analysis
    """
    if not ANTHROPIC_AVAILABLE:
        return {"error": "Anthropic package not installed"}
        
    # Get client
    if api_key:
        client = get_claude_client(api_key)
    else:
        # Try to get from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"error": "No Anthropic API key provided"}
        client = get_claude_client(api_key)
        
    if not client:
        return {"error": "Failed to initialize Anthropic client"}
        
    try:
        # Prepare system prompt
        system_prompt = """
        You are a specialist in mechanistic interpretability and AI alignment.
        Provide a thorough analysis of research papers with focus on interpretability methods, 
        circuit analysis, and how the work relates to understanding AI systems.
        """
        
        # Prepare the prompt
        user_prompt = f"""
        Analyze this paper from a mechanistic interpretability perspective:
        
        Title: {paper['title']}
        Authors: {paper['authors']}
        Abstract: {paper['abstract']}
        Content: {paper['content'][:7000] if 'content' in paper else paper['abstract']}
        
        Please return your analysis as a JSON object with the following fields:
        
        {{
          "interpretability_score": 1-10 (how relevant is this to mechanistic interpretability),
          "key_methods": "Main interpretability techniques used or proposed",
          "circuit_analysis": "Any findings about neural circuits or components",
          "relevance_to_alignment": "How this work contributes to AI alignment",
          "novel_insights": "New perspectives on model internals",
          "limitations": "Limitations of the interpretability methods",
          "potential_extensions": "How this work could be extended",
          "connection_to_other_work": "Relationship to other interpretability papers"
        }}
        
        Respond with only the JSON.
        """
        
        # Create message
        messages: List[MessageParam] = [
            {
                "role": "user",
                "content": user_prompt
            }
        ]
        
        # Call the API
        response = client.messages.create(
            model=model_name,
            max_tokens=4000,
            temperature=0.3,
            system=system_prompt,
            messages=messages
        )
        
        # Extract and parse the response
        response_text = response.content[0].text if response.content else ""
        
        # Try to extract JSON
        try:
            # Find the JSON part in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                analysis = json.loads(json_str)
                return analysis
            else:
                return {"error": "Could not extract JSON from response"}
        except json.JSONDecodeError:
            return {"error": "Failed to parse response as JSON"}
            
    except Exception as e:
        return {"error": f"Claude API error: {str(e)}"}