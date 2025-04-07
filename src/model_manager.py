"""
Model Manager module to handle different LLM providers.
This provides a unified interface for working with different LLM providers.
"""
import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum

import openai
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"

class ModelManager:
    """Manager for handling different LLM providers."""

    def __init__(self):
        self.providers = {}
        self.available_models = {}

    def register_openai(self, api_key: str) -> bool:
        """Register OpenAI as a provider."""
        if not api_key:
            logger.error("No OpenAI API key provided")
            return False

        try:
            openai.api_key = api_key
            # Test API connection
            models = openai.Model.list()
            self.providers[ModelProvider.OPENAI] = True
            self.available_models[ModelProvider.OPENAI] = [model.id for model in models.data]
            logger.info(f"Successfully connected to OpenAI API. Available models: {self.available_models[ModelProvider.OPENAI]}")
            return True
        except Exception as e:
            logger.error(f"Failed to setup OpenAI API: {e}")
            return False

    def register_gemini(self, api_key: str) -> bool:
        """Register Gemini as a provider."""
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
            self.providers[ModelProvider.GEMINI] = True
            self.available_models[ModelProvider.GEMINI] = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
            logger.info(f"Successfully connected to Gemini API. Available models: {self.available_models[ModelProvider.GEMINI]}")
            return True
        except Exception as e:
            logger.error(f"Failed to setup Gemini API: {e}")
            return False

    def register_anthropic(self, api_key: str) -> bool:
        """Register Anthropic/Claude as a provider."""
        if not ANTHROPIC_AVAILABLE:
            logger.error("Anthropic package not installed. Run 'pip install anthropic'")
            return False

        if not api_key:
            logger.error("No Anthropic API key provided")
            return False

        try:
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
            # Test API connection by listing models
            models = self.anthropic_client.models.list()
            self.providers[ModelProvider.ANTHROPIC] = True
            self.available_models[ModelProvider.ANTHROPIC] = [model.id for model in models.data]
            logger.info(f"Successfully connected to Anthropic API. Available models: {self.available_models[ModelProvider.ANTHROPIC]}")
            return True
        except Exception as e:
            logger.error(f"Failed to setup Anthropic API: {e}")
            return False

    def is_provider_available(self, provider: ModelProvider) -> bool:
        """Check if a provider is available."""
        return provider in self.providers and self.providers[provider]

    def get_available_providers(self) -> List[ModelProvider]:
        """Get a list of available providers."""
        return [provider for provider in self.providers if self.providers[provider]]

    def get_provider_models(self, provider: ModelProvider) -> List[str]:
        """Get available models for a provider."""
        if provider in self.available_models:
            return self.available_models[provider]
        return []

    def analyze_papers(
        self,
        papers: List[Dict[str, Any]],
        query: Dict[str, str],
        providers: List[ModelProvider] = None,
        model_names: Dict[ModelProvider, str] = None,
        threshold_score: int = 7,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Analyze papers using multiple model providers.
        
        Args:
            papers: List of paper dictionaries
            query: Dictionary with 'interest' key describing research interests
            providers: List of providers to use (defaults to all available)
            model_names: Dictionary mapping providers to model names
            threshold_score: Minimum score for a paper to be considered relevant
            
        Returns:
            Tuple of (list of papers with analysis, hallucination flag)
        """
        if not providers:
            providers = self.get_available_providers()
            
        if not model_names:
            model_names = {}
            
        # Default model names if not specified
        default_models = {
            ModelProvider.OPENAI: "gpt-3.5-turbo-16k",
            ModelProvider.GEMINI: "gemini-1.5-flash",
            ModelProvider.ANTHROPIC: "claude-3.5-sonnet-20240620"
        }
        
        # Use default models if not specified
        for provider in providers:
            if provider not in model_names:
                model_names[provider] = default_models.get(provider)
        
        # Check if any providers are available
        if not any(self.is_provider_available(provider) for provider in providers):
            logger.error("No available providers for paper analysis")
            return papers, False
            
        analyzed_papers = []
        hallucination = False
        
        # Import the modules here to avoid circular imports
        if ModelProvider.OPENAI in providers and self.is_provider_available(ModelProvider.OPENAI):
            from relevancy import generate_relevance_score
            try:
                analyzed_papers, hallu = generate_relevance_score(
                    papers,
                    query=query,
                    model_name=model_names[ModelProvider.OPENAI],
                    threshold_score=threshold_score,
                    num_paper_in_prompt=2
                )
                hallucination = hallucination or hallu
            except Exception as e:
                logger.error(f"Error analyzing papers with OpenAI: {e}")
        
        # Add Gemini analysis if available
        if ModelProvider.GEMINI in providers and self.is_provider_available(ModelProvider.GEMINI):
            # Import locally to avoid circular imports
            from gemini_utils import analyze_papers_with_gemini
            
            try:
                if not analyzed_papers:  # If OpenAI analysis failed or was not used
                    analyzed_papers = papers
                
                analyzed_papers = analyze_papers_with_gemini(
                    analyzed_papers,
                    query=query,
                    model_name=model_names[ModelProvider.GEMINI]
                )
            except Exception as e:
                logger.error(f"Error analyzing papers with Gemini: {e}")
        
        # Add Anthropic/Claude analysis if available
        if ModelProvider.ANTHROPIC in providers and self.is_provider_available(ModelProvider.ANTHROPIC):
            # Import locally to avoid circular imports
            from anthropic_utils import analyze_papers_with_claude
            
            try:
                if not analyzed_papers:  # If previous analyses failed or were not used
                    analyzed_papers = papers
                
                analyzed_papers = analyze_papers_with_claude(
                    analyzed_papers,
                    query=query,
                    model_name=model_names[ModelProvider.ANTHROPIC]
                )
            except Exception as e:
                logger.error(f"Error analyzing papers with Claude: {e}")
        
        return analyzed_papers, hallucination

    def get_mechanistic_interpretability_analysis(
        self, 
        paper: Dict[str, Any],
        provider: ModelProvider = None,
        model_name: str = None
    ) -> Dict[str, Any]:
        """
        Get specialized mechanistic interpretability analysis for a paper.
        
        Args:
            paper: Paper dictionary
            provider: Provider to use (defaults to first available)
            model_name: Model name to use
            
        Returns:
            Dictionary with mechanistic interpretability analysis
        """
        # Import interpretability analysis functions
        from interpretability_analysis import (
            create_analysis_prompt, 
            extract_json_from_text, 
            analyze_interpretability_circuits,
            get_paper_relation_to_ai_safety
        )
        
        if not provider:
            available_providers = self.get_available_providers()
            if not available_providers:
                logger.error("No available providers for mechanistic interpretability analysis")
                return {"error": "No available providers"}
            provider = available_providers[0]
            
        if not model_name:
            # Use more powerful models for specialized analysis
            default_models = {
                ModelProvider.OPENAI: "gpt-4o",
                ModelProvider.GEMINI: "gemini-2.0-flash",
                ModelProvider.ANTHROPIC: "claude-3.5-sonnet-20240620"
            }
            model_name = default_models.get(provider)
            
        if not self.is_provider_available(provider):
            logger.error(f"Provider {provider} is not available")
            return {"error": f"Provider {provider} is not available"}
            
        # Get specialized prompt
        prompt = create_analysis_prompt(paper, "mechanistic_interpretability")
        
        # Process based on provider
        if provider == ModelProvider.OPENAI:
            try:
                response = openai.ChatCompletion.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a specialist in mechanistic interpretability and AI safety."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2048
                )
                
                # Extract JSON from response
                content = response.choices[0].message.content
                analysis = extract_json_from_text(content)
                
                # Add additional circuit analysis if there's no error
                if "error" not in analysis:
                    analysis = analyze_interpretability_circuits(paper, analysis)
                    analysis["ai_safety_relation"] = get_paper_relation_to_ai_safety(paper)
                
                return analysis
                    
            except Exception as e:
                logger.error(f"Error getting mechanistic interpretability analysis with OpenAI: {e}")
                return {"error": f"OpenAI error: {str(e)}"}
                
        elif provider == ModelProvider.GEMINI and GEMINI_AVAILABLE:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                
                # Extract JSON from response
                content = response.text
                analysis = extract_json_from_text(content)
                
                # Add additional circuit analysis if there's no error
                if "error" not in analysis:
                    analysis = analyze_interpretability_circuits(paper, analysis)
                    analysis["ai_safety_relation"] = get_paper_relation_to_ai_safety(paper)
                
                return analysis
                    
            except Exception as e:
                logger.error(f"Error getting mechanistic interpretability analysis with Gemini: {e}")
                return {"error": f"Gemini error: {str(e)}"}
                
        elif provider == ModelProvider.ANTHROPIC and ANTHROPIC_AVAILABLE:
            try:
                response = self.anthropic_client.messages.create(
                    model=model_name,
                    max_tokens=2048,
                    temperature=0.3,
                    system="You are a specialist in mechanistic interpretability and AI safety.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # Extract JSON from response
                content = response.content[0].text
                analysis = extract_json_from_text(content)
                
                # Add additional circuit analysis if there's no error
                if "error" not in analysis:
                    analysis = analyze_interpretability_circuits(paper, analysis)
                    analysis["ai_safety_relation"] = get_paper_relation_to_ai_safety(paper)
                
                return analysis
                    
            except Exception as e:
                logger.error(f"Error getting mechanistic interpretability analysis with Claude: {e}")
                return {"error": f"Claude error: {str(e)}"}
                
        return {"error": "Unsupported provider or configuration"}
        
    def analyze_design_automation(
        self,
        paper: Dict[str, Any],
        provider: ModelProvider = None,
        model_name: str = None
    ) -> Dict[str, Any]:
        """
        Get specialized analysis for design automation papers.
        
        Args:
            paper: Paper dictionary
            provider: Provider to use (defaults to first available)
            model_name: Model name to use
            
        Returns:
            Dictionary with design automation analysis
        """
        # Import design automation functions
        from design_automation import (
            create_design_analysis_prompt,
            extract_design_capabilities
        )
        from interpretability_analysis import extract_json_from_text
        
        if not provider:
            available_providers = self.get_available_providers()
            if not available_providers:
                logger.error("No available providers for design automation analysis")
                return {"error": "No available providers"}
            provider = available_providers[0]
            
        if not model_name:
            # Use appropriate models for design analysis
            default_models = {
                ModelProvider.OPENAI: "gpt-4o",
                ModelProvider.GEMINI: "gemini-2.0-flash",
                ModelProvider.ANTHROPIC: "claude-3.5-sonnet-20240620"
            }
            model_name = default_models.get(provider)
            
        if not self.is_provider_available(provider):
            logger.error(f"Provider {provider} is not available")
            return {"error": f"Provider {provider} is not available"}
            
        # Get specialized prompt
        prompt = create_design_analysis_prompt(paper)
        
        # Process based on provider
        try:
            analysis = None
            
            if provider == ModelProvider.OPENAI:
                response = openai.ChatCompletion.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a specialist in AI for design automation."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2048
                )
                content = response.choices[0].message.content
                analysis = extract_json_from_text(content)
                
            elif provider == ModelProvider.GEMINI and GEMINI_AVAILABLE:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                content = response.text
                analysis = extract_json_from_text(content)
                
            elif provider == ModelProvider.ANTHROPIC and ANTHROPIC_AVAILABLE:
                response = self.anthropic_client.messages.create(
                    model=model_name,
                    max_tokens=2048,
                    temperature=0.3,
                    system="You are a specialist in AI for design automation.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                content = response.content[0].text
                analysis = extract_json_from_text(content)
            
            # Enhance analysis with design capabilities if successful
            if analysis and "error" not in analysis:
                capabilities = extract_design_capabilities(analysis)
                analysis["capabilities"] = capabilities
                
            return analysis or {"error": "Failed to generate analysis"}
            
        except Exception as e:
            logger.error(f"Error analyzing design automation paper: {e}")
            return {"error": f"Analysis error: {str(e)}"}

# Create a singleton instance
model_manager = ModelManager()