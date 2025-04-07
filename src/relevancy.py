"""
run:
python -m relevancy run_all_day_paper \
  --model_name="gpt-3.5-turbo-16k" \
"""
import time
import json
import os
import random
import re
import string
from datetime import datetime

import numpy as np
import tqdm
import utils

from paths import DATA_DIR


def encode_prompt(query, prompt_papers, include_content=True):
    """
    Encode multiple prompt instructions into a single string.
    
    Args:
        query: Dictionary with interest field
        prompt_papers: List of paper dictionaries
        include_content: Whether to include the full content field (False for stage 1 filtering)
    """
    # Use different prompt templates for each stage
    if include_content:
        # Stage 2: Full analysis with content
        prompt = open("src/relevancy_prompt.txt").read() + "\n"
    else:
        # Stage 1: Quick relevancy scoring with just title and abstract
        prompt = open("src/relevancy_filter_prompt.txt").read() + "\n"
    
    prompt += query['interest']

    for idx, task_dict in enumerate(prompt_papers):
        (title, authors, abstract) = task_dict["title"], task_dict["authors"], task_dict["abstract"]
        if not title:
            raise
        prompt += f"###\n"
        prompt += f"{idx + 1}. Title: {title}\n"
        prompt += f"{idx + 1}. Authors: {authors}\n"
        prompt += f"{idx + 1}. Abstract: {abstract}\n"
        
        # Only include content in stage 2
        if include_content and "content" in task_dict:
            content = task_dict["content"]
            prompt += f"{idx + 1}. Content: {content}\n"
            
    prompt += f"\n Generate response:\n1."
    
    # Just log the number of papers and stage information
    num_papers = len(prompt_papers)
    stage = "Stage 2 (full analysis)" if include_content else "Stage 1 (relevancy filtering)"
    print(f"Sending prompt for {stage} with {num_papers} papers")
    
    return prompt


def is_json(myjson):
    try:
        json.loads(myjson)
    except Exception as e:
        return False
    return True

def extract_json_from_string(text):
    """
    Improved JSON extraction that can handle multiple JSON objects in different formats
    """
    # Clean up the text - remove markdown code blocks and backticks
    text = text.replace("```json", "").replace("```", "").strip()
    
    # Try to find all JSON objects in the text
    json_objects = []
    
    # First, try to split by numbered lines (1., 2., etc.)
    numbered_pattern = re.compile(r'^\d+\.\s*(\{.*?\})', re.DOTALL | re.MULTILINE)
    numbered_matches = numbered_pattern.findall(text)
    
    if numbered_matches:
        # Found numbered JSON objects
        for json_str in numbered_matches:
            try:
                parsed = json.loads(json_str)
                json_objects.append(parsed)
            except json.JSONDecodeError:
                pass
    
    # If we didn't find numbered objects, look for direct JSON objects
    if not json_objects:
        # Find all potential JSON objects
        stack = []
        start_indices = []
        
        for i, char in enumerate(text):
            if char == '{' and (not stack):
                start_indices.append(i)
                stack.append(char)
            elif char == '{':
                stack.append(char)
            elif char == '}' and stack:
                stack.pop()
                if not stack:
                    # Found a complete JSON object
                    json_str = text[start_indices.pop():i+1]
                    try:
                        parsed = json.loads(json_str)
                        json_objects.append(parsed)
                    except json.JSONDecodeError:
                        pass
    
    print(f"Found {len(json_objects)} JSON objects in the response")
    return json_objects

def post_process_chat_gpt_response(paper_data, response, threshold_score=0):
    """
    Completely rewritten parsing function that handles the OpenAI response better
    """
    selected_data = []
    if response is None:
        print("Response is None")
        return [], False
        
    # Handle both old and new API response formats
    if isinstance(response, dict) and 'message' in response:
        # Old API format
        content = response['message']['content']
    elif hasattr(response, 'choices') and len(response.choices) > 0:
        # New API format (OpenAI Client)
        content = response.choices[0].message.content
    else:
        # Fallback to dictionary access
        try:
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        except Exception:
            content = ''
            
    if not content:
        print("Content is empty")
        return [], False
    
    # Print the raw content for debugging
    print(f"\nRaw content:\n{content}\n")
    
    # Try to extract multiple JSON objects from the content
    json_objects = extract_json_from_string(content)
    
    if json_objects:
        # Found JSON objects using our improved extractor
        score_items = []
        for obj in json_objects:
            if "Relevancy score" in obj or "relevancy score" in obj:
                # Normalize key names (handle case sensitivity)
                normalized_obj = {}
                for key, value in obj.items():
                    if key.lower() == "relevancy score":
                        normalized_obj["Relevancy score"] = value
                    else:
                        normalized_obj[key] = value
                score_items.append(normalized_obj)
    else:
        # Fallback to older parsing method
        score_items = []
        json_items = content.replace("\n\n", "\n").split("\n")
        pattern = r"^\d+\. |\\"
        
        for line in json_items:
            if is_json(line) and "relevancy score" in line.lower():
                try:
                    parsed_item = json.loads(re.sub(pattern, "", line))
                    score_items.append(parsed_item)
                except:
                    pass
    
    print(f"Found {len(score_items)} score items from response")
    
    # If we have no score items but have paper data, create default ones
    if len(score_items) == 0 and len(paper_data) > 0:
        print("Creating default score items for each paper")
        score_items = []
        for i in range(len(paper_data)):
            # Create a default item with a mid-range score
            score_items.append({
                "Relevancy score": 5,
                "Reasons for match": "Default score assigned due to parsing issues.",
                "Key innovations": "Not available in analysis",
                "Critical analysis": "Not available in analysis",
                "Goal": "Not available in analysis",
                "Data": "Not available in analysis",
                "Methodology": "Not available in analysis",
                "Implementation details": "Not available in analysis",
                "Experiments & Results": "Not available in analysis",
                "Git": "Not available in analysis",
                "Discussion & Next steps": "Not available in analysis",
                "Related work": "Not available in analysis",
                "Practical applications": "Not available in analysis",
                "Key takeaways": "Not available in analysis"
            })
    
    # Truncate score_items if needed
    if len(score_items) > len(paper_data):
        print(f"WARNING: More score items ({len(score_items)}) than papers ({len(paper_data)})")
        score_items = score_items[:len(paper_data)]
        hallucination = True
    else:
        hallucination = False

    # Define expected analysis fields we want to ensure are copied to the paper objects
    analysis_fields = [
        "Relevancy score", "Reasons for match", "Key innovations", "Critical analysis",
        "Goal", "Data", "Methodology", "Implementation details", "Experiments & Results",
        "Git", "Discussion & Next steps", "Related work", "Practical applications", 
        "Key takeaways"
    ]

    print(f"DEBUG: Processing {len(score_items)} score items for {len(paper_data)} papers")
    
    # If we don't have any score items but have papers, something went wrong with parsing
    if len(score_items) == 0 and len(paper_data) > 0:
        print("WARNING: No score items were found, but papers exist. Check JSON parsing.")
        # Create fallback score items with default score to prevent empty results
        for i in range(len(paper_data)):
            fallback_item = {
                "Relevancy score": threshold_score,  # Set to threshold score to ensure it passes filter
                "Reasons for match": "Automatically assigned threshold score due to parsing issues."
            }
            score_items.append(fallback_item)
            
    # Ensure we have at least one paper if there are score items
    for idx, inst in enumerate(score_items):
        if idx >= len(paper_data):
            print(f"DEBUG: Index {idx} out of range for paper_data (length {len(paper_data)})")
            continue
        
        # Get the relevancy score
        relevancy_score = inst.get('Relevancy score', 0)
        if isinstance(relevancy_score, str):
            try:
                # Try to convert string score to integer
                if '/' in relevancy_score:
                    relevancy_score = int(relevancy_score.split('/')[0])
                else:
                    relevancy_score = int(relevancy_score)
            except (ValueError, TypeError):
                relevancy_score = threshold_score  # Default to threshold if conversion fails
        
        print(f"DEBUG: Processing paper {idx+1} with score {relevancy_score}")
        
        # Only process papers that meet the threshold
        if relevancy_score < threshold_score:
            print(f"DEBUG: Skipping paper {idx+1} with score {relevancy_score} < threshold {threshold_score}")
            continue
            
        # Create detailed output string for logging and console display
        output_str = "Subject: " + paper_data[idx]["subjects"] + "\n"
        output_str += "Title: " + paper_data[idx]["title"] + "\n"
        output_str += "Authors: " + paper_data[idx]["authors"] + "\n"
        output_str += "Link: " + paper_data[idx]["main_page"] + "\n"
        
        # Copy all fields from the analysis to the paper object
        for key, value in inst.items():
            paper_data[idx][key] = value
            output_str += str(key) + ": " + str(value) + "\n"
            
        # Ensure all expected analysis fields are present in the paper object
        # This ensures fields used in the HTML template like "Key innovations" are set
        for field in analysis_fields:
            if field in inst:
                # Double-check the field got copied (should be redundant with the loop above)
                paper_data[idx][field] = inst[field]
                print(f"Found and copied field: {field}")
            else:
                print(f"Missing analysis field: {field}")
                paper_data[idx][field] = "Not available in analysis"
        
        paper_data[idx]['summarized_text'] = output_str
        selected_data.append(paper_data[idx])
        print(f"DEBUG: Added paper {idx+1} to selected_data (now has {len(selected_data)} papers)")
        
    print(f"DEBUG: Selected papers count: {len(selected_data)}")
    print(f"DEBUG: Paper fields: {list(selected_data[0].keys()) if selected_data else 'No papers'}")
    
    return selected_data, hallucination


def find_word_in_string(w, s):
    return re.compile(r"\b({0})\b".format(w), flags=re.IGNORECASE).search(s)


def process_subject_fields(subjects):
    all_subjects = subjects.split(";")
    all_subjects = [s.split(" (")[0] for s in all_subjects]
    return all_subjects

def filter_papers_by_relevance(
    all_papers,
    query,
    model_name="gpt-3.5-turbo-16k",
    threshold_score=2,
    num_paper_in_prompt=8,  # Fixed at 8 papers per prompt as requested
    temperature=0.3,  # Lower temperature for more consistent relevancy scoring
    top_p=1.0,
    max_papers=10  # Try to find at least this many papers that meet the threshold
):
    """
    Stage 1: Filter papers by relevance using only title and abstract
    Returns only papers that meet or exceed the threshold score
    """
    filtered_papers = []
    print(f"\n===== STAGE 1: FILTERING PAPERS BY RELEVANCE (THRESHOLD >= {threshold_score}) =====")
    
    for id in tqdm.tqdm(range(0, len(all_papers), num_paper_in_prompt), desc="Stage 1: Relevancy filtering"):
        batch_papers = all_papers[id:id+num_paper_in_prompt]
        
        # Create prompt without content for quick relevancy filtering
        prompt = encode_prompt(query, batch_papers, include_content=False)
        
        decoding_args = utils.OpenAIDecodingArguments(
            temperature=temperature,
            n=1,
            max_tokens=512,  # Less tokens needed for just scoring
            top_p=top_p,
        )
        
        request_start = time.time()
        response = utils.openai_completion(
            prompts=prompt,
            model_name=model_name,
            batch_size=1,
            decoding_args=decoding_args,
            logit_bias={"100257": -100},  # prevent the <|endoftext|> from being generated
        )
        
        request_duration = time.time() - request_start
        print(f"Stage 1 batch took {request_duration:.2f}s")
        
        # Extract just the relevancy scores
        process_start = time.time()
        batch_data, _ = post_process_chat_gpt_response(
            batch_papers, 
            response, 
            threshold_score=0  # Don't filter yet, we want all scores
        )
        
        # Keep only papers that meet or exceed the threshold
        # Make sure we have the same number of scores as papers
        if len(batch_data) != len(batch_papers):
            print(f"WARNING: Mismatch between batch_data ({len(batch_data)}) and batch_papers ({len(batch_papers)})")
            # If we have different counts, we need to match papers to scores
            # This handles cases where not all papers got scores
            
            # Create a map of titles to papers for easier lookup
            title_to_paper = {p["title"]: p for p in batch_papers}
            
            # Match scores to papers
            for paper in batch_data:
                if "title" in paper and paper["title"] in title_to_paper:
                    # Found a match by title
                    relevancy_score = paper.get("Relevancy score", 0)
                    if isinstance(relevancy_score, str):
                        try:
                            if '/' in relevancy_score:
                                relevancy_score = int(relevancy_score.split('/')[0])
                            else:
                                relevancy_score = int(relevancy_score)
                        except (ValueError, TypeError):
                            relevancy_score = 0
                            
                    if relevancy_score >= threshold_score:
                        print(f"PASSED: Paper '{paper['title'][:50]}...' with score {relevancy_score}")
                        filtered_papers.append(paper)
                    else:
                        print(f"FILTERED OUT: Paper '{paper['title'][:50]}...' with score {relevancy_score}")
        else:
            # We have the expected number of scores
            for paper in batch_data:
                relevancy_score = paper.get("Relevancy score", 0)
                if isinstance(relevancy_score, str):
                    try:
                        if '/' in relevancy_score:
                            relevancy_score = int(relevancy_score.split('/')[0])
                        else:
                            relevancy_score = int(relevancy_score)
                    except (ValueError, TypeError):
                        relevancy_score = 0
                        
                if relevancy_score >= threshold_score:
                    print(f"PASSED: Paper '{paper['title'][:50]}...' with score {relevancy_score}")
                    filtered_papers.append(paper)
                else:
                    print(f"FILTERED OUT: Paper '{paper['title'][:50]}...' with score {relevancy_score}")
                
        print(f"Post-processing took {time.time() - process_start:.2f}s")
        print(f"Filtered papers so far: {len(filtered_papers)} out of {id + len(batch_papers)}")
    
    print(f"\nStage 1 complete: {len(filtered_papers)} papers met the threshold of {threshold_score} out of {len(all_papers)}")
    
    # If we didn't find enough papers, adjust threshold downward and include more
    if len(filtered_papers) < max_papers and threshold_score > 1:
        # Find the highest-scored papers that didn't meet the threshold
        remaining_scores = {}
        for paper in all_papers:
            if paper not in filtered_papers:
                score = paper.get("Relevancy score", 0)
                if isinstance(score, str):
                    try:
                        score = int(score)
                    except (ValueError, TypeError):
                        score = 0
                remaining_scores[paper] = score
        
        # Sort the remaining papers by score (descending)
        sorted_papers = sorted(remaining_scores.keys(), key=lambda p: remaining_scores[p], reverse=True)
        
        # Add the highest-scored papers until we reach max_papers or run out of papers
        papers_to_add = sorted_papers[:max_papers - len(filtered_papers)]
        for paper in papers_to_add:
            score = remaining_scores[paper]
            print(f"Adding paper '{paper['title'][:50]}...' with score {score} (below threshold) to meet minimum paper count")
            filtered_papers.append(paper)
        
        print(f"Added {len(papers_to_add)} papers below threshold to reach {len(filtered_papers)} total papers")
    
    return filtered_papers


def analyze_papers_in_depth(
    filtered_papers,
    query,
    model_name="gemini-1.5-flash",  # Use Gemini by default for detailed analysis
    num_paper_in_prompt=5,  # Smaller batches for detailed analysis
    temperature=0.5,
    top_p=1.0
):
    """
    Stage 2: Analyze papers in depth, including content analysis
    Only called for papers that passed the relevancy threshold
    """
    analyzed_papers = []
    print(f"\n===== STAGE 2: DETAILED ANALYSIS OF {len(filtered_papers)} PAPERS =====")
    
    # If we're using Gemini, use their API instead
    if "gemini" in model_name:
        print(f"Using Gemini for detailed analysis: {model_name}")
        from gemini_utils import analyze_papers_with_gemini
        return analyze_papers_with_gemini(
            filtered_papers,
            query=query,
            model_name=model_name
        )
    
    # Otherwise use OpenAI
    for id in tqdm.tqdm(range(0, len(filtered_papers), num_paper_in_prompt), desc="Stage 2: Detailed analysis"):
        batch_papers = filtered_papers[id:id+num_paper_in_prompt]
        
        # Create prompt with content for detailed analysis
        prompt = encode_prompt(query, batch_papers, include_content=True)
        
        decoding_args = utils.OpenAIDecodingArguments(
            temperature=temperature,
            n=1,
            max_tokens=1024*num_paper_in_prompt,
            top_p=top_p,
        )
        
        request_start = time.time()
        response = utils.openai_completion(
            prompts=prompt,
            model_name=model_name,
            batch_size=1,
            decoding_args=decoding_args,
            logit_bias={"100257": -100},  # prevent the <|endoftext|> from being generated
        )
        
        request_duration = time.time() - request_start
        print(f"Stage 2 batch took {request_duration:.2f}s")
        
        # Process the detailed analysis
        process_start = time.time()
        batch_data, _ = post_process_chat_gpt_response(batch_papers, response, threshold_score=0)
        analyzed_papers.extend(batch_data)
        
        print(f"Post-processing took {time.time() - process_start:.2f}s")
        print(f"Analyzed papers so far: {len(analyzed_papers)} out of {len(filtered_papers)}")
    
    print(f"\nStage 2 complete: {len(analyzed_papers)} papers fully analyzed")
    return analyzed_papers


def generate_relevance_score(
    all_papers,
    query,
    model_name="gpt-3.5-turbo-16k",
    threshold_score=2,
    num_paper_in_prompt=8,  # Fixed at 8 papers per prompt
    temperature=0.4,
    top_p=1.0,
    sorting=True,
    stage2_model="gemini-1.5-flash",  # Model to use for Stage 2
    min_papers=10  # Minimum number of papers to return
):
    """
    Two-stage paper processing:
    1. Filter papers by relevance using OpenAI (fast, based on title/abstract)
    2. Analyze relevant papers in depth using Gemini (detailed, includes content)
    """
    # Stage 1: Filter by relevance (OpenAI)
    filtered_papers = filter_papers_by_relevance(
        all_papers,
        query,
        model_name=model_name,
        threshold_score=threshold_score,
        num_paper_in_prompt=num_paper_in_prompt,
        temperature=temperature,
        top_p=top_p,
        max_papers=min_papers  # Ensure we get at least this many papers
    )
    
    # If no papers passed the threshold, return empty results
    if len(filtered_papers) == 0:
        print("No papers passed the relevance threshold. Returning empty results.")
        return [], False
    
    # Before Stage 2: Extract HTML content for papers that passed the filter
    print(f"\n===== EXTRACTING HTML CONTENT FOR {len(filtered_papers)} PAPERS =====")
    for i, paper in enumerate(filtered_papers):
        try:
            # Extract HTML content from the paper URL
            from download_new_papers import crawl_html_version
            
            # Get the paper ID from the main_page URL
            paper_id = None
            main_page = paper.get("main_page", "")
            if main_page:
                # Extract paper ID (e.g., 2401.12345)
                import re
                id_match = re.search(r'/abs/([0-9v.]+)', main_page)
                if id_match:
                    paper_id = id_match.group(1)
            
            if paper_id:
                # Construct HTML link
                html_link = f"https://arxiv.org/html/{paper_id}"
                print(f"Fetching HTML content for paper {i+1}/{len(filtered_papers)}: {paper['title'][:50]}...")
                print(f"HTML link: {html_link}")
                
                # Try to get content
                content = crawl_html_version(html_link)
                if content and len(content) > 100 and "Error accessing HTML" not in content:
                    paper["content"] = content
                    print(f"✅ Successfully extracted {len(content)} characters of content")
                else:
                    # If HTML version fails, use the abstract + more details
                    paper["content"] = f"{paper.get('abstract', '')} {paper.get('title', '')}"
                    print(f"⚠️ Failed to extract content, using abstract instead. Error: {content[:100]}...")
                time.sleep(3)
            else:
                print(f"⚠️ Couldn't parse paper ID from URL: {main_page}")
                paper["content"] = paper.get("abstract", "No content available")
                
        except Exception as e:
            print(f"❌ Error extracting HTML content: {str(e)}")
            # Fallback to using the abstract
            paper["content"] = paper.get("abstract", "No content available")
            
    print(f"Content extraction complete for {len(filtered_papers)} papers.")
    
    # Stage 2: In-depth analysis (Gemini or fallback to OpenAI)
    analyzed_papers = analyze_papers_in_depth(
        filtered_papers,
        query,
        model_name=stage2_model,
        num_paper_in_prompt=max(1, num_paper_in_prompt // 2),  # Smaller batches for detailed analysis
        temperature=temperature,
        top_p=top_p
    )
    
    # Sort by relevancy score if requested
    if sorting and analyzed_papers:
        analyzed_papers = sorted(analyzed_papers, key=lambda x: int(x.get("Relevancy score", 0)), reverse=True)
    
    return analyzed_papers, False  # No hallucination tracking in two-stage system

def run_all_day_paper(
    query={"interest":"Computer Science", "subjects":["Machine Learning", "Computation and Language", "Artificial Intelligence", "Information Retrieval"]},
    date=None,
    model_name="gpt-3.5-turbo-16k",
    threshold_score=7,
    num_paper_in_prompt=2,
    temperature=0.4,
    top_p=1.0
):
    if date is None:
        date = datetime.today().strftime('%a, %d %b %y')
        # string format such as Wed, 10 May 23
    print ("the date for the arxiv data is: ", date)

    file_path = os.path.join(DATA_DIR, f"{date}.jsonl")
    all_papers = [json.loads(l) for l in open(file_path, "r")]
    print (f"We found {len(all_papers)}.")

    all_papers_in_subjects = [
        t for t in all_papers
        if bool(set(process_subject_fields(t['subjects'])) & set(query['subjects']))
    ]
    print(f"After filtering subjects, we have {len(all_papers_in_subjects)} papers left.")
    ans_data = generate_relevance_score(all_papers_in_subjects, query, model_name, threshold_score, num_paper_in_prompt, temperature, top_p)
    from paths import DIGEST_DIR
    utils.write_ans_to_file(ans_data, date, output_dir=DIGEST_DIR)
    return ans_data


if __name__ == "__main__":
    query = {"interest":"""
    1. Large language model pretraining and finetunings
    2. Multimodal machine learning
    3. Do not care about specific application, for example, information extraction, summarization, etc.
    4. Not interested in paper focus on specific languages, e.g., Arabic, Chinese, etc.\n""",
    "subjects":["Computation and Language"]}
    ans_data = run_all_day_paper(query)
