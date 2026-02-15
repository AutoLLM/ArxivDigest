from __future__ import annotations

import argparse
from datetime import date
import html as html_lib
import os
import re
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
import openai
import yaml

from relevancy import generate_relevance_score, process_subject_fields
from download_new_papers import get_papers

# -----------------------------
# Topic maps (original project)
# -----------------------------
topics = {
    "Physics": "",
    "Mathematics": "math",
    "Computer Science": "cs",
    "Quantitative Biology": "q-bio",
    "Quantitative Finance": "q-fin",
    "Statistics": "stat",
    "Electrical Engineering and Systems Science": "eess",
    "Economics": "econ",
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
    "Quantum Physics": "quant-ph",
}

# TODO: surely theres a better way
category_map = {
    "Astrophysics": [
        "Astrophysics of Galaxies",
        "Cosmology and Nongalactic Astrophysics",
        "Earth and Planetary Astrophysics",
        "High Energy Astrophysical Phenomena",
        "Instrumentation and Methods for Astrophysics",
        "Solar and Stellar Astrophysics",
    ],
    "Condensed Matter": [
        "Disordered Systems and Neural Networks",
        "Materials Science",
        "Mesoscale and Nanoscale Physics",
        "Other Condensed Matter",
        "Quantum Gases",
        "Soft Condensed Matter",
        "Statistical Mechanics",
        "Strongly Correlated Electrons",
        "Superconductivity",
    ],
    "General Relativity and Quantum Cosmology": ["None"],
    "High Energy Physics - Experiment": ["None"],
    "High Energy Physics - Lattice": ["None"],
    "High Energy Physics - Phenomenology": ["None"],
    "High Energy Physics - Theory": ["None"],
    "Mathematical Physics": ["None"],
    "Nonlinear Sciences": [
        "Adaptation and Self-Organizing Systems",
        "Cellular Automata and Lattice Gases",
        "Chaotic Dynamics",
        "Exactly Solvable and Integrable Systems",
        "Pattern Formation and Solitons",
    ],
    "Nuclear Experiment": ["None"],
    "Nuclear Theory": ["None"],
    "Physics": [
        "Accelerator Physics",
        "Applied Physics",
        "Atmospheric and Oceanic Physics",
        "Atomic and Molecular Clusters",
        "Atomic Physics",
        "Biological Physics",
        "Chemical Physics",
        "Classical Physics",
        "Computational Physics",
        "Data Analysis, Statistics and Probability",
        "Fluid Dynamics",
        "General Physics",
        "Geophysics",
        "History and Philosophy of Physics",
        "Instrumentation and Detectors",
        "Medical Physics",
        "Optics",
        "Physics and Society",
        "Physics Education",
        "Plasma Physics",
        "Popular Physics",
        "Space Physics",
    ],
    "Quantum Physics": ["None"],
    "Mathematics": [
        "Algebraic Geometry",
        "Algebraic Topology",
        "Analysis of PDEs",
        "Category Theory",
        "Classical Analysis and ODEs",
        "Combinatorics",
        "Commutative Algebra",
        "Complex Variables",
        "Differential Geometry",
        "Dynamical Systems",
        "Functional Analysis",
        "General Mathematics",
        "General Topology",
        "Geometric Topology",
        "Group Theory",
        "History and Overview",
        "Information Theory",
        "K-Theory and Homology",
        "Logic",
        "Mathematical Physics",
        "Metric Geometry",
        "Number Theory",
        "Numerical Analysis",
        "Operator Algebras",
        "Optimization and Control",
        "Probability",
        "Quantum Algebra",
        "Representation Theory",
        "Rings and Algebras",
        "Spectral Theory",
        "Statistics Theory",
        "Symplectic Geometry",
    ],
    "Computer Science": [
        "Artificial Intelligence",
        "Computation and Language",
        "Computational Complexity",
        "Computational Engineering, Finance, and Science",
        "Computational Geometry",
        "Computer Science and Game Theory",
        "Computer Vision and Pattern Recognition",
        "Computers and Society",
        "Cryptography and Security",
        "Data Structures and Algorithms",
        "Databases",
        "Digital Libraries",
        "Discrete Mathematics",
        "Distributed, Parallel, and Cluster Computing",
        "Emerging Technologies",
        "Formal Languages and Automata Theory",
        "General Literature",
        "Graphics",
        "Hardware Architecture",
        "Human-Computer Interaction",
        "Information Retrieval",
        "Information Theory",
        "Logic in Computer Science",
        "Machine Learning",
        "Mathematical Software",
        "Multiagent Systems",
        "Multimedia",
        "Networking and Internet Architecture",
        "Neural and Evolutionary Computing",
        "Numerical Analysis",
        "Operating Systems",
        "Other Computer Science",
        "Performance",
        "Programming Languages",
        "Robotics",
        "Social and Information Networks",
        "Software Engineering",
        "Sound",
        "Symbolic Computation",
        "Systems and Control",
    ],
    "Quantitative Biology": [
        "Biomolecules",
        "Cell Behavior",
        "Genomics",
        "Molecular Networks",
        "Neurons and Cognition",
        "Other Quantitative Biology",
        "Populations and Evolution",
        "Quantitative Methods",
        "Subcellular Processes",
        "Tissues and Organs",
    ],
    "Quantitative Finance": [
        "Computational Finance",
        "Economics",
        "General Finance",
        "Mathematical Finance",
        "Portfolio Management",
        "Pricing of Securities",
        "Risk Management",
        "Statistical Finance",
        "Trading and Market Microstructure",
    ],
    "Statistics": [
        "Applications",
        "Computation",
        "Machine Learning",
        "Methodology",
        "Other Statistics",
        "Statistics Theory",
    ],
    "Electrical Engineering and Systems Science": [
        "Audio and Speech Processing",
        "Image and Video Processing",
        "Signal Processing",
        "Systems and Control",
    ],
    "Economics": ["Econometrics", "General Economics", "Theoretical Economics"],
}


# -----------------------------
# Helpers
# -----------------------------
def _html_to_text(s: str) -> str:
    """Convert limited HTML into readable plain text fallback."""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p\s*>", "\n\n", s, flags=re.I)
    s = re.sub(r"<li\s*>", "• ", s, flags=re.I)
    s = re.sub(r"</li\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return html_lib.unescape(s).strip()


def _safe_join(xs: List[str], sep: str = ", ") -> str:
    return sep.join([x for x in xs if x])


def _pick_topic_abbr(topic: str) -> str:
    if topic == "Physics":
        raise RuntimeError("你选择了 Physics 顶级主题：必须指定一个 physics 子主题（如 Astrophysics / Quantum Physics）。")
    if topic in physics_topics:
        return physics_topics[topic]
    if topic in topics:
        return topics[topic]
    raise RuntimeError(f"无效 topic：{topic}")


def _filter_by_categories(papers: List[Dict[str, Any]], topic: str, categories: List[str]) -> List[Dict[str, Any]]:
    """Filter papers by user-selected categories (subject fields)."""
    for category in categories:
        if category not in category_map.get(topic, []):
            raise RuntimeError(f"{category} 不是 {topic} 的有效分类（subject field）。")
    return [
        t for t in papers
        if bool(set(process_subject_fields(t.get("subjects", ""))) & set(categories))
    ]


def _build_cards_html(
    papers: List[Dict[str, Any]],
    show_score: bool,
) -> str:
    """Render paper list as card-style HTML."""
    cards = []
    for idx, p in enumerate(papers, start=1):
        title = p.get("title", "").strip()
        url = p.get("main_page", "").strip()
        authors = p.get("authors", "").strip()
        subjects = p.get("subjects", "").strip()

        score = str(p.get("Relevancy score", "")).strip() if show_score else ""
        reason = str(p.get("Reasons for match", "")).strip() if show_score else ""

        title_html = html_lib.escape(title) if title else "(无标题)"
        url_html = html_lib.escape(url) if url else "#"
        authors_html = html_lib.escape(authors) if authors else "-"
        subjects_html = html_lib.escape(subjects) if subjects else "-"

        extra = ""
        if show_score:
            extra = f"""
              <div style="margin-top:10px;color:#444;font-size:13px;">
                <div><b>相关度分数</b>：{html_lib.escape(score) if score else "-"}</div>
                <div style="margin-top:6px;"><b>匹配理由</b>：{html_lib.escape(reason) if reason else "-"}</div>
              </div>
            """

        cards.append(
            f"""
            <div style="border:1px solid #eee;border-radius:12px;padding:14px 14px;margin:0 0 12px 0;background:#fff;">
              <div style="font-size:16px;line-height:1.4;margin-bottom:6px;">
                <b>{idx}. </b><a href="{url_html}" style="text-decoration:none;">{title_html}</a>
              </div>
              <div style="color:#555;font-size:13px;line-height:1.55;">
                <div><b>作者</b>：{authors_html}</div>
                <div><b>分类</b>：{subjects_html}</div>
              </div>
              {extra}
            </div>
            """
        )
    return "\n".join(cards)


def generate_digest(
    topic: str,
    categories: List[str],
    interest: str,
    threshold: float,
) -> Tuple[str, str, bool, bool]:
    """
    Generate digest content.

    Returns:
      body_fragment_html: HTML fragment
      plain_text: fallback text
      used_interest: whether interest scoring was used
      had_hallucination_warning: whether hallucination warning is present
    """
    abbr = _pick_topic_abbr(topic)

    papers = get_papers(abbr)

    if categories:
        papers = _filter_by_categories(papers, topic, categories)

    used_interest = bool(interest and interest.strip())
    hallucination_warning = False

    if used_interest:
        relevancy, hallucination = generate_relevance_score(
            papers,
            query={"interest": interest},
            threshold_score=threshold,
            num_paper_in_prompt=16,
        )
        hallucination_warning = bool(hallucination)
        # relevancy is already filtered by threshold
        papers_to_show = relevancy
    else:
        papers_to_show = papers

    if not papers_to_show:
        tips = [
            "今天没有论文命中你的筛选条件。",
            "建议：",
            "1）把 threshold 调低（例如 0.2 / 0.1），或者先留空 interest 看全量；",
            "2）扩大 categories（或先留空 categories）；",
            "3）确认 topic 是否正确（比如 Computer Science / Electrical Engineering and Systems Science 等）。",
        ]
        body_fragment = "<br>".join([html_lib.escape(x) for x in tips])
        plain_text = "\n".join(tips)
        return body_fragment, plain_text, used_interest, hallucination_warning

    # cards
    if used_interest:
        header = (
            "以下为根据你的兴趣进行相关度排序后的推荐："
            f"（阈值 threshold={threshold}）"
        )
    else:
        header = "以下为今日最新论文列表（未启用兴趣相关度排序）："

    header_html = f"<p style='margin:0 0 12px 0;color:#222;'><b>{html_lib.escape(header)}</b></p>"

    if hallucination_warning:
        warn = (
            "⚠️ 注意：模型可能对少量论文产生“幻觉匹配”。已尽力剔除，但分数/理由仍可能不完全准确。"
        )
        warn_html = f"<p style='margin:0 0 12px 0;color:#b45309;'><b>{html_lib.escape(warn)}</b></p>"
    else:
        warn_html = ""

    cards_html = _build_cards_html(papers_to_show, show_score=used_interest)

    body_fragment = header_html + warn_html + cards_html

    # text fallback
    lines = [header]
    for idx, p in enumerate(papers_to_show, start=1):
        title = p.get("title", "").strip()
        url = p.get("main_page", "").strip()
        authors = p.get("authors", "").strip()
        subjects = p.get("subjects", "").strip()
        lines.append(f"{idx}. {title}")
        if authors:
            lines.append(f"   作者：{authors}")
        if subjects:
            lines.append(f"   分类：{subjects}")
        if url:
            lines.append(f"   链接：{url}")
        if used_interest:
            score = str(p.get("Relevancy score", "")).strip()
            reason = str(p.get("Reasons for match", "")).strip()
            if score:
                lines.append(f"   相关度：{score}")
            if reason:
                lines.append(f"   理由：{reason}")
        lines.append("")
    plain_text = "\n".join(lines).strip()
    return body_fragment, plain_text, used_interest, hallucination_warning


def wrap_full_html(subject_cn: str, subtitle_cn: str, body_fragment: str, config_snapshot: str) -> str:
    """Wrap fragment into a complete Chinese HTML email."""
    safe_subject = html_lib.escape(subject_cn)
    safe_subtitle = html_lib.escape(subtitle_cn)
    safe_cfg = html_lib.escape(config_snapshot)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_subject}</title>
</head>
<body style="margin:0;background:#f6f7fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,'Noto Sans','PingFang SC','Microsoft YaHei',sans-serif;">
  <div style="max-width:860px;margin:0 auto;padding:22px;">
    <div style="background:#ffffff;border:1px solid #eef0f4;border-radius:16px;padding:18px 18px;">
      <div style="font-size:22px;font-weight:800;line-height:1.25;margin:0 0 6px 0;">{safe_subject}</div>
      <div style="color:#666;font-size:12px;line-height:1.4;margin:0 0 14px 0;">
        {safe_subtitle}
      </div>

      <div style="height:1px;background:#f0f2f6;margin:14px 0;"></div>

      <div style="font-size:14px;line-height:1.7;color:#111;">
        {body_fragment}
      </div>

      <div style="height:1px;background:#f0f2f6;margin:16px 0;"></div>

      <details style="color:#555;font-size:12px;line-height:1.6;">
        <summary style="cursor:pointer;user-select:none;">查看本次运行的配置（config.yaml 摘要）</summary>
        <pre style="white-space:pre-wrap;background:#fafafa;border:1px solid #f0f0f0;border-radius:12px;padding:12px;margin-top:10px;">{safe_cfg}</pre>
      </details>

      <div style="color:#999;font-size:11px;margin-top:14px;">
        由 GitHub Actions 自动生成与发送（SMTP）。如 HTML 被邮箱拦截，请查看纯文本正文。
      </div>
    </div>
  </div>
</body>
</html>
"""


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="yaml config file to use", default="config.yaml")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("环境变量中未找到 OPENAI_API_KEY")
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    topic = config.get("topic", "")
    categories = config.get("categories", []) or []
    threshold = float(config.get("threshold", 0))
    interest = str(config.get("interest", "") or "")

    # Generate digest
    body_fragment, plain_text, used_interest, _ = generate_digest(
        topic=topic,
        categories=categories,
        interest=interest,
        threshold=threshold,
    )

    # Chinese subject + subtitle
    today_cn = date.today().strftime("%Y-%m-%d")
    subject_cn = f"个性化 arXiv 日报（{today_cn}）"
    subtitle_cn = "建议：收藏此邮件以便回看；如 HTML 被拦截请看纯文本版本。"

    # Config snapshot (make it helpful for tuning)
    cfg_lines = [
        f"topic: {topic}",
        f"categories: {categories}",
        f"threshold: {threshold}",
        f"interest: {interest[:300] + ('…' if len(interest) > 300 else '')}",
        f"mode: {'interest_relevance' if used_interest else 'no_interest'}",
    ]
    config_snapshot = "\n".join(cfg_lines)

    full_html = wrap_full_html(subject_cn, subtitle_cn, body_fragment, config_snapshot)

    # Ensure non-empty fallback
    if not plain_text.strip():
        plain_text = "今天没有论文命中你的筛选条件。建议降低 threshold 或扩大 topic/categories。"

    # Write outputs
    with open("digest.html", "w", encoding="utf-8") as f:
        f.write(full_html)

    with open("digest.txt", "w", encoding="utf-8") as f:
        f.write(f"{subject_cn}\n\n{plain_text}\n\n---\n{config_snapshot}\n")

    print(f"[OK] 生成完成：digest.html（{len(full_html)} chars），digest.txt（{len(plain_text)} chars）")
    print("[INFO] 邮件发送由 GitHub Actions（SMTP）负责。")
