import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { exportPdf, fetchConfig, streamResearch } from "./api";

const DEFAULT_TABS = ["answer", "sources", "reasoning", "graph"];

function MarkdownAnswer({ text }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}>{text || ""}</ReactMarkdown>
  );
}

function StatPill({ label, value }) {
  return (
    <div className="stat-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ProgressPanel({ activeStage, stageHistory, researching }) {
  if (!researching && !activeStage) {
    return null;
  }

  const progress = activeStage?.progress || 0.05;

  return (
    <section className="status-card">
      <div className="status-header">
        <span className="status-eyebrow">Research in Progress</span>
        <strong>{activeStage?.label || "Preparing research..."}</strong>
      </div>
      <div className="progress-shell">
        <div className="progress-bar" style={{ width: `${progress * 100}%` }} />
      </div>
      <div className="status-list">
        {stageHistory.map((item) => (
          <div key={`${item.agent}-${item.action}`} className="status-row">
            <span className="status-dot" />
            <span className="status-agent">{item.agent}</span>
            <span className="status-text">{item.stage?.label || item.action}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function AnswerTab({ result, onResearch, onExport }) {
  const answer = result?.final_answer;
  const reasoning = result?.reasoning;

  if (!answer) {
    return <div className="empty-card">No answer generated yet.</div>;
  }

  return (
    <div className="tab-stack">
      <section className="content-card">
        <div className="confidence-badge">
          Confidence {Math.round((answer.confidence || 0) * 100)}%
        </div>
        <div className="markdown-body">
          <MarkdownAnswer text={answer.answer} />
        </div>
        {!!answer.citations?.length && (
          <div className="references">
            <h3>References</h3>
            {answer.citations.map((citation) => (
              <a key={citation.number} href={citation.url} target="_blank" rel="noreferrer">
                [{citation.number}] {citation.title} - {citation.domain}
              </a>
            ))}
          </div>
        )}
      </section>

      {!!reasoning?.key_findings?.length && (
        <section className="content-card">
          <h3>Key Findings</h3>
          <div className="findings-grid">
            {reasoning.key_findings.map((finding) => (
              <div key={finding} className="finding-card">
                {finding}
              </div>
            ))}
          </div>
        </section>
      )}

      {!!result.followups?.length && (
        <section className="content-card">
          <div className="section-row">
            <h3>Explore Further</h3>
          </div>
          <div className="followups-grid">
            {result.followups.map((followup) => (
              <button key={followup} className="followup-btn" onClick={() => onResearch(followup)}>
                {followup}
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="content-card">
        <div className="section-row">
          <h3>Export Results</h3>
          <button className="secondary-btn" onClick={onExport}>
            Download PDF
          </button>
        </div>
      </section>
    </div>
  );
}

function SourcesTab({ result }) {
  const rows = result?.sources_table || [];

  if (!rows.length) {
    return <div className="empty-card">No sources were retrieved.</div>;
  }

  return (
    <div className="content-card table-card">
      <table>
        <thead>
          <tr>
            <th>Title</th>
            <th>Domain</th>
            <th>Scraped</th>
            <th>Snippet</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.url}>
              <td>
                <a href={row.url} target="_blank" rel="noreferrer">
                  {row.title || row.url}
                </a>
              </td>
              <td>{row.domain}</td>
              <td>{row.scraped ? "Yes" : "No"}</td>
              <td>{row.snippet}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReasoningTab({ result }) {
  const reasoning = result?.reasoning;
  const queryPlan = result?.query_plan;

  if (!reasoning && !queryPlan) {
    return <div className="empty-card">No reasoning trace available.</div>;
  }

  const flowStages = [
    {
      label: "Your Question",
      content: result.query,
    },
    {
      label: "Key Concepts Identified",
      content: queryPlan?.keywords?.length ? queryPlan.keywords.join(" | ") : "Topic and intent identified",
    },
    {
      label: "Source Insights Extracted",
      content: result.stats?.successful_scrapes
        ? `Insights extracted from ${result.stats.successful_scrapes} sources`
        : `Reviewed ${result.stats?.source_count || 0} sources`,
    },
    {
      label: "Cross-Validation",
      content: reasoning ? `${Math.round((reasoning.confidence || 0) * 100)}% confidence across sources` : "Cross-checked for consistency",
    },
    {
      label: "Final Answer Synthesized",
      content: reasoning?.reasoning_summary || "Final answer composed",
    },
  ];

  return (
    <div className="tab-stack">
      <section className="content-card">
        <h3>How this answer was derived</h3>
        <div className="flow-list">
          {flowStages.map((stage) => (
            <div key={stage.label} className="flow-item">
              <strong>{stage.label}</strong>
              <span>{stage.content}</span>
            </div>
          ))}
        </div>
      </section>

      {!!reasoning?.steps?.length && (
        <section className="content-card">
          <h3>Detailed Reasoning</h3>
          <div className="reasoning-list">
            {reasoning.steps.map((step) => (
              <div key={step.step_number} className="reasoning-item">
                <div className="reasoning-num">{step.step_number}</div>
                <div>
                  <strong>{step.action}</strong>
                  <p>{step.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function GraphTab({ result }) {
  const graph = result?.graph;

  if (!graph?.stats?.nodes) {
    return <div className="empty-card">Knowledge graph is empty.</div>;
  }

  return (
    <div className="tab-stack">
      <section className="content-card">
        <div className="section-row">
          <h3>
            Knowledge Graph - {graph.stats.nodes} nodes - {graph.stats.edges} edges
          </h3>
        </div>
        <iframe
          className="graph-frame"
          srcDoc={graph.html}
          title="Knowledge Graph"
          sandbox="allow-scripts"
        />
      </section>

      {!!graph.stats.top_domains?.length && (
        <section className="content-card">
          <h3>Top Domains in Graph</h3>
          <div className="domains-chart">
            {graph.stats.top_domains.map((entry) => (
              <div key={entry.domain} className="domain-row">
                <span>{entry.domain}</span>
                <div className="domain-bar-shell">
                  <div className="domain-bar" style={{ width: `${Math.min(entry.count * 10, 100)}%` }} />
                </div>
                <strong>{entry.count}</strong>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [config, setConfig] = useState({ suggestions: [], agent_stages: [] });
  const [result, setResult] = useState(null);
  const [researching, setResearching] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState(DEFAULT_TABS[0]);
  const [activeStage, setActiveStage] = useState(null);
  const [stageHistory, setStageHistory] = useState([]);

  useEffect(() => {
    fetchConfig()
      .then(setConfig)
      .catch((err) => setError(err.message));
  }, []);

  const stats = useMemo(() => result?.stats || null, [result]);

  async function handleResearch(nextQuery = query) {
    if (!nextQuery.trim() || researching) {
      return;
    }

    setQuery(nextQuery);
    setError("");
    setResult(null);
    setResearching(true);
    setActiveStage(config.agent_stages[0] || null);
    setStageHistory([]);
    setActiveTab(DEFAULT_TABS[0]);

    try {
      await streamResearch(nextQuery, {
        onStage: (payload) => {
          if (payload.stage) {
            setActiveStage(payload.stage);
          }
          setStageHistory((current) => [...current, payload]);
        },
        onComplete: (payload) => {
          setResult(payload);
          if (!payload.success) {
            setError(payload.error || "Research failed");
          }
          setActiveStage(null);
        },
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setResearching(false);
    }
  }

  async function handleExport() {
    if (!result?.final_answer) {
      return;
    }

    const blob = await exportPdf({
      query: result.query,
      answer: result.final_answer.answer,
      sources: result.sources_table.slice(0, 15),
      reasoning_steps: result.step_log,
      confidence: result.final_answer.confidence,
      timestamp: new Date().toISOString(),
    });

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `DoraEngine_${result.query.slice(0, 30).replace(/\s+/g, "_")}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const tabContent = {
    answer: <AnswerTab result={result} onResearch={handleResearch} onExport={handleExport} />,
    sources: <SourcesTab result={result} />,
    reasoning: <ReasoningTab result={result} />,
    graph: <GraphTab result={result} />,
  };

  return (
    <div className="app-shell">
      <div className="app-bg app-bg-one" />
      <div className="app-bg app-bg-two" />

      <main className="page">
        <section className="hero">
          <div className="hero-badge">DoraEngine</div>
          <h1>Autonomous AI Research Agent</h1>
          <p>Graph RAG - Multi-step reasoning - Source-backed answers</p>
        </section>

        <section className="search-panel">
          <div className="search-input-shell">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask anything... I'll research, verify, and explain it for you"
              disabled={researching}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  handleResearch();
                }
              }}
            />
          </div>
          <button className="primary-btn" onClick={() => handleResearch()} disabled={researching}>
            {researching ? "Researching..." : "Research This"}
          </button>
          {!result && !researching && (
            <div className="suggestions">
              {config.suggestions.map((suggestion) => (
                <button key={suggestion} className="chip" onClick={() => handleResearch(suggestion)}>
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </section>

        <ProgressPanel activeStage={activeStage} stageHistory={stageHistory} researching={researching} />

        {error && <div className="error-card">{error}</div>}

        {stats && (
          <section className="stats-row">
            <StatPill label="Research time" value={`${stats.total_time_seconds}s`} />
            <StatPill label="Sources" value={stats.display_source_count} />
            <StatPill label="Confidence" value={`${stats.confidence_percent}%`} />
          </section>
        )}

        {result && result.success && (
          <>
            <section className="tabs-shell">
              {DEFAULT_TABS.map((tab) => (
                <button
                  key={tab}
                  className={`tab-btn ${activeTab === tab ? "active" : ""}`}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab}
                </button>
              ))}
            </section>
            {tabContent[activeTab]}
          </>
        )}
      </main>
    </div>
  );
}
