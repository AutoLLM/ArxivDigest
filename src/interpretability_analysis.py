"""
Specialized module for mechanistic interpretability and technical AI safety analysis.
"""
import json
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prompts for specialized analysis
MECHANISTIC_INTERPRETABILITY_PROMPT = """
You are a research assistant specializing in mechanistic interpretability of AI systems.

Analyze this paper from the perspective of mechanistic interpretability:

Title: {title}
Authors: {authors}
Abstract: {abstract}
Content: {content}

Please provide a detailed analysis covering:

1. Relevance to mechanistic interpretability: How does this paper contribute to understanding the internal workings of models?
2. Interpretability techniques: What specific methods or approaches does the paper use to explain model behavior?
3. Circuit analysis: Does the paper identify specific circuits or computational components within models?
4. Attribution methods: What techniques are used to attribute model outputs to internal components?
5. Novel insights: What new understanding does this paper bring to model internals?
6. Limitations: What are the limitations of the approach from an interpretability perspective?
7. Future directions: What follow-up work would be valuable?
8. Connections to other interpretability research: How does this relate to other work in the field?

Format your response as JSON with these fields.
"""

TECHNICAL_AI_SAFETY_PROMPT = """
You are a research assistant specializing in technical AI safety.

Analyze this paper from the perspective of technical AI safety:

Title: {title}
Authors: {authors}
Abstract: {abstract}
Content: {content}

Please provide a detailed analysis covering:

1. Relevance to AI safety: How does this paper contribute to building safer AI systems?
2. Safety approaches: What specific methods or approaches does the paper use to improve AI safety?
3. Robustness: How does the paper address model robustness to distribution shifts or adversarial attacks?
4. Alignment: Does the paper discuss techniques for aligning AI systems with human values?
5. Risk assessment: What potential risks or failure modes does the paper address?
6. Monitoring and oversight: What methods are proposed for monitoring or controlling AI systems?
7. Limitations: What are the limitations of the approach from a safety perspective?
8. Future directions: What follow-up work would be valuable for improving safety?

Format your response as JSON with these fields.
"""

PROMPT_TEMPLATES = {
    "mechanistic_interpretability": MECHANISTIC_INTERPRETABILITY_PROMPT,
    "technical_ai_safety": TECHNICAL_AI_SAFETY_PROMPT
}

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Attempt to extract JSON from text, handling various formats.
    
    Args:
        text: String potentially containing JSON
        
    Returns:
        Extracted JSON as a dictionary, or error dictionary
    """
    try:
        # Look for JSON-like structures
        start_idx = text.find('{')
        end_idx = text.rfind('}') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = text[start_idx:end_idx]
            return json.loads(json_str)
        else:
            return {"error": "Could not find JSON in text", "raw_text": text}
    except json.JSONDecodeError:
        return {"error": "Failed to parse as JSON", "raw_text": text}

def create_analysis_prompt(paper: Dict[str, Any], analysis_type: str) -> str:
    """
    Create a prompt for specialized analysis.
    
    Args:
        paper: Dictionary with paper details
        analysis_type: Type of analysis to perform
        
    Returns:
        Formatted prompt string
    """
    if analysis_type not in PROMPT_TEMPLATES:
        raise ValueError(f"Unknown analysis type: {analysis_type}")
        
    prompt_template = PROMPT_TEMPLATES[analysis_type]
    
    return prompt_template.format(
        title=paper.get("title", ""),
        authors=paper.get("authors", ""),
        abstract=paper.get("abstract", ""),
        content=paper.get("content", "")[:10000]  # Limit content length
    )

def analyze_interpretability_circuits(paper: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform additional circuit analysis based on paper content and initial response.
    
    Args:
        paper: Dictionary with paper details
        response: Initial analysis response
        
    Returns:
        Enhanced analysis with circuit information
    """
    # This is a placeholder for more sophisticated circuit analysis
    # In a real implementation, this would use specialized tools to analyze
    # neural network circuits mentioned in the paper
    
    # Extract potential circuit descriptions from paper content
    circuit_mentions = []
    
    content = paper.get("content", "").lower()
    circuit_keywords = ["circuit", "attention head", "neuron", "mlp", "weight", "activation"]
    
    for keyword in circuit_keywords:
        if keyword in content:
            # Very simple extraction - in reality would use more sophisticated NLP
            start_idx = content.find(keyword)
            if start_idx >= 0:
                excerpt = content[max(0, start_idx-50):min(len(content), start_idx+100)]
                circuit_mentions.append(excerpt)
    
    # Add circuit information to response
    enhanced_response = response.copy()
    enhanced_response["circuit_mentions"] = circuit_mentions[:5]  # Limit to 5 mentions
    enhanced_response["circuit_analysis_performed"] = len(circuit_mentions) > 0
    
    return enhanced_response

def get_paper_relation_to_ai_safety(paper: Dict[str, Any]) -> str:
    """
    Determine how a paper relates to AI safety research.
    
    Args:
        paper: Dictionary with paper details
        
    Returns:
        Description of relation to AI safety
    """
    # Simple keyword-based approach
    safety_keywords = {
        "alignment": "AI alignment",
        "safety": "AI safety",
        "robustness": "Model robustness",
        "adversarial": "Adversarial robustness",
        "bias": "Bias mitigation",
        "fairness": "Fairness",
        "transparency": "Transparency",
        "interpretability": "Interpretability",
        "explainability": "Explainability",
        "oversight": "AI oversight",
        "control": "AI control",
        "verification": "Formal verification",
        "monitoring": "AI monitoring"
    }
    
    relation = []
    content = (paper.get("abstract", "") + " " + paper.get("title", "")).lower()
    
    for keyword, category in safety_keywords.items():
        if keyword in content:
            relation.append(category)
    
    if relation:
        return ", ".join(set(relation))
    else:
        return "No direct relation to AI safety identified"

def analyze_multi_agent_safety(paper: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze multi-agent safety aspects of a paper.
    
    Args:
        paper: Dictionary with paper details
        
    Returns:
        Multi-agent safety analysis
    """
    # Check if paper mentions multi-agent systems
    content = (paper.get("abstract", "") + " " + paper.get("title", "")).lower()
    
    multi_agent_keywords = [
        "multi-agent", "multiagent", "agent cooperation", "agent competition",
        "game theory", "nash equilibrium", "cooperative ai", "collaborative ai"
    ]
    
    is_multi_agent = any(keyword in content for keyword in multi_agent_keywords)
    
    if not is_multi_agent:
        return {"is_multi_agent_focused": False}
    
    # Simple analysis of multi-agent safety aspects
    safety_aspects = []
    
    if "cooperation" in content or "collaborative" in content or "coordination" in content:
        safety_aspects.append("Agent cooperation")
    
    if "competition" in content or "adversarial" in content:
        safety_aspects.append("Agent competition")
    
    if "equilibrium" in content or "game theory" in content:
        safety_aspects.append("Game theoretic analysis")
    
    if "incentive" in content or "reward" in content:
        safety_aspects.append("Incentive design")
    
    if "communication" in content:
        safety_aspects.append("Agent communication")
    
    return {
        "is_multi_agent_focused": True,
        "multi_agent_safety_aspects": safety_aspects,
        "summary": f"This paper focuses on multi-agent systems, specifically addressing: {', '.join(safety_aspects)}" if safety_aspects else "This paper discusses multi-agent systems but doesn't specifically address safety aspects."
    }