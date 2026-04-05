"""
Graph Visualizer — converts a NetworkX graph to an interactive Pyvis HTML string.
"""
from __future__ import annotations

import hashlib
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
        Full self-contained HTML string (includes pyvis JS).
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
