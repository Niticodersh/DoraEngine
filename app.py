"""
DoraEngine — Premium Autonomous AI Research Agent
Streamlit UI: Perplexity-level design with dark glass-morphism theme
"""
from __future__ import annotations

import os
import re
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

import streamlit as st

# Suppress transformers import warnings for optional dependencies
import warnings
warnings.filterwarnings("ignore", category=ImportWarning)

load_dotenv()

# Hoist the heavy pipeline import to module load time so that the FIRST
# query submission doesn't pay a multi-second import cost (torch, transformers,
# sentence-transformers, langgraph, etc.) before Streamlit can flush the
# initial progress UI to the browser. Paid once at app startup instead.
from pipeline.orchestrator import run_research  # noqa: E402

def clean_text(text: str) -> str:
    import re

    # Fix spaced letters like "p e r b a r r e l"
    text = re.sub(r'(\b\w\b\s+){2,}', lambda m: m.group(0).replace(" ", ""), text)

    # Normalize spaces
    text = re.sub(r'\s+', ' ', text)

    # Remove markdown bold artifacts
    text = text.replace("**", "")

    # Fix unicode spaces
    text = text.replace("\xa0", " ").replace("\u202f", " ")

    return text.strip()

# ─── Page config (MUST be first Streamlit call) ───────────────────────
st.set_page_config(
    page_title="DoraEngine · AI Research Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Injected CSS ─────────────────────────────────────
css_path = Path(__file__).parent / "styles" / "theme.css"
CUSTOM_CSS = css_path.read_text(encoding="utf-8")

st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

def generate_followup_questions(query: str, answer: str, n: int = 5) -> list[str]:
    """Generate contextual follow-up questions using LLM, with fallback."""
    cache_key = f"followups_{hash(query + answer)}_{n}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    # Try LLM first
    try:
        from utils.llm_client import LLMClient
        llm = LLMClient()
        prompt = f"""Based on this question: '{query}' and this answer: '{answer}', generate {n} contextual follow-up questions that would help explore the topic further.

Make them specific, insightful, and varied. Focus on:
- Deeper understanding of key concepts
- Practical applications
- Related topics or comparisons
- Potential limitations or risks
- Future developments

Return only the questions, one per line, numbered 1. 2. etc."""

        response = llm.chat([{"role": "user", "content": prompt}])
        # Parse numbered list
        questions = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering
                if line[0].isdigit():
                    line = re.sub(r'^\d+\.\s*', '', line)
                elif line.startswith('-'):
                    line = line[1:].strip()
                questions.append(line)

        if len(questions) >= n:
            st.session_state[cache_key] = questions[:n]
            return st.session_state[cache_key]
    except Exception:
        pass

    # Fallback questions
    fallback_questions = [
        f"What is the next most important question about {query}?",
        f"How can I apply this answer in practice?",
        f"What risks should I watch for with this topic?",
        f"What related topic should I explore next?",
        f"What are the common myths about this subject?",
    ]
    st.session_state[cache_key] = fallback_questions[:n]
    return st.session_state[cache_key]


def _conf_class(conf: float) -> str:
    if conf >= 0.8:
        return "high"
    elif conf >= 0.6:
        return "medium"
    else:
        return "low"


def _conf_label(conf: float) -> str:
    if conf >= 0.8:
        return "High"
    elif conf >= 0.6:
        return "Medium"
    else:
        return "Low"


def _conf_icon(conf: float) -> str:
    if conf >= 0.8:
        return "🟢"
    elif conf >= 0.6:
        return "🟡"
    else:
        return "🔴"


SUGGESTIONS = [
    "Latest advances in AI agents",
    "Explain quantum computing simply",
    "Best open-source LLMs in 2025",
    "How AlphaFold works",
    "Future of self-driving cars",
    "Graph RAG vs vector RAG",
]

AGENT_STEPS = [
    ("🧠 QueryAgent",    "Understanding your question…",        0.08),
    ("🔍 SearchAgent",   "Searching the web for sources…",      0.20),
    ("⚡ ScraperAgent",  "Reading the most relevant pages…",    0.42),
    ("🕸️ GraphBuilder",  "Organising what we found…",           0.60),
    ("🔮 GraphRAG",      "Connecting related information…",     0.72),
    ("📊 RankingAgent",  "Picking the most useful details…",    0.82),
    ("💭 ReasoningAgent","Thinking it through…",                0.90),
    ("✍️ AnswerAgent",   "Writing your answer…",                0.97),
]


# ─── Main App ─────────────────────────────────────────────────────────

def render_hero():
    st.markdown("""
    <div class="dora-hero">
      <div class="dora-logo">🔍 DoraEngine</div>
      <div class="dora-tagline">
        Autonomous AI Research Agent · Graph RAG · Multi-step Reasoning
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_suggestions():
    if st.session_state.get("result") is not None:
        return

    # Helper text above pills
    st.markdown(
        '<div class="suggestion-helper">Try one of these, or ask your own question</div>',
        unsafe_allow_html=True,
    )

    # Pill layout: one column per suggestion, pills flow in a single row.
    # CSS (.suggestion-pill-wrap) restyles the st.button inside as a pill.
    st.markdown('<div class="suggestion-pill-wrap">', unsafe_allow_html=True)
    cols = st.columns(len(SUGGESTIONS))
    for i, suggestion in enumerate(SUGGESTIONS):
        with cols[i]:
            if st.button(suggestion, key=f"sug_{i}", width='stretch'):
                st.session_state["pending_query"] = suggestion
                st.session_state["auto_search"] = True
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def render_search_bar() -> tuple[str, bool]:
    # Apply a suggested query before rendering the input widget
    pending = st.session_state.get("pending_query")
    if pending:
        st.session_state["main_query"] = pending
        st.session_state["pending_query"] = None

    is_researching = st.session_state.get("is_researching", False)

    col_l, col_c, col_r = st.columns([1, 6, 1])
    with col_c:
        st.markdown('<div class="search-wrap"><div class="search-inner">', unsafe_allow_html=True)
        query = st.text_input(
            label      = "query",
            label_visibility = "collapsed",
            placeholder= "Ask anything… I'll research, verify, and explain it for you",
            value      = st.session_state.get("main_query", ""),
            key        = "main_query",
            disabled   = is_researching,
        )
        st.markdown('</div></div>', unsafe_allow_html=True)

        # Helper text below the input — empty-state guidance
        # st.markdown(
        #     '<div class="suggestion-helper" style="margin-top:0.9rem;margin-bottom:0.6rem;">'
        #     "Ask anything. I'll research, verify, and explain it for you."
        #     '</div>',
        #     unsafe_allow_html=True,
        # )

        btn_label = "⏳  Researching…" if is_researching else "🔍  Research This"
        clicked = st.button(
            btn_label,
            width='stretch',
            key="search_btn",
            disabled=is_researching,
        )

    return query.strip(), clicked


def render_progress(placeholder, label: str):
    # Minimal, non-technical progress card: just a header and the current
    # stage message. No per-agent breakdown — the progress bar itself
    # communicates position in the pipeline.
    #
    # Emitted as a single compact HTML string (no leading indentation, no
    # blank lines) so Streamlit's CommonMark parser treats it as one HTML
    # block instead of escaping the tags.
    html = (
        '<div class="status-container">'
        '<div class="status-title">⚡ Research in Progress</div>'
        f'<div class="step-text" style="font-size:0.95rem;color:#d1d5db;">{label}</div>'
        '</div>'
    )
    placeholder.markdown(html, unsafe_allow_html=True)


def render_stats_bar(result):
    """Simplified, user-friendly research summary.

    Replaces the old 6-column grid of metrics with a single pill-style line
    showing the two things users actually care about: how long it took and
    how many sources it was based on.
    """
    ok_pages = sum(1 for p in result.scraped_pages if p.success) if result.scraped_pages else 0
    sources  = len(result.search_results)
    conf_pct = int((result.final_answer.confidence if result.final_answer else 0) * 100)
    total_t  = sum(result.timings.values()) if result.timings else 0

    st.markdown(
        f'<div class="research-summary">'
        f'<span>⚡ Research completed in <span class="val">{total_t:.1f}s</span></span>'
        f'<span>📊 Based on <span class="val">{ok_pages or sources}</span> sources</span>'
        f'<span>✦ Confidence <span class="val">{conf_pct}%</span></span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_answer_tab(result):
    fa = result.final_answer
    if not fa:
        st.warning("No answer generated.")
        return

    # Confidence badge
    cls   = _conf_class(fa.confidence)
    label = _conf_label(fa.confidence)
    icon  = _conf_icon(fa.confidence)
    pct   = int(fa.confidence * 100)
    st.markdown(
        f'<span class="confidence-badge {cls}">{icon} {label} · {pct}%</span>',
        unsafe_allow_html=True,
    )

    # Answer card
    st.markdown('<div class="answer-card">', unsafe_allow_html=True)
    st.markdown(fa.answer, unsafe_allow_html=False)
    
    # Inject references into the answer view
    if fa.citations:
        st.markdown("<hr style='margin: 2rem 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        st.markdown("### References")
        for cit in fa.citations:
            domain = cit.domain or "Link"
            title = cit.title.replace('<', '&lt;').replace('>', '&gt;')
            st.markdown(f"**[{cit.number}]** {title} — [{domain}]({cit.url})")

    st.markdown('</div>', unsafe_allow_html=True)

    # Key findings (from reasoning)
    if result.reasoning and result.reasoning.key_findings:
        st.markdown('<div class="section-header">💡 Key Findings</div>', unsafe_allow_html=True)
        cards_html = "".join(
            f'<div class="finding-card">• {f}</div>'
            for f in result.reasoning.key_findings
        )
        st.markdown(f'<div class="findings-grid">{cards_html}</div>', unsafe_allow_html=True)

    # ── Follow-up questions ("Explore further") ──────────────────────
    render_followups(result)


def render_followups(result):
    """LLM-generated contextual follow-up questions. Cached per query."""
    fa = result.final_answer
    if not fa or not fa.answer:
        return

    followups = generate_followup_questions(result.query, fa.answer, n=6)
    if not followups:
        return

    st.markdown(
        '<div class="followup-title">🔍 Explore further</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="followup-wrap">', unsafe_allow_html=True)

    # Render follow-ups in a 2-column grid
    cols = st.columns(2)
    for i, q in enumerate(followups):
        with cols[i % 2]:
            if st.button(q, key=f"followup_{i}", width='stretch'):
                st.session_state["pending_query"] = q
                st.session_state["auto_search"] = True
                # Clear prior result so the new research starts fresh
                st.session_state.pop("result", None)
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def render_sources_tab(result):
    sources = result.search_results or []
    if not sources:
        st.info("No sources were retrieved.")
        return

    scraped_urls = {p.url for p in result.scraped_pages or [] if p.success}

    # Filter checkbox
    show_only_scraped = st.checkbox("Show only successfully scraped sources", value=False)

    if show_only_scraped:
        filtered_sources = [src for src in sources if src.url in scraped_urls]
        header_text = f"📚 {len(filtered_sources)} Scraped Sources"
    else:
        filtered_sources = sources
        header_text = f"📚 {len(sources)} Sources Retrieved"

    st.markdown(
        f'<div class="section-header">{header_text}</div>',
        unsafe_allow_html=True,
    )

    # Prepare data for table
    data = []
    chunk_map: dict[str, str] = {}
    for chunk in (result.ranked_chunks or []):
        if chunk.url not in chunk_map:
            chunk_map[chunk.url] = chunk.content[:250]

    for src in filtered_sources:
        snippet = chunk_map.get(src.url, src.snippet or "")
        data.append({
            "Title": src.title,
            "URL": src.url,
            "Domain": src.domain,
            "Snippet": snippet,
            "Scraped": "Yes" if src.url in scraped_urls else "No"
        })

    st.dataframe(data, width='stretch')


def render_reasoning_tab(result):
    """User-facing reasoning view.

    Default: a clean visual flow showing HOW the answer was derived, with
    dynamic content pulled from the pipeline state. No agent names, no raw
    logs, no timing metrics.

    Expandable: a structured list of the underlying reasoning steps (still
    sanitised — no agent identifiers, just numbered insights).
    """
    reasoning = result.reasoning
    query_plan = result.query_plan

    if not reasoning and not query_plan:
        st.info("No reasoning trace available.")
        return

    st.markdown(
        '<div class="reasoning-header">🧠 How this answer was derived</div>',
        unsafe_allow_html=True,
    )

    # ── Build dynamic content for each flow stage ─────────────────────
    query_text = (result.query or "Your question")[:90]

    # Stage 2 — key concepts from the query plan
    if query_plan and query_plan.keywords:
        concepts = " • ".join(query_plan.keywords[:5])
    else:
        concepts = "Topic and intent identified"

    # Stage 3 — source insights
    ok_pages = sum(1 for p in (result.scraped_pages or []) if p.success)
    total_sources = len(result.search_results or [])
    if ok_pages:
        source_line = f"Insights extracted from {ok_pages} of {total_sources} sources"
    elif total_sources:
        source_line = f"Reviewed {total_sources} sources"
    else:
        source_line = "Source review step"

    # Stage 4 — cross-validation
    if reasoning and reasoning.confidence:
        conf_pct = int(reasoning.confidence * 100)
        if conf_pct >= 75:
            validation_line = f"Cross-validated across sources ({conf_pct}% agreement)"
        elif conf_pct >= 50:
            validation_line = f"Moderate cross-source agreement ({conf_pct}%)"
        else:
            validation_line = f"Limited source agreement ({conf_pct}%)"
    else:
        validation_line = "Cross-checked for consistency"

    # Stage 5 — synthesis
    if reasoning and reasoning.steps:
        synth_line = f"Synthesised from {len(reasoning.steps)} reasoning steps"
    else:
        synth_line = "Final answer composed"

    flow_stages: list[tuple[str, str]] = [
        ("Your Question",              query_text),
        ("Key Concepts Identified",    concepts),
        ("Source Insights Extracted",  source_line),
        ("Cross-Validation",           validation_line),
        ("Final Answer Synthesised",   synth_line),
    ]

    # ── Render the visual flow ────────────────────────────────────────
    flow_parts = ['<div class="flow-container">']
    for i, (label, content) in enumerate(flow_stages):
        flow_parts.append(
            f'<div class="flow-step">'
            f'<div class="flow-step-label">{label}</div>'
            f'<div class="flow-step-content">{content}</div>'
            f'</div>'
        )
        if i < len(flow_stages) - 1:
            flow_parts.append('<div class="flow-arrow">↓</div>')
    flow_parts.append('</div>')
    st.markdown("".join(flow_parts), unsafe_allow_html=True)

    # ── Expandable detail: structured reasoning insights ──────────────
    if reasoning and reasoning.steps:
        with st.expander("🔍 View detailed reasoning", expanded=False):
            detail_parts: list[str] = []
            for i, step in enumerate(reasoning.steps, 1):
                # Sanitise: use only action + detail, never agent name
                action = (step.action or "").strip() or f"Insight {i}"
                detail = (step.detail or "").strip()
                text = f"<strong>{action}.</strong>"
                if detail:
                    text += f" {detail}"
                detail_parts.append(
                    f'<div class="reasoning-detail-item">'
                    f'<div class="reasoning-detail-num">{i}</div>'
                    f'<div class="reasoning-detail-text">{text}</div>'
                    f'</div>'
                )
            st.markdown("".join(detail_parts), unsafe_allow_html=True)

            if reasoning.reasoning_summary:
                st.markdown(
                    f'<div style="margin-top:1.2rem;padding:1rem 1.2rem;'
                    f'background:rgba(168,85,247,0.06);border-left:3px solid #a855f7;'
                    f'border-radius:8px;color:#d1d5db;font-size:0.88rem;line-height:1.6;">'
                    f'<strong style="color:#a855f7;">Summary.</strong> '
                    f'{reasoning.reasoning_summary}</div>',
                    unsafe_allow_html=True,
                )


def render_graph_tab(result):
    gs = result.graph_state
    if not gs or gs.graph.number_of_nodes() == 0:
        st.info("Knowledge graph is empty — not enough content was scraped.")
        return

    nodes = gs.graph.number_of_nodes()
    edges = gs.graph.number_of_edges()

    st.markdown(f"""
    <div class="section-header">🌐 Knowledge Graph · {nodes} nodes · {edges} edges</div>
    """, unsafe_allow_html=True)

    try:
        from utils.graph_viz import graph_to_html
        from base64 import b64encode

        html = graph_to_html(gs.graph, height="560px")
        encoded = b64encode(html.encode("utf-8")).decode("ascii")
        src = f"data:text/html;charset=utf-8;base64,{encoded}"

        st.markdown('<div class="graph-container">', unsafe_allow_html=True)
        st.iframe(src, width='stretch', height=560)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <div style="font-size:0.78rem;color:#475569;margin-top:0.8rem;text-align:center;">
          🟣 Hover nodes for content · Edge colour: <span style="color:#a855f7">■</span> semantic &nbsp;
          <span style="color:#ec4899">■</span> sequential · Drag to rearrange
        </div>
        """, unsafe_allow_html=True)

        # Add chart: Top domains by node count
        domains = [gs.graph.nodes[n].get("domain", "") for n in gs.graph.nodes()]
        from collections import Counter
        domain_counts = Counter(domains)
        top_domains = dict(domain_counts.most_common(10))
        if top_domains:
            st.subheader("📊 Top Domains in Graph")
            st.bar_chart(top_domains)

    except Exception as e:
        st.error(f"Graph rendering error: {e}")


def render_export(result):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">📄 Export Results</div>', unsafe_allow_html=True)

    from utils.pdf_export import generate_pdf

    fa        = result.final_answer
    reasoning = result.reasoning

    if not fa:
        st.info("Run a query first to enable export.")
        return

    sources_for_pdf = [
        {
            "title":   getattr(s, "title",  ""),
            "url":     getattr(s, "url",    ""),
            "snippet": getattr(s, "snippet", ""),
            "domain":  getattr(s, "domain", ""),
        }
        for s in result.search_results[:15]
    ]

    steps_for_pdf = [
        {
            "agent":  step.get("agent", ""),
            "action": step.get("action", ""),
            "detail": step.get("detail", ""),
        }
        for step in (result.step_log or [])
    ]

    if reasoning:
        for rs in reasoning.steps:
            steps_for_pdf.append({
                "agent":  "ReasoningAgent",
                "action": rs.action,
                "detail": rs.detail,
            })

    try:
        pdf_bytes = generate_pdf(
            query           = result.query,
            answer          = fa.answer,
            sources         = sources_for_pdf,
            reasoning_steps = steps_for_pdf,
            confidence      = fa.confidence,
            timestamp       = datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        )

        safe_query = result.query[:30].replace(" ", "_").replace("/", "-")
        filename   = f"DoraEngine_{safe_query}.pdf"

        col1, col2 = st.columns([2, 5])
        with col1:
            st.download_button(
                label     = "⬇ Download PDF Report",
                data      = pdf_bytes,
                file_name = filename,
                mime      = "application/pdf",
                use_container_width=True,
            )

    except Exception as e:
        st.error(f"PDF generation failed: {e}")


def run_pipeline_with_ui(query: str) -> None:
    """Run the research pipeline with live progress UI.

    UX flow:
      1. Immediately (before any backend work) render the progress panel with
         stage 0 active, so the user gets instant feedback on submit.
      2. As LangGraph streams node completions, advance the active stage and
         update the progress bar + status panel live.
      3. On completion, briefly show "Research complete!" then clear.
    """
    # Mark session as researching (used by render_search_bar to disable the
    # input + button and show "⏳ Researching…" state for this run).
    st.session_state["is_researching"] = True

    # ── 1. Render progress UI *immediately* on submit ───────────────────
    # (run_research is imported at module level so there is no hidden
    # import cost between the click and the first visible UI frame.)
    progress_ph = st.empty()
    _, first_action, first_prog = AGENT_STEPS[0]
    prog_bar = st.progress(first_prog, text=first_action)
    render_progress(progress_ph, first_action)

    agent_to_stage: dict[str, int] = {}
    for idx, (agent, _, _) in enumerate(AGENT_STEPS):
        agent_to_stage[agent] = idx
        # Support both styled agent labels and plain agent names from the pipeline.
        if " " in agent:
            plain = agent.split(" ", 1)[-1]
            agent_to_stage[plain] = idx

    seen_agents: set[int] = set()

    def on_progress(agent: str, action: str):
        """Called by the orchestrator when a pipeline node logs progress.

        Advance the UI only once per agent stage and ignore duplicate logs.
        """
        idx = agent_to_stage.get(agent)
        if idx is None or idx in seen_agents:
            return
        seen_agents.add(idx)

        if idx == 0:
            # First stage is already displayed immediately.
            return

        _, next_action, next_prog = AGENT_STEPS[idx]
        prog_bar.progress(next_prog, text=next_action)
        render_progress(progress_ph, next_action)

    try:
        result = run_research(query, progress_callback=on_progress)
    finally:
        # Always clear the researching flag, even on exception, so the
        # button returns to its normal state.
        st.session_state["is_researching"] = False

    # ── 3. Wrap up ──────────────────────────────────────────────────────
    progress_ph.empty()
    prog_bar.progress(1.0, text="✓ Research complete!")
    time.sleep(0.4)
    prog_bar.empty()

    # Store in session
    st.session_state["result"] = result
    st.session_state["query"]  = query


# ─── Entry Point ──────────────────────────────────────────────────────

def main():
    render_hero()

    query, clicked = render_search_bar()
    searching = st.session_state.get("is_researching", False)
    auto_search = st.session_state.get("auto_search", False)

    if not st.session_state.get("result") and not searching and not clicked and not auto_search:
        render_suggestions()

    # Check API key
    if clicked or (query and st.session_state.get("auto_search")):
        if not (os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")):
            st.markdown("""
            <div class="error-card">
              ⚠️ <strong>GROQ_API_KEY not set.</strong><br>
              Create a <code>.env</code> file in the project root with:<br>
              <code>GROQ_API_KEY=your_key_here</code>
            </div>
            """, unsafe_allow_html=True)
            return

        if not query:
            st.warning("Please enter a research query.")
            return

        if not st.session_state.get("auto_search", False):
            st.session_state["manual_search_done"] = True

        run_pipeline_with_ui(query)
        st.session_state["auto_search"] = False

    # ── Results ────────────────────────────────────────────────────────
    result = st.session_state.get("result")

    if result:
        if not result.success:
            st.markdown(f"""
            <div class="error-card">
              ❌ <strong>Research failed</strong><br>
              <pre style="font-size:0.75rem;margin-top:8px;color:#f87171">{result.error}</pre>
            </div>
            """, unsafe_allow_html=True)
            return

        # Stats bar
        render_stats_bar(result)

        tab_names = ["✍️ Answer", "📚 Sources", "🧠 Reasoning", "🌐 Graph"]
        tabs = st.tabs(tab_names)

        with tabs[0]:
            render_answer_tab(result)
            render_export(result)

        with tabs[1]:
            render_sources_tab(result)

        with tabs[2]:
            render_reasoning_tab(result)

        with tabs[3]:
            render_graph_tab(result)

    # Footer
    st.markdown("""
    <div class="dora-footer">
      DoraEngine · Autonomous AI Research Agent · Powered by Groq · Graph RAG · LangGraph
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
