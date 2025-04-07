"""
A script to fix and test the OpenAI response parsing.
"""
import json
import re
import os

def is_valid_json(text):
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False

def extract_json_from_string(text):
    """
    Attempt to extract JSON from a string by finding '{'...'}'
    """
    # Find the outermost JSON object
    stack = []
    start_idx = -1
    
    for i, char in enumerate(text):
        if char == '{' and start_idx == -1:
            start_idx = i
            stack.append(char)
        elif char == '{':
            stack.append(char)
        elif char == '}' and stack:
            stack.pop()
            if not stack and start_idx != -1:
                # Found complete JSON object
                json_str = text[start_idx:i+1]
                try:
                    parsed = json.loads(json_str)
                    return parsed
                except json.JSONDecodeError:
                    # If this one fails, continue looking
                    start_idx = -1
    
    return None

def fix_openai_response(response_text):
    """
    Fix the OpenAI response by handling different formats and parsing the JSON.
    Returns a list of dictionaries with paper analysis.
    """
    # First, try to parse the entire response as JSON
    cleaned_text = response_text.strip()
    
    # Try to extract JSON directly
    if '{' in cleaned_text and '}' in cleaned_text:
        json_obj = extract_json_from_string(cleaned_text)
        if json_obj and "Relevancy score" in json_obj:
            print(f"Successfully extracted JSON with score {json_obj['Relevancy score']}")
            return [json_obj]
            
    return []

# Example usage
if __name__ == "__main__":
    example_response = """
  "Relevancy score": 7, 
  "Reasons for match": "This paper aligns with your research interests as it explores the application of Large Language Models (LLMs) in the context of hardware design. It introduces a unified framework, Marco, that integrates configurable graph-based task solving with multi-modality and multi-AI agents for chip design. This is relevant to your interests in AI Alignment, AI safety, Large Language Models, and Multimodal Learning.",
  "Key innovations": [
    "Introduction of Marco, a unified framework that integrates configurable graph-based task solving with multi-modality and multi-AI agents for chip design.",
    "Demonstration of promising performance, productivity, and efficiency of LLM agents by leveraging the Marco framework on layout optimization, Verilog/design rule checker (DRC) coding, and timing analysis tasks."
  ],
  "Critical analysis": "The paper presents a novel approach to leveraging LLMs in the field of hardware design, which could have significant implications for improving efficiency and reducing costs. However, without access to the full paper, it's difficult to assess the strengths and potential limitations of the approach.",
  "Goal": "The paper addresses the challenge of optimizing performance, power, area, and cost (PPAC) during synthesis, verification, physical design, and reliability loops in hardware design. It aims to reduce turn-around-time (TAT) for these processes by leveraging the capabilities of LLMs.",
  "Data": "Unable to provide details about the datasets used due to lack of access to the full paper content.",
  "Methodology": "The paper proposes a unified framework, Marco, that integrates configurable graph-based task solving with multi-modality and multi-AI agents for chip design. However, detailed methodology is not available due to lack of access to the full paper content.",
  "Implementation details": "Unable to provide implementation details due to lack of access to the full paper content.",
  "Git": "Link to code repository is not provided in the abstract.",
  "Experiments & Results": "The abstract mentions that the Marco framework demonstrates promising performance on layout optimization, Verilog/design rule checker (DRC) coding, and timing analysis tasks. However, detailed results and comparisons are not available due to lack of access to the full paper content.",
  "Discussion & Next steps": "Unable to provide details on the authors' conclusions, identified limitations, and future research directions due to lack of access to the full paper content.",
  "Related work": "Unable to provide details on how this paper relates to similar recent papers in the field due to lack of access to the full paper content.",
  "Practical applications": "The framework proposed in this paper could have practical applications in the field of hardware design, potentially leading to faster product cycles, lower costs, improved design reliability and reduced risk of costly errors.",
  "Key takeaways": [
    "The paper proposes a unified framework, Marco, that integrates configurable graph-based task solving with multi-modality and multi-AI agents for chip design.",
    "The Marco framework leverages the capabilities of Large Language Models (LLMs) to improve efficiency and reduce costs in hardware design.",
    "The framework demonstrates promising performance on layout optimization, Verilog/design rule checker (DRC) coding, and timing analysis tasks."
  ]
}
    """
    
    # Test the fix
    results = fix_openai_response(example_response)
    print(f"Found {len(results)} paper analyses")
    for i, result in enumerate(results):
        print(f"Paper {i+1} score: {result.get('Relevancy score', 'Not found')}")