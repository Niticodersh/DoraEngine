import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  exportDocument,
  fetchConfig,
  fetchHistory,
  fetchMe,
  fetchPlans,
  login,
  signup,
  streamResearch,
  updatePlan,
  updateProfile,
} from "./api";

const STORAGE_KEY = "doraengine_auth_token";
const RESEARCH_TABS = ["answer", "sources", "reasoning", "graph"];
const APP_PAGES = ["research", "history", "plans", "profile"];

function MarkdownAnswer({ text }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]}>{text || ""}</ReactMarkdown>;
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
          <div key={`${item.agent}-${item.action}-${item.stage?.progress || 0}`} className="status-row">
            <span className="status-dot" />
            <span className="status-agent">{item.agent}</span>
            <span className="status-text">{item.stage?.label || item.action}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function AuthView({ mode, onModeChange, onSubmit, loading, error }) {
  const [form, setForm] = useState({ email: "", password: "", mobile: "" });

  return (
    <div className="auth-shell">
      <section className="auth-card">
        <div className="hero-badge">DoraEngine</div>
        <h1>{mode === "login" ? "Sign in" : "Create account"}</h1>
        <p>{mode === "login" ? "Continue your saved research workspace." : "Mobile number is mandatory and unique for every account."}</p>

        <div className="auth-toggle">
          <button className={mode === "login" ? "tab-btn active" : "tab-btn"} onClick={() => onModeChange("login")}>
            Login
          </button>
          <button className={mode === "signup" ? "tab-btn active" : "tab-btn"} onClick={() => onModeChange("signup")}>
            Sign up
          </button>
        </div>

        <div className="form-grid">
          <label>
            Email
            <input
              value={form.email}
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              placeholder="you@example.com"
            />
          </label>
          {mode === "signup" && (
            <label>
              Mobile number
              <input
                value={form.mobile}
                onChange={(event) => setForm((current) => ({ ...current, mobile: event.target.value }))}
                placeholder="+91..."
              />
            </label>
          )}
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              placeholder="Minimum 8 characters"
            />
          </label>
        </div>

        {error && <div className="error-card compact">{error}</div>}

        <button
          className="primary-btn"
          disabled={loading}
          onClick={() => onSubmit(form)}
        >
          {loading ? "Please wait..." : mode === "login" ? "Login" : "Create account"}
        </button>
      </section>
    </div>
  );
}

function AnswerTab({ result, onResearch, onExportPdf, onExportDocx }) {
  const answer = result?.final_answer;
  const reasoning = result?.reasoning;

  if (!answer) {
    return <div className="empty-card">No answer generated yet.</div>;
  }

  return (
    <div className="tab-stack">
      <section className="content-card">
        <div className="confidence-badge">Confidence {Math.round((answer.confidence || 0) * 100)}%</div>
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
          <h3>Explore Further</h3>
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
          <h3>Export</h3>
          <div className="button-row">
            <button className="secondary-btn" onClick={onExportPdf}>Download PDF</button>
            <button className="secondary-btn" onClick={onExportDocx}>Download Word</button>
          </div>
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
              <td><a href={row.url} target="_blank" rel="noreferrer">{row.title || row.url}</a></td>
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
    { label: "Your Question", content: result.query },
    { label: "Key Concepts Identified", content: queryPlan?.keywords?.length ? queryPlan.keywords.join(" | ") : "Topic and intent identified" },
    { label: "Source Insights Extracted", content: result.stats?.successful_scrapes ? `Insights extracted from ${result.stats.successful_scrapes} sources` : `Reviewed ${result.stats?.source_count || 0} sources` },
    { label: "Cross-Validation", content: reasoning ? `${Math.round((reasoning.confidence || 0) * 100)}% confidence across sources` : "Cross-checked for consistency" },
    { label: "Final Answer Synthesized", content: reasoning?.reasoning_summary || "Final answer composed" },
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
        <h3>Knowledge Graph - {graph.stats.nodes} nodes - {graph.stats.edges} edges</h3>
        <iframe className="graph-frame" srcDoc={graph.html} title="Knowledge Graph" sandbox="allow-scripts" />
      </section>
    </div>
  );
}

function ResearchPage({
  user,
  config,
  token,
  result,
  setResult,
  researching,
  setResearching,
  error,
  setError,
  activeStage,
  setActiveStage,
  stageHistory,
  setStageHistory,
}) {
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState(RESEARCH_TABS[0]);
  const stats = useMemo(() => result?.stats || null, [result]);

  const requiresApiKey = user?.plan_code === "free" && !user?.has_groq_api_key;

  async function handleResearch(nextQuery = query) {
    if (!nextQuery.trim() || researching || requiresApiKey) {
      return;
    }

    setQuery(nextQuery);
    setError("");
    setResult(null);
    setResearching(true);
    setActiveStage(config.agent_stages[0] || null);
    setStageHistory([]);
    setActiveTab(RESEARCH_TABS[0]);

    try {
      await streamResearch(token, nextQuery, {
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

  async function handleExport(type) {
    if (!result?.final_answer) {
      return;
    }

    const blob = await exportDocument(token, type, {
      query: result.query,
      answer: result.final_answer.answer,
      sources: result.sources_table.slice(0, 15),
      confidence: result.final_answer.confidence,
      timestamp: new Date().toISOString(),
    });

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `DoraEngine_${result.query.slice(0, 30).replace(/\s+/g, "_")}.${type === "pdf" ? "pdf" : "docx"}`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const tabContent = {
    answer: <AnswerTab result={result} onResearch={handleResearch} onExportPdf={() => handleExport("pdf")} onExportDocx={() => handleExport("docx")} />,
    sources: <SourcesTab result={result} />,
    reasoning: <ReasoningTab result={result} />,
    graph: <GraphTab result={result} />,
  };

  return (
    <>
      {requiresApiKey && (
        <div className="warning-card">
          Free plan requires adding your GROQ API key in Profile before you can run research.
        </div>
      )}

      <section className="search-panel">
        <div className="search-input-shell">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ask anything... I'll research, verify, and explain it for you"
            disabled={researching || requiresApiKey}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleResearch();
              }
            }}
          />
        </div>
        <button className="primary-btn" onClick={() => handleResearch()} disabled={researching || requiresApiKey}>
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
            {RESEARCH_TABS.map((tab) => (
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
    </>
  );
}

function HistoryPage({ items, onOpen }) {
  return (
    <section className="content-card">
      <div className="section-row">
        <h3>Saved research history</h3>
      </div>
      {!items.length && <div className="empty-inline">No saved history yet.</div>}
      <div className="history-list">
        {items.map((item) => (
          <button key={item.id} className="history-item" onClick={() => onOpen(item.result)}>
            <strong>{item.query}</strong>
            <span>{item.answer_summary || "No summary available"}</span>
            <small>{item.created_at ? new Date(item.created_at).toLocaleString() : ""}</small>
          </button>
        ))}
      </div>
    </section>
  );
}

function PlansPage({ plans, user, onSelect }) {
  return (
    <section className="plans-grid">
      {plans.map((plan) => (
        <div key={plan.code} className={`content-card plan-card ${user?.plan_code === plan.code ? "plan-card-active" : ""}`}>
          <h3>{plan.name}</h3>
          <div className="plan-price">{plan.price_inr === 0 ? "Free" : `Rs ${plan.price_inr}`}</div>
          <p>{plan.billing === "forever" ? "Use your own API key and export with watermark." : `Billed per ${plan.billing}. Platform API key supported.`}</p>
          <button className="secondary-btn" onClick={() => onSelect(plan.code)}>
            {user?.plan_code === plan.code ? "Current plan" : "Choose plan"}
          </button>
        </div>
      ))}
    </section>
  );
}

function ProfilePage({ user, onSave }) {
  const [groqApiKey, setGroqApiKey] = useState("");
  const [tavilyApiKey, setTavilyApiKey] = useState("");

  return (
    <section className="content-card">
      <h3>Profile</h3>
      <div className="profile-grid">
        <div><strong>Email</strong><span>{user?.email}</span></div>
        <div><strong>Mobile</strong><span>{user?.mobile}</span></div>
        <div><strong>Plan</strong><span>{user?.plan_code}</span></div>
      </div>
      <div className="form-grid">
        <label>
          GROQ API key
          <input value={groqApiKey} onChange={(event) => setGroqApiKey(event.target.value)} placeholder={user?.has_groq_api_key ? "Stored - enter to replace" : "Paste your GROQ API key"} />
        </label>
        <label>
          Tavily API key
          <input value={tavilyApiKey} onChange={(event) => setTavilyApiKey(event.target.value)} placeholder={user?.has_tavily_api_key ? "Stored - enter to replace" : "Optional"} />
        </label>
      </div>
      <button className="primary-btn slim" onClick={() => onSave({ groq_api_key: groqApiKey, tavily_api_key: tavilyApiKey })}>
        Save profile keys
      </button>
    </section>
  );
}

export default function RootApp() {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY) || "");
  const [authMode, setAuthMode] = useState("login");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [user, setUser] = useState(null);
  const [config, setConfig] = useState({ suggestions: [], agent_stages: [] });
  const [plans, setPlans] = useState([]);
  const [historyItems, setHistoryItems] = useState([]);
  const [page, setPage] = useState(APP_PAGES[0]);
  const [result, setResult] = useState(null);
  const [researching, setResearching] = useState(false);
  const [error, setError] = useState("");
  const [activeStage, setActiveStage] = useState(null);
  const [stageHistory, setStageHistory] = useState([]);

  useEffect(() => {
    fetchConfig().then(setConfig).catch((err) => setError(err.message));
    fetchPlans().then((payload) => setPlans(payload.plans || [])).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }
    fetchMe(token)
      .then((payload) => setUser(payload.user))
      .catch(() => {
        localStorage.removeItem(STORAGE_KEY);
        setToken("");
        setUser(null);
      });
  }, [token]);

  useEffect(() => {
    if (!token) {
      setHistoryItems([]);
      return;
    }
    fetchHistory(token)
      .then((payload) => setHistoryItems(payload.items || []))
      .catch(() => {});
  }, [token, result]);

  async function handleAuthSubmit(form) {
    setAuthLoading(true);
    setAuthError("");
    try {
      const payload = authMode === "login"
        ? await login({ email: form.email, password: form.password })
        : await signup({ email: form.email, password: form.password, mobile: form.mobile });
      localStorage.setItem(STORAGE_KEY, payload.token);
      setToken(payload.token);
      setUser(payload.user);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleProfileSave(payload) {
    try {
      const response = await updateProfile(token, payload);
      setUser(response.user);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handlePlanSelect(planCode) {
    try {
      const response = await updatePlan(token, { plan_code: planCode });
      setUser(response.user);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  function openHistoryResult(savedResult) {
    setPage("research");
    setResult(savedResult);
    setError("");
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY);
    setToken("");
    setUser(null);
    setResult(null);
    setHistoryItems([]);
  }

  if (!token || !user) {
    return <AuthView mode={authMode} onModeChange={setAuthMode} onSubmit={handleAuthSubmit} loading={authLoading} error={authError} />;
  }

  return (
    <div className="app-shell">
      <div className="app-bg app-bg-one" />
      <div className="app-bg app-bg-two" />

      <main className="page">
        <section className="hero hero-compact">
          <div className="hero-badge">DoraEngine</div>
          <h1>Autonomous AI Research Agent</h1>
          <p>Graph RAG - Multi-step reasoning - Source-backed answers</p>
        </section>

        <section className="topbar">
          <div className="nav-row">
            {APP_PAGES.map((entry) => (
              <button
                key={entry}
                className={`tab-btn ${page === entry ? "active" : ""}`}
                onClick={() => setPage(entry)}
              >
                {entry}
              </button>
            ))}
          </div>
          <div className="user-meta">
            <span>{user.email}</span>
            <span className="plan-chip">{user.plan_code}</span>
            <button className="secondary-btn" onClick={logout}>Logout</button>
          </div>
        </section>

        {error && <div className="error-card">{error}</div>}

        {page === "research" && (
          <ResearchPage
            user={user}
            config={config}
            token={token}
            result={result}
            setResult={setResult}
            researching={researching}
            setResearching={setResearching}
            error={error}
            setError={setError}
            activeStage={activeStage}
            setActiveStage={setActiveStage}
            stageHistory={stageHistory}
            setStageHistory={setStageHistory}
          />
        )}

        {page === "history" && <HistoryPage items={historyItems} onOpen={openHistoryResult} />}
        {page === "plans" && <PlansPage plans={plans} user={user} onSelect={handlePlanSelect} />}
        {page === "profile" && <ProfilePage user={user} onSave={handleProfileSave} />}
      </main>
    </div>
  );
}
