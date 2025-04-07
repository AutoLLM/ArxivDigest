import gradio as gr
from download_new_papers import get_papers
import utils
from relevancy import generate_relevance_score, process_subject_fields

import os
import openai
import datetime
import yaml
from paths import DATA_DIR, DIGEST_DIR
from model_manager import model_manager, ModelProvider
from gemini_utils import setup_gemini_api, get_topic_clustering

# Load config file
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {"threshold": 2}  # Default threshold if config loading fails

config = load_config()

# Helper function to filter papers by threshold
def filter_papers_by_threshold(papers, threshold):
    """Filter papers by relevancy score threshold"""
    print(f"\n===== FILTERING PAPERS =====")
    print(f"Only showing papers with relevancy score >= {threshold}")
    print(f"(Change this value in config.yaml if needed)")
    
    # Debug the paper scores
    for i, paper in enumerate(papers):
        print(f"Paper {i+1} - Title: {paper.get('title', 'No title')}")
        print(f"   - Score: {paper.get('Relevancy score', 'No score')}")
        print(f"   - Fields: {list(paper.keys())}")
    
    # First extract data from gemini_analysis if it exists and Relevancy score doesn't
    for paper in papers:
        if "gemini_analysis" in paper and "Relevancy score" not in paper:
            print(f"Extracting analysis data for paper: {paper.get('title')}")
            gemini_data = paper["gemini_analysis"]
            
            # Map Gemini analysis fields to expected fields
            field_mapping = {
                "relevance_score": "Relevancy score",
                "relationship_score": "Relevancy score",
                "paper_relevance": "Relevancy score",
                "paper's_relationship_to_the_user's_interests": "Relevancy score",
                "key_innovations": "Key innovations",
                "critical_analysis": "Critical analysis",
                "methodology_summary": "Methodology",
                "technical_significance": "Critical analysis",
                "related_research": "Related work"
            }
            
            # Copy fields using mapping
            for gemini_field, expected_field in field_mapping.items():
                if gemini_field in gemini_data:
                    paper[expected_field] = gemini_data[gemini_field]
                    print(f"  - Mapped {gemini_field} to {expected_field}")
                
            # If we have no score yet, look for a number in other fields
            if "Relevancy score" not in paper:
                # Try to find a relevance score in any field
                for field, value in gemini_data.items():
                    if isinstance(value, (int, float)) and 1 <= value <= 10:
                        paper["Relevancy score"] = value
                        print(f"  - Found score {value} in field {field}")
                        break
                    elif isinstance(value, str) and "score" in field.lower():
                        try:
                            # Try to extract a number from the string
                            import re
                            numbers = re.findall(r'\d+', value)
                            if numbers:
                                score = int(numbers[0])
                                if 1 <= score <= 10:  # Validate score range
                                    paper["Relevancy score"] = score
                                    print(f"  - Extracted score {score} from {field}: {value}")
                                    break
                        except:
                            pass
            
            # If still no score, default to threshold to include paper
            if "Relevancy score" not in paper:
                paper["Relevancy score"] = threshold
                print(f"  - Assigned default score {threshold}")
                
            # Add some reasonable defaults for missing fields
            if "Reasons for match" not in paper and "topic_classification" in gemini_data:
                paper["Reasons for match"] = gemini_data.get("topic_classification", "Not provided")
                
            # Set missing fields with default values
            for field in ["Key innovations", "Critical analysis", "Goal", "Data", "Methodology", 
                         "Implementation details", "Experiments & Results", "Discussion & Next steps",
                         "Related work", "Practical applications", "Key takeaways"]:
                if field not in paper:
                    paper[field] = "Not available in analysis"
    
    # Ensure scores are properly parsed to integers
    for paper in papers:
        if "Relevancy score" in paper and not isinstance(paper["Relevancy score"], int):
            try:
                if isinstance(paper["Relevancy score"], str) and "/" in paper["Relevancy score"]:
                    paper["Relevancy score"] = int(paper["Relevancy score"].split("/")[0])
                else:
                    paper["Relevancy score"] = int(paper["Relevancy score"])
            except (ValueError, TypeError):
                print(f"WARNING: Could not convert score '{paper.get('Relevancy score')}' to integer for paper: {paper.get('title')}")
                paper["Relevancy score"] = threshold  # Use threshold as default
    
    # Make sure all papers have required fields
    required_fields = [
        "Relevancy score", "Reasons for match", "Key innovations", "Critical analysis",
        "Goal", "Data", "Methodology", "Implementation details", "Experiments & Results",
        "Git", "Discussion & Next steps", "Related work", "Practical applications", 
        "Key takeaways"
    ]
    
    for paper in papers:
        # Make sure it has a relevancy score
        if "Relevancy score" not in paper:
            paper["Relevancy score"] = threshold
            print(f"Assigned default threshold score to paper: {paper.get('title')}")
            
        # Add missing fields with default values - always ensure all fields exist
        for field in required_fields:
            if field not in paper or paper[field] is None:
                paper[field] = f"Not available in the paper content"
                print(f"Added missing field {field} to paper: {paper.get('title')}")
            elif isinstance(paper[field], str) and (not paper[field].strip() or 
                  paper[field] == "Not provided" or paper[field] == "Not available in analysis"):
                paper[field] = f"Not available in the paper content"
                print(f"Replaced placeholder for field {field} in paper: {paper.get('title')}")
    
    # Now filter papers
    filtered_papers = [p for p in papers if p.get("Relevancy score", 0) >= threshold]
    print(f"After filtering: {len(filtered_papers)} papers remain out of {len(papers)}")
    
    # If fewer than 10 papers passed the filter, add the highest-scoring papers below threshold
    # This ensures we always show a reasonable number of papers
    if len(filtered_papers) < 10 and len(papers) > len(filtered_papers):
        print(f"WARNING: Only {len(filtered_papers)} papers passed the threshold filter. Adding more papers.")
        # Sort remaining papers by score and add the highest scoring ones
        remaining_papers = [p for p in papers if p not in filtered_papers]
        remaining_papers.sort(key=lambda x: x.get("Relevancy score", 0), reverse=True)
        # Add enough papers to get to 10 or all remaining papers, whichever is less
        additional_count = min(10 - len(filtered_papers), len(remaining_papers))
        filtered_papers.extend(remaining_papers[:additional_count])
        print(f"Added {additional_count} additional papers below threshold. Total papers: {len(filtered_papers)}")
    
    # Fallback if no papers passed the filter
    if len(filtered_papers) == 0 and len(papers) > 0:
        print("WARNING: No papers passed the threshold filter. Using all papers.")
        filtered_papers = papers
        
    return filtered_papers
from design_automation import (
    is_design_automation_paper, 
    categorize_design_paper, 
    analyze_design_techniques,
    extract_design_metrics,
    get_related_design_papers,
    create_design_analysis_prompt
)

topics = {
    "Physics": "",
    "Mathematics": "math",
    "Computer Science": "cs",
    "Quantitative Biology": "q-bio",
    "Quantitative Finance": "q-fin",
    "Statistics": "stat",
    "Electrical Engineering and Systems Science": "eess",
    "Economics": "econ"
}

physics_topics = {
    "Astrophysics": "astro-ph",
    "Condensed Matter": "cond-mat",
    "General Relativity and Quantum Cosmology": "gr-qc",
    "High Energy Physics - Experiment": "hep-ex",
    "High Energy Physics - Lattice": "hep-lat",
    "High Energy Physics - Phenomenology": "hep-ph",
    "High Energy Physics - Theory": "hep-th",
    "Mathematical Physics": "math-ph",
    "Nonlinear Sciences": "nlin",
    "Nuclear Experiment": "nucl-ex",
    "Nuclear Theory": "nucl-th",
    "Physics": "physics",
    "Quantum Physics": "quant-ph"
}

categories_map = {
    "Astrophysics": ["Astrophysics of Galaxies", "Cosmology and Nongalactic Astrophysics", "Earth and Planetary Astrophysics", "High Energy Astrophysical Phenomena", "Instrumentation and Methods for Astrophysics", "Solar and Stellar Astrophysics"],
    "Condensed Matter": ["Disordered Systems and Neural Networks", "Materials Science", "Mesoscale and Nanoscale Physics", "Other Condensed Matter", "Quantum Gases", "Soft Condensed Matter", "Statistical Mechanics", "Strongly Correlated Electrons", "Superconductivity"],
    "General Relativity and Quantum Cosmology": ["None"],
    "High Energy Physics - Experiment": ["None"],
    "High Energy Physics - Lattice": ["None"],
    "High Energy Physics - Phenomenology": ["None"],
    "High Energy Physics - Theory": ["None"],
    "Mathematical Physics": ["None"],
    "Nonlinear Sciences": ["Adaptation and Self-Organizing Systems", "Cellular Automata and Lattice Gases", "Chaotic Dynamics", "Exactly Solvable and Integrable Systems", "Pattern Formation and Solitons"],
    "Nuclear Experiment": ["None"],
    "Nuclear Theory": ["None"],
    "Physics": ["Accelerator Physics", "Applied Physics", "Atmospheric and Oceanic Physics", "Atomic and Molecular Clusters", "Atomic Physics", "Biological Physics", "Chemical Physics", "Classical Physics", "Computational Physics", "Data Analysis, Statistics and Probability", "Fluid Dynamics", "General Physics", "Geophysics", "History and Philosophy of Physics", "Instrumentation and Detectors", "Medical Physics", "Optics", "Physics and Society", "Physics Education", "Plasma Physics", "Popular Physics", "Space Physics"],
    "Quantum Physics": ["None"],
    "Mathematics": ["Algebraic Geometry", "Algebraic Topology", "Analysis of PDEs", "Category Theory", "Classical Analysis and ODEs", "Combinatorics", "Commutative Algebra", "Complex Variables", "Differential Geometry", "Dynamical Systems", "Functional Analysis", "General Mathematics", "General Topology", "Geometric Topology", "Group Theory", "History and Overview", "Information Theory", "K-Theory and Homology", "Logic", "Mathematical Physics", "Metric Geometry", "Number Theory", "Numerical Analysis", "Operator Algebras", "Optimization and Control", "Probability", "Quantum Algebra", "Representation Theory", "Rings and Algebras", "Spectral Theory", "Statistics Theory", "Symplectic Geometry"],
    "Computer Science": ["Artificial Intelligence", "Computation and Language", "Computational Complexity", "Computational Engineering, Finance, and Science", "Computational Geometry", "Computer Science and Game Theory", "Computer Vision and Pattern Recognition", "Computers and Society", "Cryptography and Security", "Data Structures and Algorithms", "Databases", "Digital Libraries", "Discrete Mathematics", "Distributed, Parallel, and Cluster Computing", "Emerging Technologies", "Formal Languages and Automata Theory", "General Literature", "Graphics", "Hardware Architecture", "Human-Computer Interaction", "Information Retrieval", "Information Theory", "Logic in Computer Science", "Machine Learning", "Mathematical Software", "Multiagent Systems", "Multimedia", "Networking and Internet Architecture", "Neural and Evolutionary Computing", "Numerical Analysis", "Operating Systems", "Other Computer Science", "Performance", "Programming Languages", "Robotics", "Social and Information Networks", "Software Engineering", "Sound", "Symbolic Computation", "Systems and Control"],
    "Quantitative Biology": ["Biomolecules", "Cell Behavior", "Genomics", "Molecular Networks", "Neurons and Cognition", "Other Quantitative Biology", "Populations and Evolution", "Quantitative Methods", "Subcellular Processes", "Tissues and Organs"],
    "Quantitative Finance": ["Computational Finance", "Economics", "General Finance", "Mathematical Finance", "Portfolio Management", "Pricing of Securities", "Risk Management", "Statistical Finance", "Trading and Market Microstructure"],
    "Statistics": ["Applications", "Computation", "Machine Learning", "Methodology", "Other Statistics", "Statistics Theory"],
    "Electrical Engineering and Systems Science": ["Audio and Speech Processing", "Image and Video Processing", "Signal Processing", "Systems and Control"],
    "Economics": ["Econometrics", "General Economics", "Theoretical Economics"]
}


def generate_html_report(papers, title="ArXiv Digest Results", topic=None, category=None, query=None):
    """Generate an HTML report for the papers and save to file.
    
    Args:
        papers: List of paper dictionaries
        title: Title for the HTML report
        topic: Optional topic name for filename
        category: Optional category name for filename
        query: Optional dictionary with interest field for research interests
        
    Returns:
        Path to the HTML file
    """
    # Debug: Log what fields are available in each paper
    print(f"Generating HTML report for {len(papers)} papers")
    for i, paper in enumerate(papers):
        print(f"Paper {i+1} fields: {list(paper.keys())}")
        if "Key innovations" in paper:
            print(f"Paper {i+1} has Key innovations: {paper['Key innovations'][:50]}...")
        if "Critical analysis" in paper:
            print(f"Paper {i+1} has Critical analysis: {paper['Critical analysis'][:50]}...")
    
    # Create a date for the filename (without time)
    date = datetime.datetime.now().strftime("%Y%m%d")
    
    # Create filename with topic if provided
    if topic:
        # Clean up topic name for filename (remove spaces, etc.)
        topic_clean = topic.lower().replace(" ", "_").replace("/", "_")
        html_file = os.path.join(DIGEST_DIR, f"arxiv_digest_{topic_clean}_{date}.html")
    else:
        html_file = os.path.join(DIGEST_DIR, f"arxiv_digest_{date}.html")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; max-width: 1200px; margin: 0 auto; }}
            .paper {{ margin-bottom: 40px; border-bottom: 2px solid #ddd; padding-bottom: 30px; }}
            .title {{ font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
            .authors {{ font-style: italic; margin: 8px 0; color: #34495e; }}
            .categories {{ color: #3498db; margin-bottom: 15px; font-size: 14px; }}
            .abstract {{ margin: 15px 0; line-height: 1.6; background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
            .score {{ font-weight: bold; color: #e74c3c; margin: 12px 0; font-size: 18px; }}
            .reason {{ margin: 15px 0; background-color: #f5f9f9; padding: 15px; border-left: 4px solid #2ecc71; border-radius: 0 5px 5px 0; }}
            .techniques {{ margin: 12px 0; color: #16a085; }}
            a {{ color: #2980b9; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .stats {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .interests {{ background-color: #e6f7ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #1890ff; }}
            .footer {{ margin-top: 40px; font-size: 12px; color: #7f8c8d; text-align: center; padding: 20px; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 30px; }}
            .section {{ margin: 15px 0; padding: 15px; background-color: #f8f9fa; border-radius: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            .section-title {{ font-weight: bold; color: #2c3e50; margin-bottom: 5px; font-size: 16px; }}
            .design-info {{ background-color: #e8f6f3; padding: 15px; margin: 15px 0; border-radius: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            .links {{ margin-top: 20px; background-color: #f8f9fa; padding: 10px; border-radius: 5px; display: inline-block; }}
            .key-section {{ margin: 15px 0; padding: 15px; background-color: #fdf5e6; border-radius: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            .implementation {{ margin: 15px 0; padding: 15px; background-color: #f0f8ff; border-radius: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            .experiments {{ margin: 15px 0; padding: 15px; background-color: #f5f5f5; border-radius: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            .discussion {{ margin: 15px 0; padding: 15px; background-color: #f0fff0; border-radius: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            .paper-navigation {{ 
                position: fixed; 
                top: 20px; 
                right: 20px; 
                background-color: white; 
                padding: 15px; 
                border: 1px solid #eee; 
                border-radius: 5px; 
                max-width: 250px;
                max-height: 80vh; /* Limit height to 80% of viewport height */
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 100;
                transition: transform 0.3s ease;
                transform: translateX(85%);
                overflow-y: auto; /* Enable vertical scrolling */
                overflow-x: hidden; /* Hide horizontal scrollbar */
            }}
            .paper-navigation:hover {{ 
                transform: translateX(0);
            }}
            .paper-navigation::before {{
                content: "Papers ◄";
                position: absolute;
                left: 10px;
                top: 15px;
                font-weight: bold;
                color: #2980b9;
                background-color: white; /* Ensure text is visible */
                padding: 2px 5px;
                z-index: 2; /* Keep above scrolling content */
            }}
            .paper-navigation ul {{ 
                list-style-type: none; 
                padding: 0 5px 0 0; /* Add padding for scrollbar */
                margin: 30px 0 0 0; /* Increased margin-top to make room for the "Papers ◄" label */
            }}
            .paper-navigation li {{ margin: 8px 0; }}
            .paper-navigation a {{ text-decoration: none; }}
            
            @media print {{
                .paper-navigation {{ display: none; }}
                .paper {{ page-break-after: always; }}
            }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        <div class="stats">
            <p>Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>Found {len(papers)} papers</p>
            <p>Topics: {topic or "All"}</p>
            <p>Threshold: {query.get("threshold", config.get("threshold", "Not specified"))}</p>
        </div>
        
        <div class="interests">
            <h3>Research Interests:</h3>
            <pre>{query.get('interest', 'Not specified')}</pre>
        </div>
        
        <!-- Create table of contents -->
        <div class="paper-navigation">
            <h3>Index</h3>
            <ul>
                {' '.join([f'<li><a href="#paper-{i}">{p.get("title", "Paper " + str(i+1))[:40]}...</a></li>' for i, p in enumerate(papers)])}
            </ul>
        </div>
    """
    
    # Check if we have any papers
    if not papers:
        html += """
        <div class="paper">
            <div class="title">No papers found matching your criteria</div>
            <div class="abstract">
                <p>No papers met the relevancy threshold criteria. You can:</p>
                <ul>
                    <li>Lower the threshold using the slider in Advanced Settings (currently set to {threshold})</li>
                    <li>Try different research interests</li>
                    <li>Check different categories or topics</li>
                </ul>
            </div>
        </div>
        """.format(threshold=config.get("threshold", 2))
    
    # Add papers
    for i, paper in enumerate(papers):
        paper_id = f"paper-{i}"
        html += f"""
        <div id="{paper_id}" class="paper">
            <div class="title"><a href="{paper.get("main_page", "#")}" target="_blank">{paper.get("title", "No title")}</a></div>
            <div class="authors">{paper.get("authors", "Unknown authors")}</div>
            <div class="categories">Subject: {paper.get("subjects", "N/A")}</div>
            """
        
        # Add relevancy score and reasons if available
        if "Relevancy score" in paper:
            html += f'<div class="score">Relevancy Score: {paper.get("Relevancy score", "N/A")}</div>'
        
        if "Reasons for match" in paper:
            html += f'<div class="reason"><b>Reason for Relevance:</b> {paper.get("Reasons for match", "")}</div>'
            
        # Add design information if available
        if "design_category" in paper or "design_techniques" in paper:
            html += '<div class="design-info">'
            if "design_category" in paper:
                html += f'<div><b>Design Category:</b> {paper.get("design_category", "")}</div>'
            if "design_techniques" in paper:
                html += f'<div><b>Design Techniques:</b> {", ".join(paper.get("design_techniques", []))}</div>'
            html += '</div>'
            
        # Add abstract
        if "abstract" in paper:
            html += f'<div class="abstract"><b>Abstract:</b> {paper.get("abstract", "")}</div>'
        
        # Helper function to format field content properly
        def format_field_content(content):
            if isinstance(content, list):
                # Format list items with bullet points
                return '<ul>' + ''.join([f'<li>{item}</li>' for item in content]) + '</ul>'
            else:
                return content
        
        # Add key innovations and critical analysis with special styling
        if "Key innovations" in paper:
            formatted_innovations = format_field_content(paper.get("Key innovations", ""))
            html += f'<div class="key-section"><div class="section-title">Key Innovations:</div> {formatted_innovations}</div>'
            print(f"Added Key innovations for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Key innovations field")
        
        if "Critical analysis" in paper:
            formatted_analysis = format_field_content(paper.get("Critical analysis", ""))
            html += f'<div class="key-section"><div class="section-title">Critical Analysis:</div> {formatted_analysis}</div>'
            print(f"Added Critical analysis for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Critical analysis field")
            
        # Add goal
        if "Goal" in paper:
            formatted_goal = format_field_content(paper.get("Goal", ""))
            html += f'<div class="key-section"><div class="section-title">Goal:</div> {formatted_goal}</div>'
            print(f"Added Goal for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Goal field")
            
        # Add Data
        if "Data" in paper:
            formatted_data = format_field_content(paper.get("Data", ""))
            html += f'<div class="implementation"><div class="section-title">Data:</div> {formatted_data}</div>'
            print(f"Added Data for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Data field")
            
        # Add Methodology
        if "Methodology" in paper:
            formatted_methodology = format_field_content(paper.get("Methodology", ""))
            html += f'<div class="implementation"><div class="section-title">Methodology:</div> {formatted_methodology}</div>'
            print(f"Added Methodology for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Methodology field")
            
        # Add implementation details
        if "Implementation details" in paper:
            formatted_details = format_field_content(paper.get("Implementation details", ""))
            html += f'<div class="implementation"><div class="section-title">Implementation Details:</div> {formatted_details}</div>'
            print(f"Added Implementation details for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Implementation details field")
            
        # Add experiments and results
        if "Experiments & Results" in paper:
            formatted_results = format_field_content(paper.get("Experiments & Results", ""))
            html += f'<div class="experiments"><div class="section-title">Experiments & Results:</div> {formatted_results}</div>'
            print(f"Added Experiments & Results for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Experiments & Results field")
            
        # Add discussion and next steps
        if "Discussion & Next steps" in paper:
            formatted_discussion = format_field_content(paper.get("Discussion & Next steps", ""))
            html += f'<div class="discussion"><div class="section-title">Discussion & Next Steps:</div> {formatted_discussion}</div>'
            print(f"Added Discussion & Next steps for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Discussion & Next steps field")
            
        # Add Related work
        if "Related work" in paper:
            formatted_related = format_field_content(paper.get("Related work", ""))
            html += f'<div class="discussion"><div class="section-title">Related Work:</div> {formatted_related}</div>'
            print(f"Added Related work for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Related work field")
            
        # Add Practical applications
        if "Practical applications" in paper:
            formatted_applications = format_field_content(paper.get("Practical applications", ""))
            html += f'<div class="discussion"><div class="section-title">Practical Applications:</div> {formatted_applications}</div>'
            print(f"Added Practical applications for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Practical applications field")
            
        # Add Key takeaways
        if "Key takeaways" in paper:
            formatted_takeaways = format_field_content(paper.get("Key takeaways", ""))
            html += f'<div class="key-section"><div class="section-title">Key Takeaways:</div> {formatted_takeaways}</div>'
            print(f"Added Key takeaways for paper {i+1}")
        else:
            print(f"Paper {i+1} is missing Key takeaways field")
        
        # Add remaining sections that weren't already handled specifically above
        for key, value in paper.items():
            # Skip fields we've already handled or don't want to display
            if key in ["title", "authors", "subjects", "main_page", "Relevancy score", "Reasons for match", 
                      "design_category", "design_techniques", "summarized_text", "abstract", "content",
                      "Key innovations", "Critical analysis", "Goal", "Data", "Methodology", 
                      "Implementation details", "Experiments & Results", "Discussion & Next steps",
                      "Related work", "Practical applications", "Key takeaways"]:
                continue
            
            if isinstance(value, str) and value.strip():
                # Choose appropriate styling based on the section
                section_class = "section"
                
                if "goal" in key.lower() or "aim" in key.lower():
                    section_class = "key-section"
                elif "data" in key.lower() or "methodology" in key.lower():
                    section_class = "implementation"
                elif "related" in key.lower() or "practical" in key.lower() or "takeaway" in key.lower():
                    section_class = "discussion"
                
                formatted_value = format_field_content(value)
                html += f'<div class="{section_class}"><div class="section-title">{key}:</div> {formatted_value}</div>'
                print(f"Added additional field {key} for paper {i+1}")
            
        # Add links
        html += f"""
            <div class="links">
                <a href="{paper.get("pdf", paper.get("main_page", "#") + ".pdf")}" target="_blank">PDF</a> | 
                <a href="{paper.get("main_page", "#")}" target="_blank">arXiv</a> |
                <a href="#" onclick="window.scrollTo(0,0); return false;">Back to Top</a>
            </div>
        </div>
        """
    
    html += """
        <div class="footer">
            <p>Generated by ArXiv Digest Extra v2</p>
        </div>
    </body>
    </html>
    """
    
    # Save the HTML file
    with open(html_file, "w") as f:
        f.write(html)
    
    print(f"Saved HTML report to {html_file}")
    return html_file

def sample(email, topic, physics_topic, categories, interest, use_openai, use_gemini, use_anthropic, 
           openai_model, gemini_model, anthropic_model, special_analysis, threshold_from_ui, custom_batch_size, custom_batch_number, 
           custom_prompt_batch_size, mechanistic_interpretability, technical_ai_safety, 
           design_automation, design_reference_paper, design_techniques, design_categories):
    print(f"\n===== STARTING TWO-STAGE PAPER ANALYSIS =====")
    print(f"Topic: {topic}")
    print(f"Research interests: {interest[:100]}...")
    print(f"Using threshold: {threshold_from_ui}")
    print(f"Stage 1 (Filtering): OpenAI {openai_model}")
    print(f"Stage 2 (Analysis): {'Gemini ' + gemini_model if use_gemini else 'OpenAI ' + openai_model}")
    print(f"UI Batch size: {custom_batch_size} papers")
    print(f"Prompt batch size: {custom_prompt_batch_size} papers per prompt")
    print(f"===============================================")
    if not topic:
        raise gr.Error("You must choose a topic.")
    if topic == "Physics":
        if isinstance(physics_topic, list):
            raise gr.Error("You must choose a physics topic.")
        topic = physics_topic
        abbr = physics_topics[topic]
    else:
        abbr = topics[topic]
    
    # Check if at least one model is selected
    if not (use_openai or use_gemini or use_anthropic):
        raise gr.Error("You must select at least one model provider (OpenAI, Gemini, or Claude)")
    
    # Get papers based on categories
    if categories:
        all_papers = get_papers(abbr)
        all_papers = [
            t for t in all_papers
            if bool(set(process_subject_fields(t['subjects'])) & set(categories))]
        print(f"Found {len(all_papers)} papers matching categories: {categories}")
    else:
        all_papers = get_papers(abbr)
        print(f"Found {len(all_papers)} papers for topic: {topic}")
    
    # Always process all papers
    papers = all_papers
    total_papers = len(all_papers)
    print(f"Processing all {total_papers} papers")
    
    # Fixed parameters:
    # - Stage 1: 8 papers per batch for relevancy scoring (title & abstract only)
    # - Stage 2: Detailed analysis of papers that meet threshold
    # - Minimum 10 papers (will include top-scoring papers below threshold if needed)
    
    if interest:
        # Build list of providers to use
        providers = []
        model_names = {}
        
        if use_openai:
            if not model_manager.is_provider_available(ModelProvider.OPENAI):
                if not openai.api_key:
                    raise gr.Error("Set your OpenAI API key in the OpenAI tab first")
                else:
                    model_manager.register_openai(openai.api_key)
            providers.append(ModelProvider.OPENAI)
            model_names[ModelProvider.OPENAI] = openai_model
            
        if use_gemini:
            if not model_manager.is_provider_available(ModelProvider.GEMINI):
                raise gr.Error("Set your Gemini API key in the Gemini tab first")
            providers.append(ModelProvider.GEMINI)
            model_names[ModelProvider.GEMINI] = gemini_model
            
        if use_anthropic:
            if not model_manager.is_provider_available(ModelProvider.ANTHROPIC):
                raise gr.Error("Set your Anthropic API key in the Anthropic tab first")
            providers.append(ModelProvider.ANTHROPIC)
            model_names[ModelProvider.ANTHROPIC] = anthropic_model
        
        # Check if we need to find design automation papers
        if design_automation:
            # Filter for design automation papers
            design_papers = [p for p in papers if is_design_automation_paper(p)]
            
            # Filter by techniques if specified
            if design_techniques:
                filtered_papers = []
                for paper in design_papers:
                    paper_techniques = analyze_design_techniques(paper)
                    if any(technique in design_techniques for technique in paper_techniques):
                        filtered_papers.append(paper)
                design_papers = filtered_papers if filtered_papers else design_papers
                
            # Filter by categories if specified
            if design_categories:
                filtered_papers = []
                for paper in design_papers:
                    paper_category = categorize_design_paper(paper)
                    if any(category in paper_category for category in design_categories):
                        filtered_papers.append(paper)
                design_papers = filtered_papers if filtered_papers else design_papers
                
            # Find related papers if reference paper is specified
            if design_reference_paper:
                related_papers = get_related_design_papers(design_reference_paper, papers)
                if related_papers:
                    design_papers = related_papers
            
            # Use these papers if we found any, otherwise fallback to regular papers
            if design_papers:
                papers = design_papers
        
        # Process papers directly instead of using model_manager
        print("\n===== ANALYZING PAPERS FOR EMAIL =====")
        print(f"Processing {len(papers)} papers...")
        relevancy = []
        hallucination = False
        
        # Use OpenAI if selected
        if use_openai and model_manager.is_provider_available(ModelProvider.OPENAI):
            try:
                # Import directly to avoid circular imports
                from relevancy import generate_relevance_score
                openai_results, hallu = generate_relevance_score(
                    papers,
                    query={"interest": interest},
                    model_name=openai_model,
                    threshold_score=int(threshold_from_ui),  # Apply threshold from UI slider
                    num_paper_in_prompt=int(custom_prompt_batch_size),  # Use the user-specified prompt batch size
                    stage2_model=gemini_model if use_gemini else "gpt-4-turbo"  # Use Gemini for stage 2 if selected
                )
                hallucination = hallucination or hallu
                relevancy.extend(openai_results)
                print(f"OpenAI analysis added {len(openai_results)} papers")
            except Exception as e:
                print(f"Error during OpenAI analysis: {e}")
        
        # Use Gemini if selected and no papers yet
        if use_gemini and model_manager.is_provider_available(ModelProvider.GEMINI) and len(relevancy) == 0:
            try:
                # Import directly to avoid circular imports
                from gemini_utils import analyze_papers_with_gemini
                gemini_papers = analyze_papers_with_gemini(
                    papers,
                    query={"interest": interest},
                    model_name=gemini_model
                )
                # Process papers to ensure they have the right fields
                for paper in gemini_papers:
                    if 'gemini_analysis' in paper:
                        # Copy all fields from gemini_analysis to the paper object
                        for key, value in paper['gemini_analysis'].items():
                            paper[key] = value
                
                relevancy.extend(gemini_papers)
                print(f"Gemini analysis added {len(gemini_papers)} papers")
            except Exception as e:
                print(f"Error during Gemini analysis: {e}")
                
        # Use Anthropic if selected and no papers yet
        if use_anthropic and model_manager.is_provider_available(ModelProvider.ANTHROPIC) and len(relevancy) == 0:
            try:
                # Import directly to avoid circular imports
                from anthropic_utils import analyze_papers_with_claude
                claude_papers = analyze_papers_with_claude(
                    papers,
                    query={"interest": interest},
                    model_name=anthropic_model
                )
                # Process papers to ensure they have the right fields
                for paper in claude_papers:
                    if 'claude_analysis' in paper:
                        # Copy all fields from claude_analysis to the paper object
                        for key, value in paper['claude_analysis'].items():
                            paper[key] = value
                
                relevancy.extend(claude_papers)
                print(f"Claude analysis added {len(claude_papers)} papers")
            except Exception as e:
                print(f"Error during Claude analysis: {e}")
        
        print(f"Total papers after analysis: {len(relevancy)}")
        
        # Papers are already filtered by threshold during LLM response processing
        # This is now just a safety check to ensure we didn't miss any
        threshold_value = int(threshold_from_ui) if threshold_from_ui is not None else config.get("threshold", 2)
        print(f"Using relevancy threshold: {threshold_value}")
        print(f"Papers before final threshold check: {len(relevancy)}")
        relevancy = filter_papers_by_threshold(relevancy, threshold_value)
        print(f"Papers after final threshold check: {len(relevancy)}")
        
        # Add design automation information if requested
        if design_automation and relevancy:
            for paper in relevancy:
                paper["design_category"] = categorize_design_paper(paper)
                paper["design_techniques"] = analyze_design_techniques(paper)
                paper["design_metrics"] = extract_design_metrics(paper)
                
                # Perform detailed design automation analysis on highest scored papers
                if paper.get("Relevancy score", 0) >= 7 and (use_openai or use_gemini or use_anthropic):
                    # Select provider for design analysis
                    provider = None
                    model = None
                    
                    if use_openai and model_manager.is_provider_available(ModelProvider.OPENAI):
                        provider = ModelProvider.OPENAI
                        model = openai_model
                    elif use_gemini and model_manager.is_provider_available(ModelProvider.GEMINI):
                        provider = ModelProvider.GEMINI
                        model = gemini_model
                    elif use_anthropic and model_manager.is_provider_available(ModelProvider.ANTHROPIC):
                        provider = ModelProvider.ANTHROPIC
                        model = anthropic_model
                        
                    if provider:
                        design_analysis = model_manager.analyze_design_automation(
                            paper,
                            provider=provider,
                            model_name=model
                        )
                        if design_analysis and "error" not in design_analysis:
                            paper["design_analysis"] = design_analysis
        
        # Add specialized analysis if requested
        if special_analysis and len(relevancy) > 0:
            # Get topic clustering from Gemini if available
            if use_gemini and model_manager.is_provider_available(ModelProvider.GEMINI):
                try:
                    clusters = get_topic_clustering(relevancy, model_name=gemini_model)
                    cluster_info = "\n\n=== TOPIC CLUSTERS ===\n"
                    for i, cluster in enumerate(clusters.get("clusters", [])):
                        cluster_info += f"\nCluster {i+1}: {cluster.get('name')}\n"
                        cluster_info += f"Papers: {', '.join([str(p) for p in cluster.get('papers', [])])}\n"
                        cluster_info += f"Description: {cluster.get('description')}\n"
                    
                    # Add cluster info to the output
                    cluster_summary = "\n\n" + cluster_info + "\n\n"
                except Exception as e:
                    cluster_summary = f"\n\nError generating clusters: {str(e)}\n\n"
            else:
                cluster_summary = ""
                
            # Add specialized mechanistic interpretability analysis if requested
            if mechanistic_interpretability and len(relevancy) > 0:
                # Use the first available provider in order of preference
                preferred_providers = [
                    (ModelProvider.ANTHROPIC, anthropic_model if use_anthropic else None),
                    (ModelProvider.OPENAI, openai_model if use_openai else None),
                    (ModelProvider.GEMINI, gemini_model if use_gemini else None)
                ]
                
                provider = None
                model = None
                for p, m in preferred_providers:
                    if model_manager.is_provider_available(p) and m:
                        provider = p
                        model = m
                        break
                        
                if provider:
                    try:
                        interp_analysis = model_manager.get_mechanistic_interpretability_analysis(
                            relevancy[0],  # Analyze the most relevant paper
                            provider=provider,
                            model_name=model
                        )
                        
                        interp_summary = "\n\n=== MECHANISTIC INTERPRETABILITY ANALYSIS ===\n"
                        for key, value in interp_analysis.items():
                            if key != "error" and key != "raw_content":
                                interp_summary += f"\n{key}: {value}\n"
                        
                        # Add interpretability analysis to the output
                        interpretability_info = "\n\n" + interp_summary + "\n\n"
                    except Exception as e:
                        interpretability_info = f"\n\nError generating interpretability analysis: {str(e)}\n\n"
                else:
                    interpretability_info = "\n\nNo available provider for interpretability analysis.\n\n"
            else:
                interpretability_info = ""
                
            # Generate HTML report
            html_file = generate_html_report(
                relevancy, 
                title=f"ArXiv Digest: {topic} papers",
                topic=topic,
                query={"interest": interest, "threshold": threshold_value}
            )
            
            # Create summary texts for display
            summary_texts = []
            for paper in relevancy:
                if "summarized_text" in paper:
                    summary_texts.append(paper["summarized_text"])
                else:
                    # Create a summary if summarized_text doesn't exist
                    summary = f"Title: {paper.get('title', 'No title')}\n"
                    summary += f"Authors: {paper.get('authors', 'Unknown')}\n"
                    summary += f"Score: {paper.get('Relevancy score', 'N/A')}\n"
                    summary += f"Abstract: {paper.get('abstract', 'No abstract')[:200]}...\n"
                    summary_texts.append(summary)
                    
            result_text = cluster_summary + "\n\n".join(summary_texts) + interpretability_info
            return result_text + f"\n\nHTML report saved to: {html_file}"
        else:
            # Generate HTML report
            html_file = generate_html_report(
                relevancy, 
                title=f"ArXiv Digest: {topic} papers",
                topic=topic,
                query={"interest": interest, "threshold": threshold_value}
            )
            
            # Create summary texts for display
            summary_texts = []
            for paper in relevancy:
                if "summarized_text" in paper:
                    summary_texts.append(paper["summarized_text"])
                else:
                    # Create a summary if summarized_text doesn't exist
                    summary = f"Title: {paper.get('title', 'No title')}\n"
                    summary += f"Authors: {paper.get('authors', 'Unknown')}\n" 
                    summary += f"Score: {paper.get('Relevancy score', 'N/A')}\n"
                    summary += f"Abstract: {paper.get('abstract', 'No abstract')[:200]}...\n"
                    summary_texts.append(summary)
                    
            result_text = "\n\n".join(summary_texts)
            return result_text + f"\n\nHTML report saved to: {html_file}"
    else:
        # Generate HTML report for basic results
        html_file = generate_html_report(
            papers, 
            title=f"ArXiv Digest: {topic} papers",
            topic=topic,
            query={"interest": interest, "threshold": threshold_from_ui if "threshold_from_ui" in locals() else config.get("threshold", 2)}
        )
        result_text = "\n\n".join(f"Title: {paper['title']}\nAuthors: {paper['authors']}" for paper in papers)
        return result_text + f"\n\nHTML report saved to: {html_file}"


def change_subsubject(subject, physics_subject):
    # For any subject (not just Physics), show appropriate subtopics
    if subject == "Physics" and physics_subject and not isinstance(physics_subject, list):
        # For Physics, show subcategories based on selected physics category
        return {"choices": categories_map[physics_subject], "value": [], "visible": True}
    elif subject in categories_map:
        # For other main topics, show their subtopics directly
        return {"choices": categories_map[subject], "value": [], "visible": True}
    else:
        # If no subtopics available
        return {"choices": [], "value": [], "visible": False}


def change_physics(subject):
    # Always return just the visibility attribute to avoid errors with value updates
    if subject != "Physics":
        return {"visible": False}
    else:
        return {"visible": True}


def register_openai_token(token):
    openai.api_key = token
    model_manager.register_openai(token)
    
def register_gemini_token(token):
    setup_gemini_api(token)
    model_manager.register_gemini(token)
    
def register_anthropic_token(token):
    model_manager.register_anthropic(token)

# Custom CSS
custom_css = """
#main-title h1 {
    text-align: center;
    font-size: 2.5rem;
    font-weight: bold;
    color: #2c3e50;
    margin-bottom: 0.5rem;
}

.banner-image {
    display: flex;
    justify-content: center;
    margin: 0 auto;
}
"""

with gr.Blocks(css=custom_css) as demo:
    with gr.Column():
        # Title first, then banner image
        with gr.Row():
            gr.Markdown("""
            # ArXiv Digest
            """, elem_id="main-title")
            
        # Smaller banner image, centered
        with gr.Row(elem_classes="banner-image"):
            gr.Image(value="./readme_images/main_banner.png", show_label=False, width=250)
            
        with gr.Row():
            gr.Markdown("""
            **Personalized arXiv Paper Recommendations with LLMs**
            
            This app helps you discover relevant academic papers from arXiv based on your research interests. 
            It uses a two-stage processing system: first filtering papers for relevance, then analyzing them in depth.
            
            [GitHub Repository](https://github.com/linhkid/ArxivDigest-extra) • [Report an Issue](https://github.com/linhkid/ArxivDigest-extra/issues)
            """)
            
        with gr.Tabs():
            with gr.TabItem("OpenAI"):
                openai_token = gr.Textbox(label="OpenAI API Key", type="password")
                openai_token.change(fn=register_openai_token, inputs=[openai_token])
            
            with gr.TabItem("Gemini"):
                gemini_token = gr.Textbox(label="Gemini API Key", type="password")
                gemini_token.change(fn=register_gemini_token, inputs=[gemini_token])
            
            with gr.TabItem("Anthropic"):
                anthropic_token = gr.Textbox(label="Anthropic API Key", type="password")
                anthropic_token.change(fn=register_anthropic_token, inputs=[anthropic_token])
        
        subject = gr.Radio(
            list(topics.keys()), label="Topic"
        )
        # Only show physics dropdown when Physics is selected
        physics_subject = gr.Dropdown(list(physics_topics.keys()), value=list(physics_topics.keys())[0], 
            multiselect=False, label="Physics category", visible=False)
        subsubject = gr.Dropdown(
            [], value=[], multiselect=True, 
            label="Subtopic (optional)", info="Optional. Leaving it empty will use all subtopics.", visible=True)

        # Use interest from config.yaml as default value
        interest = gr.Textbox(
            label="A natural language description of what you are interested in. We will generate relevancy scores (1-10) and explanations for the papers in the selected topics according to this statement.", 
            info="Press shift-enter or click the button below to update.", 
            lines=7,
            value=config.get("interest", "")
        )
        
        with gr.Row():
            use_openai = gr.Checkbox(label="Use OpenAI", value=True)
            use_gemini = gr.Checkbox(label="Use Gemini", value=False)
            use_anthropic = gr.Checkbox(label="Use Claude", value=False)
        
        with gr.Accordion("Advanced Settings", open=False):
            openai_model = gr.Dropdown(["gpt-3.5-turbo-16k", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"], value="gpt-4", label="OpenAI Model")
            gemini_model = gr.Dropdown(["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"], value="gemini-2.0-flash", label="Gemini Model")
            anthropic_model = gr.Dropdown(["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3.5-sonnet-20240620"], value="claude-3-sonnet-20240229", label="Claude Model")
            
            # Always include specialized analysis by default
            special_analysis = gr.Checkbox(label="Include specialized analysis for research topics", value=True)
            
            # Add threshold slider for relevancy filtering
            threshold = gr.Slider(
                minimum=0,
                maximum=10,
                value=config.get("threshold", 2),
                step=1,
                label="Relevancy Score Threshold",
                info="Papers with scores below this value will be filtered out (default from config.yaml: " + str(config.get("threshold", 2)) + ")"
            )
            
            # Hidden fields with fixed defaults (not shown in UI)
            batch_size = gr.Number(value=0, visible=False)  # 0 = process all
            batch_number = gr.Number(value=1, visible=False)
            prompt_batch_size = gr.Number(value=8, visible=False)  # Fixed at 8 papers per prompt
            
            # Multi-stage processing info
            gr.Markdown("""
            ### Two-Stage Paper Processing
            1. **Stage 1**: OpenAI performs quick relevancy filtering based on title & abstract only
            2. **Stage 2**: Gemini (if selected) performs detailed analysis on papers that passed threshold
            """)
            
            # Add two-stage processing explanation
            gr.Markdown("""
            **Efficiency Benefits**:
            - Filtering happens before downloading full content
            - Only relevant papers get detailed analysis
            - Optimizes token usage and response time
            """, visible=True)
            
            # Hidden fields for mechanistic interpretability and technical AI safety (not shown in UI but needed for function calls)
            mechanistic_interpretability = gr.Checkbox(label="Include mechanistic interpretability analysis", value=False, visible=False)
            technical_ai_safety = gr.Checkbox(label="Include technical AI safety analysis", value=False, visible=False)
            
            # Hidden fields for design automation (not shown in UI but needed for function calls)
            design_automation = gr.Checkbox(label="Find graphic design automation papers", value=False, visible=False)
            design_reference_paper = gr.Textbox(
                label="Reference paper ID",
                value="",
                visible=False
            )
            design_techniques = gr.CheckboxGroup(
                choices=[],
                value=[],
                visible=False
            )
            design_categories = gr.CheckboxGroup(
                choices=[],
                value=[],
                visible=False
            )
            
            # Hidden fields for email (not shown in UI but needed for function calls)
            email = gr.Textbox(label="Email address", type="email", placeholder="", visible=False)
            sendgrid_token = gr.Textbox(label="SendGrid API Key", type="password", visible=False)
            
        with gr.Row():
            sample_btn = gr.Button("Generate Digest", variant="primary", scale=2)
        
        with gr.Row():
            sample_output = gr.Textbox(
                label="Results", 
                info="Papers are first filtered by relevance score, then analyzed in depth. HTML reports are saved to the 'digest' folder.",
                show_label=True
            )
        
    # Define all input fields
    all_inputs = [
        email, subject, physics_subject, subsubject, interest, 
        use_openai, use_gemini, use_anthropic,
        openai_model, gemini_model, anthropic_model,
        special_analysis, threshold, batch_size, batch_number, prompt_batch_size,
        mechanistic_interpretability, technical_ai_safety,
        design_automation, design_reference_paper, design_techniques, design_categories
    ]
    
    # Connect change handlers for dynamic UI - use cleaner event handling
    def on_topic_change(topic):
        visible = (topic == "Physics")
        return {
            physics_subject: gr.update(visible=visible),
            subsubject: gr.update(choices=categories_map.get(topic, []), visible=topic in categories_map)
        }
        
    subject.change(fn=on_topic_change, inputs=[subject], outputs=[physics_subject, subsubject])
    
    # Use simpler event handler for physics subtopic changing
    def on_physics_change(topic, physics_topic):
        if topic == "Physics" and physics_topic and physics_topic in categories_map:
            return gr.update(choices=categories_map[physics_topic], visible=True)
        return gr.update(visible=False)
        
    physics_subject.change(fn=on_physics_change, inputs=[subject, physics_subject], outputs=[subsubject])
    
    # Sample button
    sample_btn.click(
        fn=sample, 
        inputs=all_inputs,
        outputs=sample_output
    )
    
    # Register API keys
    openai_token.change(fn=register_openai_token, inputs=[openai_token])
    gemini_token.change(fn=register_gemini_token, inputs=[gemini_token])
    anthropic_token.change(fn=register_anthropic_token, inputs=[anthropic_token])
    
    # Only allow updates when the button is clicked or interest is submitted directly
    interest.submit(fn=sample, inputs=all_inputs, outputs=sample_output)

demo.launch(show_api=False)
