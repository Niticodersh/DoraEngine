"""
Graph Visualizer — converts a NetworkX graph to an interactive Pyvis HTML string.
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Optional

import networkx as nx

try:
    from pyvis.network import Network
    _PYVIS_AVAILABLE = True
except ImportError:
    _PYVIS_AVAILABLE = False


# ── Colour palette per domain (cycled) ────────────────────────────────
_DOMAIN_COLOURS = [
    "#7c3aed", "#3b82f6", "#06b6d4", "#10b981",
    "#f59e0b", "#ef4444", "#ec4899", "#8b5cf6",
]


def _domain_color(domain: str, palette: dict) -> str:
    if domain not in palette:
        palette[domain] = _DOMAIN_COLOURS[len(palette) % len(_DOMAIN_COLOURS)]
    return palette[domain]


def _build_injected_ui(domain_palette: dict) -> str:
    """Build the legend, walkthrough, and toolbar HTML to inject into the graph."""

    # ── Legend items ──────────────────────────────────────────────────
    domain_legend_items = ""
    for domain, colour in list(domain_palette.items())[:8]:
        domain_legend_items += f"""
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
            <div style="width:10px;height:10px;border-radius:50%;background:{colour};flex-shrink:0;"></div>
            <span style="font-size:11px;color:#d1d5db;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:130px;">{domain}</span>
        </div>"""

    legend_html = f"""
    <div id="dora-legend" style="
        position:fixed; top:12px; right:12px; z-index:1000;
        background:rgba(15,15,26,0.92); border:1px solid rgba(124,58,237,0.3);
        border-radius:10px; padding:12px 14px; min-width:160px;
        backdrop-filter:blur(8px); font-family:system-ui,sans-serif;
        box-shadow:0 4px 24px rgba(0,0,0,0.4);">
        <div style="font-size:10px;font-weight:700;color:#7c3aed;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px;">Legend</div>

        <div style="font-size:10px;color:#9ca3af;margin-bottom:6px;font-weight:600;">Website sources</div>
        {domain_legend_items}

        <div style="height:1px;background:rgba(255,255,255,0.08);margin:10px 0;"></div>

        <div style="font-size:10px;color:#9ca3af;margin-bottom:6px;font-weight:600;">Line types</div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
            <div style="width:22px;height:2px;background:#7c3aed;border-radius:2px;flex-shrink:0;"></div>
            <span style="font-size:11px;color:#d1d5db;">Same topic / idea</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
            <div style="width:22px;height:2px;background:#3b82f6;border-radius:2px;flex-shrink:0;"></div>
            <span style="font-size:11px;color:#d1d5db;">From the same article</span>
        </div>
    </div>"""

    # ── Walkthrough — plain-English story steps ───────────────────────
    steps = [
        (
            "This map shows your research",
            "Every bubble you see is a piece of real content DoraEngine found on the web to answer your question — like sticky notes it took during research."
        ),
        (
            "Connected bubbles share ideas",
            "When two bubbles are linked by a line, it means those two pieces of information are related — they talk about similar things. Bubbles with many connections are the most important ideas."
        ),
        (
            "Colours = different websites",
            "Each colour represents a different website. Bubbles of the same colour all came from the same source. Check the legend (top-right) to see which colour is which site."
        ),
        (
            "Try hovering over any bubble",
            "Move your mouse over a bubble to read a snippet of that content. You can zoom in, drag the map around, or use the \"Fit view\" button to zoom back out."
        ),
    ]
    steps_json = json.dumps(steps)

    walkthrough_html = f"""
    <div id="dora-walkthrough" style="
        position:fixed; bottom:16px; left:12px; z-index:1000;
        background:rgba(15,15,26,0.95);
        border:1.5px solid transparent;
        border-radius:12px; padding:16px 18px; width:272px;
        backdrop-filter:blur(10px); font-family:system-ui,sans-serif;
        box-shadow:0 4px 30px rgba(0,0,0,0.5);
        background-clip:padding-box;
        outline:1.5px solid;
        outline-color:rgba(99,102,241,0.35);">

        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
            <div>
                <div style="font-size:9px;font-weight:700;color:#6366f1;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:2px;">Guide</div>
                <div style="font-size:12px;font-weight:600;color:#f9fafb;">How to read this map</div>
            </div>
            <span id="dora-step-counter" style="font-size:11px;color:#4b5563;background:rgba(255,255,255,0.06);padding:2px 8px;border-radius:20px;"></span>
        </div>

        <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:14px;">
            <div id="dora-step-num" style="
                min-width:32px;height:32px;border-radius:50%;
                background:linear-gradient(135deg,#7c3aed,#3b82f6);
                display:flex;align-items:center;justify-content:center;
                font-size:15px;font-weight:700;color:#fff;flex-shrink:0;"></div>
            <div>
                <div id="dora-step-title" style="font-size:13px;font-weight:600;color:#f3f4f6;margin-bottom:5px;line-height:1.3;"></div>
                <div id="dora-step-body" style="font-size:11.5px;color:#9ca3af;line-height:1.6;"></div>
            </div>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;">
            <button id="dora-prev" onclick="doraStep(-1)" style="
                background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);
                color:#9ca3af;border-radius:6px;padding:5px 12px;font-size:11px;cursor:pointer;">← Back</button>
            <div id="dora-dots" style="display:flex;gap:5px;"></div>
            <button id="dora-next" onclick="doraStep(1)" style="
                background:linear-gradient(135deg,rgba(124,58,237,0.3),rgba(59,130,246,0.2));
                border:1px solid rgba(124,58,237,0.4);
                color:#c4b5fd;border-radius:6px;padding:5px 12px;font-size:11px;cursor:pointer;">Next →</button>
        </div>

        <div style="margin-top:12px;text-align:center;border-top:1px solid rgba(255,255,255,0.06);padding-top:10px;">
            <button onclick="document.getElementById('dora-walkthrough').style.display='none';sessionStorage.setItem('dora_tour_done','1');" style="
                background:transparent;border:none;color:#4b5563;font-size:10.5px;cursor:pointer;
                text-decoration:none;letter-spacing:0.02em;">
                Got it — hide this guide ✓
            </button>
        </div>
    </div>
    <script>
    (function() {{
        var steps = {steps_json};
        var cur = 0;
        function render() {{
            document.getElementById('dora-step-num').textContent   = cur + 1;
            document.getElementById('dora-step-title').textContent = steps[cur][0];
            document.getElementById('dora-step-body').innerHTML    = steps[cur][1];
            document.getElementById('dora-step-counter').textContent = (cur+1) + ' / ' + steps.length;
            var dots = document.getElementById('dora-dots');
            dots.innerHTML = '';
            for (var i=0; i<steps.length; i++) {{
                var d = document.createElement('div');
                d.style.cssText = 'width:6px;height:6px;border-radius:50%;transition:background 0.2s;background:'
                    + (i===cur ? 'linear-gradient(135deg,#7c3aed,#3b82f6)' : '#374151');
                dots.appendChild(d);
            }}
            document.getElementById('dora-prev').style.opacity = cur===0 ? '0.3' : '1';
            document.getElementById('dora-prev').style.pointerEvents = cur===0 ? 'none' : 'auto';
            document.getElementById('dora-next').style.opacity = cur===steps.length-1 ? '0.3' : '1';
            document.getElementById('dora-next').style.pointerEvents = cur===steps.length-1 ? 'none' : 'auto';
        }}
        window.doraStep = function(d) {{
            cur = Math.max(0, Math.min(steps.length-1, cur+d));
            render();
        }};
        if (sessionStorage.getItem('dora_tour_done') === '1') {{
            document.getElementById('dora-walkthrough').style.display = 'none';
        }}
        render();
    }})();
    </script>"""

    # ── Toolbar strip — Fit view only (cluster removed: vis.js clusterByColor
    # requires color objects, not strings — silently fails with string palette) ─
    toolbar_html = """
    <div id="dora-toolbar" style="
        position:fixed; top:12px; left:12px; z-index:1000;
        display:flex;gap:8px;align-items:center;
        font-family:system-ui,sans-serif;">
        <div style="
            background:rgba(15,15,26,0.9);border:1px solid rgba(124,58,237,0.25);
            border-radius:8px;padding:6px 12px;
            font-size:11px;font-weight:700;color:#8b5cf6;letter-spacing:0.04em;">
            ⬡ Knowledge Graph
        </div>
        <button onclick="if(window.network){window.network.fit({animation:{duration:600,easingFunction:'easeInOutQuad'}});}" style="
            background:rgba(15,15,26,0.9);border:1px solid rgba(255,255,255,0.1);
            border-radius:8px;padding:6px 10px;font-size:11px;color:#d1d5db;
            cursor:pointer;backdrop-filter:blur(6px);"
            title="Zoom to fit all nodes into view">⊞ Fit view</button>
    </div>"""

    return legend_html + walkthrough_html + toolbar_html


def graph_to_html(
    G: nx.Graph,
    height: str = "520px",
    width: str = "100%",
    max_nodes: int = 80,
) -> str:
    """
    Convert a NetworkX graph to an interactive Pyvis HTML string.

    Node attributes expected (all optional):
        - content   : text snippet shown in tooltip
        - source    : URL of the source page
        - domain    : domain name for colour coding
        - chunk_index: integer position within source

    Returns:
        Full self-contained HTML string (includes pyvis JS + legend + walkthrough).
        Falls back to a plain SVG placeholder if pyvis is unavailable.
    """
    if not _PYVIS_AVAILABLE:
        return _fallback_html(G)

    # Subsample if huge
    if G.number_of_nodes() > max_nodes:
        # Keep the highest-degree nodes
        top_nodes = sorted(G.degree, key=lambda x: x[1], reverse=True)[:max_nodes]
        top_ids   = {n for n, _ in top_nodes}
        G = G.subgraph(top_ids).copy()

    net = Network(
        height=height,
        width=width,
        bgcolor="#0f0f1a",
        font_color="#e5e7eb",
        notebook=False,
        directed=False,
    )

    domain_palette: dict = {}

    for node_id, data in G.nodes(data=True):
        domain   = data.get("domain", "unknown")
        colour   = _domain_color(domain, domain_palette)
        snippet  = (data.get("content") or "")[:200]
        label    = f"{domain}#{data.get('chunk_index', 0)}"
        title    = f"<b>{domain}</b><br/>{snippet}"

        net.add_node(
            node_id,
            label=label,
            title=title,
            color=colour,
            size=14,
            font={"size": 9, "color": "#e5e7eb"},
        )

    for src, dst, edata in G.edges(data=True):
        edge_type = edata.get("type", "semantic")
        weight    = edata.get("weight", 0.5)
        edge_col  = "#7c3aed" if edge_type == "semantic" else "#3b82f6"
        net.add_edge(
            src, dst,
            value=float(weight),
            color=edge_col,
            title=f"{edge_type} ({weight:.2f})",
        )

    # Physics config for nice layout
    net.set_options(json.dumps({
        "physics": {
            "enabled": True,
            "barnesHut": {
                "gravitationalConstant": -8000,
                "centralGravity": 0.3,
                "springLength": 100,
                "springConstant": 0.04,
                "damping": 0.09,
            },
            "stabilization": {"iterations": 150},
        },
        "interaction": {
            "hover": True,
            "tooltipDelay": 100,
            "navigationButtons": False,
        },
        "edges": {
            "smooth": {"type": "dynamic"},
            "width": 1.2,
        },
    }))

    # Store network in window for toolbar buttons
    net.html = True

    # Write to temp file and read back as string
    with tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8"
    ) as f:
        tmp_path = f.name

    try:
        net.write_html(tmp_path, notebook=False)
        with open(tmp_path, "r", encoding="utf-8") as f:
            html = f.read()
    finally:
        os.unlink(tmp_path)

    # Expose vis Network instance as window.network for toolbar controls
    expose_script = """
    <script>
    (function waitForNetwork() {
        if (typeof network !== 'undefined') {
            window.network = network;
        } else {
            setTimeout(waitForNetwork, 100);
        }
    })();
    </script>"""

    # Inject UI enrichments + network exposure before </body>
    injected = _build_injected_ui(domain_palette) + expose_script
    html = html.replace("</body>", injected + "\n</body>")
    return html


def _fallback_html(G: nx.Graph) -> str:
    """Simple SVG fallback when pyvis is not installed."""
    n = G.number_of_nodes()
    e = G.number_of_edges()
    return f"""
    <div style="
        background:#0f0f1a; border-radius:12px; padding:40px;
        text-align:center; color:#7c3aed; font-family:sans-serif;
    ">
        <div style="font-size:48px;">🕸️</div>
        <div style="font-size:18px; margin-top:12px;">Knowledge Graph</div>
        <div style="font-size:13px; color:#6b7280; margin-top:8px;">
            {n} nodes · {e} edges
        </div>
        <div style="font-size:11px; color:#ef4444; margin-top:16px;">
            Install pyvis to see the interactive graph
        </div>
    </div>
    """

