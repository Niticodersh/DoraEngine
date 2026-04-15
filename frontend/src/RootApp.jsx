/**
 * DoraEngine — Root Application
 * 
 * MVP changes:
 *  - Chat history removed from all plans (commented out, re-enable later)
 *  - Tavily API key removed from user-facing UI (backend-only)
 *  - OTP verification added before onboarding
 *  - Research playground centered
 */

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  exportDocument,
  fetchConfig,
  fetchMe,
  fetchPlans,
  forgotPassword,
  login,
  resetPassword,
  sendOtp,
  signup,
  streamResearch,
  updatePlan,
  updateProfile,
  createPaymentOrder,
  verifyPaymentSignature,
  verifySignupOtp,
} from "./api";


/* ─────────────────────────────────────────────────────────────────────────────
   CONSTANTS
   ───────────────────────────────────────────────────────────────────────────── */

const STORAGE_KEY = "doraengine_auth_token";

const RESEARCH_TABS = [
  { id: "answer",    label: "Answer",    icon: "✦" },
  { id: "sources",   label: "Sources",   icon: "⊞" },
  { id: "reasoning", label: "Reasoning", icon: "⊙" },
  { id: "graph",     label: "Graph",     icon: "⬡" },
];

const PAID_PLANS = ["standard_daily", "standard_monthly"];
const isPaidPlan = (code) => PAID_PLANS.includes(code);

/* ─────────────────────────────────────────────────────────────────────────────
   CUSTOM HOOK — Typing animation
   ───────────────────────────────────────────────────────────────────────────── */

function useTypingAnimation(phrases, { typeSpeed = 45, deleteSpeed = 22, pauseMs = 2200 } = {}) {
  const [text, setText] = useState("");
  const [phraseIdx, setPhraseIdx] = useState(0);
  const [deleting, setDeleting] = useState(false);
  const timeoutRef = useRef(null);

  useEffect(() => {
    const current = phrases[phraseIdx];
    const tick = () => {
      if (!deleting) {
        if (text.length < current.length) {
          setText(current.slice(0, text.length + 1));
          timeoutRef.current = setTimeout(tick, typeSpeed);
        } else {
          timeoutRef.current = setTimeout(() => setDeleting(true), pauseMs);
        }
      } else {
        if (text.length > 0) {
          setText(text.slice(0, -1));
          timeoutRef.current = setTimeout(tick, deleteSpeed);
        } else {
          setDeleting(false);
          setPhraseIdx((i) => (i + 1) % phrases.length);
        }
      }
    };
    timeoutRef.current = setTimeout(tick, deleting ? deleteSpeed : typeSpeed);
    return () => clearTimeout(timeoutRef.current);
  }, [text, deleting, phraseIdx, phrases, typeSpeed, deleteSpeed, pauseMs]);

  return text;
}

/* ─────────────────────────────────────────────────────────────────────────────
   INLINE SVG ICONS
   ───────────────────────────────────────────────────────────────────────────── */

const Icons = {
  ArrowLeft: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m15 18-6-6 6-6" />
    </svg>
  ),
  ExternalLink: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  ),
  Search: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
    </svg>
  ),
  Send: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" />
    </svg>
  ),
  Brain: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.46 2.5 2.5 0 0 1-1.96-3.2A3 3 0 0 1 4 11a3 3 0 0 1 2-2.83V8A2.5 2.5 0 0 1 9.5 2Z" />
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.46 2.5 2.5 0 0 0 1.96-3.2A3 3 0 0 0 20 11a3 3 0 0 0-2-2.83V8A2.5 2.5 0 0 0 14.5 2Z" />
    </svg>
  ),
  Network: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="5" r="2" /><circle cx="5" cy="19" r="2" /><circle cx="19" cy="19" r="2" />
      <path d="M12 7v3" /><path d="m7 17-1.5-5.5" /><path d="m17 17 1.5-5.5" />
      <path d="M10.5 13.5 7 17" /><path d="m13.5 13.5 3.5 3.5" />
    </svg>
  ),
  Shield: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  FileDown: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
      <path d="M14 2v4a2 2 0 0 0 2 2h4" /><path d="M12 18v-6" /><path d="m9 15 3 3 3-3" />
    </svg>
  ),
  User: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  ),
  LogOut: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  ),
  Zap: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  ),
  Check: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  X: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
  Key: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4" />
    </svg>
  ),
  CreditCard: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect width="22" height="16" x="1" y="4" rx="2" /><line x1="1" y1="10" x2="23" y2="10" />
    </svg>
  ),
  Lock: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  ),
  Info: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" />
    </svg>
  ),
  Warning: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <path d="M12 9v4" /><path d="M12 17h.01" />
    </svg>
  ),
  Layers: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z" />
      <path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65" />
      <path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65" />
    </svg>
  ),
  Phone: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.4 2 2 0 0 1 3.6 1.22h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L7.91 9A16 16 0 0 0 15 16.09l1.14-1.14a2 2 0 0 1 2.11-.45c.898.36 1.836.574 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  ),
  Mail: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="16" x="2" y="4" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  ),
  LinkedIn: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
      <rect width="4" height="12" x="2" y="9" /><circle cx="4" cy="4" r="2" />
    </svg>
  ),
  Plan: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z" />
      <path d="M7 7h.01" />
    </svg>
  ),
  Smartphone: () => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect width="14" height="20" x="5" y="2" rx="2" ry="2" />
      <path d="M12 18h.01" />
    </svg>
  ),
};

/* ─────────────────────────────────────────────────────────────────────────────
   LANDING PAGE
   ───────────────────────────────────────────────────────────────────────────── */

function LandingPage({ onLogin, onSignUp }) {
  const typingText = useTypingAnimation([
    "Research. Reason. Deliver.",
    "Graph RAG + multi-step reasoning.",
    "Source-backed answers, always.",
    "Your autonomous AI research agent.",
  ]);

  const features = [
    { icon: <Icons.Network />, name: "Knowledge Graph RAG", desc: "Builds a dynamic knowledge graph from scraped sources, enabling deep cross-source reasoning and semantic connections." },
    { icon: <Icons.Brain />,   name: "Multi-step Reasoning", desc: "Plans research queries, validates findings, and synthesizes evidence across multiple iterations before answering." },
    { icon: <Icons.Shield />,  name: "Source-backed Answers", desc: "Every claim is traceable. Full citation list, confidence score, and domain breakdown included with every answer." },
    { icon: <Icons.FileDown />, name: "Export Ready", desc: "Download research results as polished PDF or Word documents. Paid plans export without watermarks." },
  ];

  const steps = [
    { num: "01", title: "Ask your question", desc: "Type any research question — technical, analytical, or exploratory." },
    { num: "02", title: "DoraEngine reasons", desc: "The agent plans, searches, scrapes, and builds a knowledge graph in real time." },
    { num: "03", title: "Get your answer", desc: "Receive a structured, cited, confidence-scored answer ready to export." },
  ];

  const contactItems = [
    { icon: <Icons.Phone />, label: "Phone", value: "+91-8287040699", href: "tel:+918287040699" },
    { icon: <Icons.Mail />,  label: "Email", value: "nitishbhardwaj471@gmail.com", href: "mailto:nitishbhardwaj471@gmail.com" },
    { icon: <Icons.LinkedIn />, label: "LinkedIn", value: "nitish-bhardwaj-973a57228", href: "https://www.linkedin.com/in/nitish-bhardwaj-973a57228/" },
  ];

  return (
    <div className="landing-root">
      <nav className="landing-nav">
        <div className="nav-logo">
          <div className="nav-logo-mark">D</div>
          DoraEngine
        </div>
        <div className="nav-actions">
          <button className="btn btn-ghost" onClick={onLogin} id="nav-signin">Sign In</button>
          <button className="btn btn-primary" onClick={onSignUp} id="nav-signup">Get Started</button>
        </div>
      </nav>

      <section className="landing-hero" id="hero">
        <div className="hero-eyebrow">
          <div className="hero-eyebrow-dot" />
          Autonomous AI Research Agent
        </div>
        <h1 className="hero-title">DoraEngine</h1>
        <p className="hero-typing-line">
          <span className="hero-typing-text">{typingText}</span>
          <span className="hero-cursor" aria-hidden="true" />
        </p>
        <p className="hero-subtitle">
          Ask complex questions and receive source-backed, evidence-grade answers — powered by Knowledge Graph RAG and autonomous multi-step reasoning.
        </p>
        <div className="hero-cta-row">
          <button className="btn btn-primary btn-primary-lg" onClick={onSignUp} id="hero-signup">
            <Icons.Zap /> Start Researching Free
          </button>
          <button className="btn btn-ghost btn-ghost-lg" onClick={onLogin} id="hero-signin">
            Sign in to workspace
          </button>
        </div>
        <p className="hero-scroll-hint">↓ scroll to learn more</p>
      </section>

      <div className="landing-section" id="features">
        <div className="section-header">
          <span className="section-label">Capabilities</span>
          <h2 className="section-title">Built for serious research</h2>
          <p className="section-subtitle">DoraEngine isn't a simple Q&A tool. It's an agent that plans, reasons, and delivers.</p>
        </div>
        <div className="features-grid">
          {features.map((f) => (
            <div key={f.name} className="feature-card">
              <div className="feature-icon">{f.icon}</div>
              <div className="feature-name">{f.name}</div>
              <p className="feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="how-it-works-bg" id="how-it-works">
        <div className="landing-section">
          <div className="section-header">
            <span className="section-label">Workflow</span>
            <h2 className="section-title">How it works</h2>
            <p className="section-subtitle">From question to cited answer in minutes.</p>
          </div>
          <div className="steps-row">
            {steps.map((s) => (
              <div key={s.num} className="step-item">
                <div className="step-num">{s.num}</div>
                <div className="step-title">{s.title}</div>
                <p className="step-desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="contact-section" id="contact">
        <div className="landing-section">
          <div className="contact-card">
            <div>
              <div className="contact-label">Get in touch</div>
              <h2 className="contact-title">Have questions?</h2>
              <p className="contact-subtitle">
                Built and maintained by a solo developer. Reach out directly — happy to discuss research use cases, custom plans, or technical questions.
              </p>
            </div>
            <div className="contact-items">
              {contactItems.map((item) => (
                <a key={item.label} href={item.href} className="contact-item" target={item.href.startsWith("http") ? "_blank" : undefined} rel="noreferrer">
                  <div className="contact-item-icon">{item.icon}</div>
                  <div className="contact-item-text">
                    <span className="contact-item-label">{item.label}</span>
                    <span className="contact-item-value">{item.value}</span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>

      <footer>
        <div className="landing-footer">
          <span>© {new Date().getFullYear()} DoraEngine. All rights reserved.</span>
          <div className="nav-actions">
            <button className="btn btn-ghost btn-sm" onClick={onLogin}>Sign In</button>
            <button className="btn btn-primary btn-sm" onClick={onSignUp}>Get Started</button>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   AUTH PAGE
   ───────────────────────────────────────────────────────────────────────────── */

function AuthPage({ defaultMode = "login", onBack, onSuccess, onForgotPassword, notice = "" }) {
  const [mode, setMode] = useState(defaultMode); // "login", "signup", "signup_verify"
  const [form, setForm] = useState({ email: "", password: "", mobile: "", otp: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(notice || "");

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "login") {
        const payload = await login({ email: form.email, password: form.password });
        onSuccess(payload, "login");
      } else if (mode === "signup") {
        if (form.password.length < 8) throw new Error("Password must be at least 8 characters.");
        const payload = await signup({
          email: form.email.trim().toLowerCase(),
          password: form.password,
          mobile: form.mobile.trim(),
        });
        if (payload.status === "needs_otp") {
          setMode("signup_verify");
        } else {
          // Fallback if somehow it skipped OTP
          onSuccess(payload, "signup");
        }
      } else if (mode === "signup_verify") {
        const payload = await verifySignupOtp({
          email: form.email.trim().toLowerCase(),
          otp_code: form.otp.trim(),
        });
        onSuccess(payload, "signup");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const capabilities = [
    "Graph RAG — knowledge graph from real sources",
    "Multi-step reasoning with full trace",
    "Source citations and confidence scores",
    "Export to PDF & Word",
  ];

  return (
    <div className="auth-page">
      <div className="auth-visual">
        <div className="auth-visual-logo" onClick={onBack}>DoraEngine</div>
        <div className="auth-visual-tagline">
          <strong>Research at the speed of thought.</strong>
          Autonomous AI agent that plans, reasons, and delivers evidence-backed answers.
        </div>
        <div className="auth-visual-pills">
          {capabilities.map((c) => (
            <div key={c} className="auth-visual-pill">
              <span className="auth-visual-pill-icon"><Icons.Check /></span>
              {c}
            </div>
          ))}
        </div>
      </div>

      <div className="auth-panel">
        <div className="auth-panel-inner">
          <button className="auth-back" onClick={onBack}>
            <Icons.ArrowLeft /> Back to homepage
          </button>

          <h1 className="auth-heading">
            {mode === "login" ? "Welcome back" 
             : mode === "signup_verify" ? "Verify your email" 
             : "Create your account"}
          </h1>
          <p className="auth-subheading">
            {mode === "login" ? "Sign in to your research workspace."
             : mode === "signup_verify" ? "We sent a 6-digit code to your email."
             : "Get started — it's free to use with your own GROQ key."}
          </p>

          {mode !== "signup_verify" && (
            <>
              <div className="auth-mode-toggle">
            <button className={`auth-mode-btn ${mode === "login" ? "active" : ""}`}
              onClick={() => { setMode("login"); setError(""); }} id="auth-tab-login">
              Sign In
            </button>
            <button className={`auth-mode-btn ${mode === "signup" ? "active" : ""}`}
              onClick={() => { setMode("signup"); setError(""); }} id="auth-tab-signup">
              Sign Up
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <div className="field">
                <label className="field-label" htmlFor="auth-email">Email address</label>
                <input id="auth-email" type="email" className="field-input"
                  value={form.email} onChange={update("email")}
                  placeholder="you@example.com" required autoComplete="email" />
              </div>

              {mode === "signup" && (
                <div className="field">
                  <label className="field-label" htmlFor="auth-mobile">Mobile number</label>
                  <input id="auth-mobile" type="tel" className="field-input"
                    value={form.mobile} onChange={update("mobile")}
                    placeholder="+91 XXXXX XXXXX" required autoComplete="tel" />
                  <span className="field-hint">For contact only. Include country code.</span>
                </div>
              )}

              <div className="field">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.3rem" }}>
                  <label className="field-label" htmlFor="auth-password" style={{ marginBottom: 0 }}>Password</label>
                  {mode === "login" && (
                    <button
                      type="button"
                      className="otp-resend-btn"
                      onClick={onForgotPassword}
                      id="forgot-password-link"
                      style={{ fontSize: "0.8rem" }}
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <input id="auth-password" type="password" className="field-input"
                  value={form.password} onChange={update("password")}
                  placeholder={mode === "signup" ? "Minimum 8 characters" : "Your password"}
                  required autoComplete={mode === "login" ? "current-password" : "new-password"} />
              </div>
            </div>

            {error && (
              <div className="auth-error" role="alert">
                <Icons.X /> {error}
              </div>
            )}

            <button type="submit" className="btn btn-primary btn-full"
              disabled={loading} id="auth-submit" style={{ marginTop: "0.25rem" }}>
              {loading
                ? <><div className="spinner" /> Please wait…</>
                : mode === "login" ? "Sign In →" : "Sign Up →"}
            </button>
          </form>
            </>
          )}

          {mode === "signup_verify" && (
          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label>6-Digit Code</label>
              <div className="input-with-icon">
                <span className="input-icon"><Icons.Key /></span>
                <input 
                  type="text" 
                  maxLength={6}
                  placeholder="Enter code" 
                  value={form.otp} 
                  onChange={update("otp")} 
                  required 
                  autoFocus
                />
              </div>
            </div>

            {error && (
              <div className="auth-error">
                <Icons.Warning />
                {error}
              </div>
            )}

            <button type="submit" className="btn btn-primary auth-submit" disabled={loading} id="auth-signup-verify-btn">
              {loading ? "Verifying..." : "Complete Sign Up"}
            </button>
            <div className="auth-footer" style={{ marginTop: "1rem" }}>
              <button type="button" className="text-secondary hover-white" onClick={() => setMode("signup")}>
                Try a different email
              </button>
            </div>
          </form>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   OTP VERIFICATION PAGE
   ───────────────────────────────────────────────────────────────────────────── */

function OtpVerifyPage({ user, token, devOtp, onVerified, onBack }) {
  const [digits, setDigits] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMsg, setResendMsg] = useState("");
  const [countdown, setCountdown] = useState(30);
  const [newDevOtp, setNewDevOtp] = useState(devOtp || "");
  const inputRefs = useRef([]);

  // Countdown timer for resend button
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  function handleDigit(index, value) {
    const v = value.replace(/\D/g, "").slice(-1);
    const next = [...digits];
    next[index] = v;
    setDigits(next);
    if (v && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  }

  function handleKeyDown(index, e) {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }

  function handlePaste(e) {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    const next = [...digits];
    for (let i = 0; i < 6; i++) next[i] = pasted[i] || "";
    setDigits(next);
    inputRefs.current[Math.min(pasted.length, 5)]?.focus();
  }

  async function handleVerify() {
    const code = digits.join("");
    if (code.length !== 6) { setError("Please enter the full 6-digit OTP."); return; }
    setLoading(true);
    setError("");
    try {
      const response = await verifyOtp(token, code);
      onVerified(response.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setResendLoading(true);
    setResendMsg("");
    setError("");
    try {
      const response = await sendOtp(token);
      setNewDevOtp(response.dev_otp || "");
      setResendMsg("OTP resent successfully.");
      setCountdown(30);
      setDigits(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } catch (err) {
      setError(err.message);
    } finally {
      setResendLoading(false);
    }
  }

  const maskedMobile = user?.mobile
    ? user.mobile.slice(0, -4).replace(/\d/g, "•") + user.mobile.slice(-4)
    : "your registered mobile";

  return (
    <div className="otp-page">
      <div className="otp-card">
        <div className="otp-icon">
          <Icons.Smartphone />
        </div>
        <h2 className="otp-title">Verify your mobile</h2>
        <p className="otp-subtitle">
          We've sent a 6-digit OTP to <strong>{maskedMobile}</strong>.<br />
          Enter it below to verify your account.
        </p>

        <div className="otp-digits" onPaste={handlePaste}>
          {digits.map((d, i) => (
            <input
              key={i}
              ref={(el) => (inputRefs.current[i] = el)}
              id={`otp-digit-${i}`}
              className={`otp-digit ${d ? "filled" : ""}`}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={d}
              onChange={(e) => handleDigit(i, e.target.value)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              autoFocus={i === 0}
              autoComplete="one-time-code"
            />
          ))}
        </div>

        {error && <div className="auth-error" role="alert"><Icons.X /> {error}</div>}
        {resendMsg && <div className="success-alert"><Icons.Check /> {resendMsg}</div>}

        <button
          className="btn btn-primary btn-full"
          onClick={handleVerify}
          disabled={loading || digits.join("").length !== 6}
          id="otp-verify-btn"
        >
          {loading ? <><div className="spinner" /> Verifying…</> : "Verify & Continue →"}
        </button>

        <div className="otp-resend-row">
          <span>Didn't receive it?</span>
          <button
            className="otp-resend-btn"
            onClick={handleResend}
            disabled={resendLoading || countdown > 0}
            id="otp-resend-btn"
          >
            {resendLoading ? "Sending…" : countdown > 0 ? `Resend in ${countdown}s` : "Resend OTP"}
          </button>
        </div>

        {/* Dev-mode hint: shows the actual OTP for testing when no SMS is connected */}
        {(newDevOtp || devOtp) && (
          <div className="otp-dev-hint">
            <Icons.Warning />
            <div>
              <strong>Development mode:</strong> OTP delivery via SMS/email is not yet configured.
              Your OTP is: <strong style={{ fontFamily: "monospace", letterSpacing: "0.1em" }}>{newDevOtp || devOtp}</strong>
              <div style={{ marginTop: "0.25rem", opacity: 0.75 }}>Remove <code>dev_otp</code> from the API response in production.</div>
            </div>
          </div>
        )}

        <button className="btn btn-ghost" style={{ marginTop: "1rem", width: "100%" }} onClick={onBack}>
          <Icons.ArrowLeft /> Back to sign in
        </button>
      </div>
    </div>
  );
}


/* ─────────────────────────────────────────────────────────────────────────────
   FORGOT PASSWORD PAGE
   ───────────────────────────────────────────────────────────────────────────── */

function ForgotPasswordPage({ onBack }) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await forgotPassword(email.trim().toLowerCase());
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <div className="otp-page">
        <div className="otp-card">
          <div className="otp-icon"><Icons.Mail /></div>
          <h2 className="otp-title">Check your email</h2>
          <p className="otp-subtitle">
            If an account exists for <strong>{email}</strong>, a password reset link has been sent.
            Check your inbox (and spam folder).
          </p>
          <button className="btn btn-ghost" style={{ marginTop: "1.5rem", width: "100%" }} onClick={onBack}>
            <Icons.ArrowLeft /> Back to sign in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="otp-page">
      <div className="otp-card">
        <div className="otp-icon"><Icons.Lock /></div>
        <h2 className="otp-title">Reset your password</h2>
        <p className="otp-subtitle">
          Enter your account email and we'll send you a link to reset your password.
        </p>
        <form onSubmit={handleSubmit} style={{ marginTop: "1.5rem" }}>
          <div className="field" style={{ marginBottom: "1rem" }}>
            <label className="field-label" htmlFor="forgot-email">Email address</label>
            <input id="forgot-email" type="email" className="field-input"
              value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com" required autoComplete="email" />
          </div>
          {error && <div className="auth-error" role="alert"><Icons.X /> {error}</div>}
          <button type="submit" className="btn btn-primary btn-full" disabled={loading} id="forgot-submit">
            {loading ? <><div className="spinner" /> Sending…</> : "Send reset link →"}
          </button>
        </form>
        <button className="btn btn-ghost" style={{ marginTop: "0.75rem", width: "100%" }} onClick={onBack}>
          <Icons.ArrowLeft /> Back to sign in
        </button>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   RESET PASSWORD PAGE
   ───────────────────────────────────────────────────────────────────────────── */

function ResetPasswordPage({ email, token, onSuccess }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (password !== confirm) { setError("Passwords do not match."); return; }
    setLoading(true);
    setError("");
    try {
      await resetPassword(email, token, password);
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <div className="otp-page">
        <div className="otp-card">
          <div className="otp-icon" style={{ background: "rgba(52,211,153,0.12)", color: "var(--emerald-400)" }}>
            <Icons.Check />
          </div>
          <h2 className="otp-title">Password updated!</h2>
          <p className="otp-subtitle">Your password has been reset successfully. You can now sign in with your new password.</p>
          <button className="btn btn-primary btn-full" style={{ marginTop: "1.5rem" }} onClick={onSuccess}>
            Go to Sign In →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="otp-page">
      <div className="otp-card">
        <div className="otp-icon"><Icons.Key /></div>
        <h2 className="otp-title">Set new password</h2>
        <p className="otp-subtitle">
          Choose a strong new password for <strong>{email}</strong>.
        </p>
        <form onSubmit={handleSubmit} style={{ marginTop: "1.5rem" }}>
          <div className="field" style={{ marginBottom: "0.875rem" }}>
            <label className="field-label" htmlFor="reset-password">New password</label>
            <input id="reset-password" type="password" className="field-input"
              value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters" required autoComplete="new-password" />
          </div>
          <div className="field" style={{ marginBottom: "1rem" }}>
            <label className="field-label" htmlFor="reset-confirm">Confirm password</label>
            <input id="reset-confirm" type="password" className="field-input"
              value={confirm} onChange={(e) => setConfirm(e.target.value)}
              placeholder="Re-enter new password" required autoComplete="new-password" />
          </div>
          {error && <div className="auth-error" role="alert"><Icons.X /> {error}</div>}
          <button type="submit" className="btn btn-primary btn-full" disabled={loading} id="reset-submit">
            {loading ? <><div className="spinner" /> Updating…</> : "Update password →"}
          </button>
        </form>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   PLAN SELECTION PAGE
   ───────────────────────────────────────────────────────────────────────────── */

function PlanSelectionPage({ plans, user, currentPlanCode, onSelect, onSkip, isChanging = false }) {
  const [selecting, setSelecting] = useState(null);

  const hasActivePaidPlan = user && user.plan_code && user.plan_code !== "free";
  const formattedExpiry = user?.plan_expiry_date ? new Date(user.plan_expiry_date).toLocaleString(undefined, {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  }) : "it expires";

  async function handleSelect(planCode) {
    setSelecting(planCode);
    await onSelect(planCode);
    setSelecting(null);
  }

  const getPlanFeatures = (plan) => {
    if (plan.code === "free") {
      return {
        included: [
          "Use your own GROQ API key",
          "Unlimited research questions",
          "Graph RAG + multi-step reasoning",
          "PDF & Word export (watermarked)",
          "Knowledge graph visualization",
        ],
        excluded: ["Platform-managed API key", "Watermark-free exports"],
      };
    }
    if (plan.code === "standard_daily") {
      return {
        included: [
          "Platform-managed GROQ API key",
          "Unlimited research questions",
          "Graph RAG + multi-step reasoning",
          "PDF & Word export (no watermark)",
          "Knowledge graph visualization",
        ],
        excluded: [],
      };
    }
    return {
      included: [
        "Platform-managed GROQ API key",
        "Unlimited research questions",
        "Graph RAG + multi-step reasoning",
        "PDF & Word export (no watermark)",
        "Knowledge graph visualization",
        "Best value — save vs. daily plan",
      ],
      excluded: [],
    };
  };

  return (
    <div className="onboarding-page">
      <div className="onboarding-header">
        {!isChanging && <div className="onboarding-step">Almost there!</div>}
        <h1 className="onboarding-title">
          {isChanging ? "Change your plan" : "Choose your plan"}
        </h1>
        <p className="onboarding-subtitle">
          {isChanging
            ? "Select a new plan. Paid plans require payment to activate."
            : "Start free with your own GROQ key, or unlock the full platform."}
        </p>
      </div>

      {hasActivePaidPlan && (
        <div className="auth-error" style={{ marginBottom: "1.5rem", maxWidth: "800px", margin: "0 auto 1.5rem auto", backgroundColor: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.2)", color: "var(--indigo-300)" }}>
          <div style={{ marginLeft: "0.5rem" }}>
            <span style={{ fontWeight: "600" }}>You currently have an active paid plan ({user?.plan_code === "standard_daily" ? "Daily" : "Monthly"}).</span><br/>
            You can select another plan after {formattedExpiry}.
          </div>
        </div>
      )}

      <div className="plans-onboarding-grid">
        {plans.map((plan) => {
          const { included, excluded } = getPlanFeatures(plan);
          const isMonthly = plan.code === "standard_monthly";
          const isCurrent = plan.code === currentPlanCode;

          return (
            <div key={plan.code}
              className={`plan-onboarding-card ${isMonthly ? "featured" : ""}`}
              style={{ opacity: hasActivePaidPlan && !isCurrent ? 0.6 : 1 }}
              onClick={() => !(isChanging && isCurrent) && !hasActivePaidPlan && handleSelect(plan.code)}
              role="button" tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && !(isChanging && isCurrent) && !hasActivePaidPlan && handleSelect(plan.code)}>
              {isMonthly && <div className="plan-badge-recommended">Best Value</div>}
              <div>
                <div className="plan-name">{plan.name}</div>
                <div className="plan-price-row">
                  <span className="plan-price-amount">
                    {plan.price_inr === 0 ? "₹0" : `₹${plan.price_inr}`}
                  </span>
                  <span className="plan-price-period">
                    {plan.billing === "forever" ? "/forever" : `/${plan.billing}`}
                  </span>
                </div>
              </div>
              <ul className="plan-features-list">
                {included.map((f) => (
                  <li key={f} className="plan-feature-item">
                    <span className="plan-feature-check"><Icons.Check /></span>{f}
                  </li>
                ))}
                {excluded.map((f) => (
                  <li key={f} className="plan-feature-item" style={{ opacity: 0.45 }}>
                    <span className="plan-feature-cross"><Icons.X /></span>{f}
                  </li>
                ))}
              </ul>
              <div className="plan-cta">
                <button
                  className={`btn btn-full ${isMonthly ? "btn-primary" : "btn-ghost"}`}
                  disabled={selecting !== null || (isChanging && isCurrent) || hasActivePaidPlan}
                  id={`plan-select-${plan.code}`}
                  onClick={(e) => { e.stopPropagation(); !(isChanging && isCurrent) && !hasActivePaidPlan && handleSelect(plan.code); }}>
                  {selecting === plan.code
                    ? <><div className="spinner" /> Processing…</>
                    : (isChanging && isCurrent) ? "Current plan"
                      : hasActivePaidPlan ? "Locked"
                      : plan.price_inr === 0 ? "Get started free" : `Choose ${plan.name}`}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {isChanging && (
        <button className="btn btn-ghost" style={{ marginTop: "1.5rem" }} onClick={onSkip}>Cancel</button>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   GROQ KEY SETUP PAGE
   ───────────────────────────────────────────────────────────────────────────── */

function GroqKeyPage({ onSave, onSkip, loading, error }) {
  const [key, setKey] = useState("");

  return (
    <div className="onboarding-page">
      <div className="groq-setup-card">
        <div className="groq-setup-icon"><Icons.Key /></div>
        <h2 className="groq-setup-title">Add your GROQ API key</h2>
        <p className="groq-setup-desc">
          The <strong>Free plan</strong> uses your own GROQ API key. Your key is stored securely and never shared.
        </p>

        <div className="groq-info-box">
          <span className="groq-info-box-icon"><Icons.Info /></span>
          <div>
            GROQ's free tier with LLaMA-3 is extremely fast and generous. Create your key at console.groq.com.
            <br />
            <a className="groq-cta-link" href="https://console.groq.com/keys" target="_blank" rel="noreferrer">
              Create your GROQ API key <Icons.ExternalLink />
            </a>
          </div>
        </div>

        <div className="field" style={{ marginBottom: "1.25rem" }}>
          <label className="field-label" htmlFor="groq-key-input">GROQ API Key</label>
          <input id="groq-key-input" type="password" className="field-input"
            value={key} onChange={(e) => setKey(e.target.value)}
            placeholder="gsk_..." autoComplete="off" />
          <span className="field-hint">Starts with <code>gsk_</code>. You can update this anytime from Profile.</span>
        </div>

        {error && <div className="auth-error" style={{ marginBottom: "1rem" }}><Icons.X /> {error}</div>}

        <button className="btn btn-primary btn-full"
          disabled={!key.trim() || loading} onClick={() => onSave(key.trim())} id="groq-save-btn">
          {loading ? <><div className="spinner" /> Saving…</> : "Save and start researching →"}
        </button>

        <button className="btn btn-ghost btn-full" style={{ marginTop: "0.75rem" }}
          onClick={onSkip} id="groq-skip-btn">
          Skip for now
        </button>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   RAZORPAY PAYMENT PAGE (Frontend UI — wire to backend when ready)
   ───────────────────────────────────────────────────────────────────────────── */

function PaymentPage({ plan, user, onPaymentDone, onBack, token }) {
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");

  const amount = plan?.price_inr || 0;
  const gst = Math.round(amount * 0.18);
  const total = amount + gst;

  useEffect(() => {
    // Dynamically load Razorpay SDK
    if (!document.getElementById("razorpay-sdk")) {
      const script = document.createElement("script");
      script.id = "razorpay-sdk";
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      document.body.appendChild(script);
    }
  }, []);

  async function handlePay() {
    setProcessing(true);
    setError("");
    try {
      if (!window.Razorpay) {
        throw new Error("Razorpay SDK failed to load. Please check your connection.");
      }

      // 1. Create order on backend
      const orderRes = await createPaymentOrder(token, { plan_code: plan.code });

      // 2. Setup Razorpay widget options
      const options = {
        key: orderRes.key_id, 
        amount: orderRes.amount, 
        currency: orderRes.currency,
        name: "DoraEngine",
        description: `Upgrade to ${plan.name}`,
        order_id: orderRes.order_id,
        handler: async function (response) {
          try {
            // 3. Verify signature on backend
            setProcessing(true);
            const verifyRes = await verifyPaymentSignature(token, {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              plan_code: plan.code
            });
            if (verifyRes.status === "success") {
              onPaymentDone(verifyRes.user); // update the logged-in user state
            }
          } catch (err) {
            setError(err.message || "Payment verification failed.");
            setProcessing(false);
          }
        },
        prefill: {
          name: user.email.split("@")[0],
          email: user.email,
          contact: user.mobile || "",
        },
        theme: {
          color: "#8b5cf6", // match DoraEngine primary accent
        },
      };

      const rzp = new window.Razorpay(options);
      rzp.on("payment.failed", function (response) {
        setError(response.error.description || "Payment failed.");
        setProcessing(false);
      });
      
      rzp.open();
    } catch (err) {
      setError(err.message || "Unable to initiate payment.");
      setProcessing(false);
    }
  }

  return (
    <div className="payment-page-wrapper">
      <div className="payment-header">
        <button className="btn btn-ghost btn-sm" onClick={onBack} style={{ margin: "0 auto 1.5rem", pointerEvents: processing ? "none" : "auto", opacity: processing ? 0.5 : 1 }}>
          <Icons.ArrowLeft /> Change plan
        </button>
        <h1 className="onboarding-title" style={{ marginBottom: "0.4rem" }}>Complete payment</h1>
        <p className="onboarding-subtitle">Secure payment powered by Razorpay</p>
      </div>

      <div className="payment-layout">
        <div className="payment-summary-card">
          <div className="payment-summary-title">Order Summary</div>
          <div className="payment-plan-block">
            <div className="payment-plan-icon"><Icons.Layers /></div>
            <div>
              <div className="payment-plan-name">{plan?.name}</div>
              <div className="payment-plan-desc">Billed per {plan?.billing} · Platform-managed API key</div>
            </div>
          </div>
          <div className="payment-line-items">
            <div className="payment-line"><span>{plan?.name}</span><span>₹{amount}</span></div>
            <div className="payment-line"><span>GST (18%)</span><span>₹{gst}</span></div>
          </div>
          <div className="payment-total-line">
            <span>Total</span>
            <span className="payment-total-amount">₹{total}</span>
          </div>
          <div className="payment-trust-items">
            {["256-bit SSL encrypted", "Powered by Razorpay", "Cancel anytime"].map((t) => (
              <div key={t} className="payment-trust-item">
                <span className="payment-trust-icon"><Icons.Check /></span>{t}
              </div>
            ))}
          </div>
        </div>

        <div className="payment-form-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ textAlign: "center", marginBottom: "2rem" }}>
            <h3 style={{ fontSize: "1.1rem", marginBottom: "0.5rem", color: "var(--text-primary)" }}>Ready to checkout?</h3>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
              Click below to securely complete your payment using UPI, QR code, credit/debit cards, or netbanking.
            </p>
          </div>

          {error && (
            <div className="auth-error" style={{ marginBottom: "1.5rem" }} role="alert">
              <Icons.Warning /> {error}
            </div>
          )}

          <button className="btn btn-primary btn-full" disabled={processing}
            onClick={handlePay} id="pay-now-btn" style={{ padding: "1rem" }}>
            {processing ? <><div className="spinner" /> Processing…</> : <><Icons.Lock /> Proceed to pay ₹{total}</>}
          </button>
          
          <div className="payment-powered" style={{ marginTop: "1.5rem" }}>
            Secured by <span>Razorpay</span> · PCI DSS compliant
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   APP TOPBAR
   ───────────────────────────────────────────────────────────────────────────── */

function AppTopbar({ user, page, onNavigate, onLogout }) {
  const initials = (user?.email || "U").charAt(0).toUpperCase();
  const isPaid = isPaidPlan(user?.plan_code);
  const planLabel = { free: "Free", standard_daily: "Daily", standard_monthly: "Monthly" }[user?.plan_code] || "Free";

  return (
    <header className="app-topbar">
      <div className="topbar-left">
        <div className="topbar-logo" onClick={() => onNavigate("research")}>
          <div className="topbar-logo-mark">D</div>
          <span>DoraEngine</span>
        </div>
        <nav className="topbar-nav">
          <button className={`topbar-nav-btn ${page === "research" ? "active" : ""}`}
            onClick={() => onNavigate("research")} id="nav-research">
            <Icons.Search /><span>Research</span>
          </button>
          {/* MVP: History tab removed from nav — re-enable with history feature */}
          <button className={`topbar-nav-btn ${page === "profile" ? "active" : ""}`}
            onClick={() => onNavigate("profile")} id="nav-profile">
            <Icons.User /><span>Profile</span>
          </button>
        </nav>
      </div>
      <div className="topbar-right">
        <div className="topbar-user-pill">
          <div className="topbar-user-avatar">{initials}</div>
          <span className="topbar-user-email">{user?.email}</span>
          <span className={`topbar-plan-badge ${isPaid ? "plan-badge-paid" : "plan-badge-free"}`}>
            {planLabel}
          </span>
        </div>
        <button className="btn btn-outline-accent btn-sm" onClick={() => onNavigate("plans")} id="nav-change-plan">
          <Icons.Plan /> Plan
        </button>
        <button className="btn btn-danger btn-sm" onClick={onLogout} id="nav-logout">
          <Icons.LogOut />
        </button>
      </div>
    </header>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   RESEARCH PAGE — tab components
   ───────────────────────────────────────────────────────────────────────────── */

function MarkdownAnswer({ text }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text || ""}</ReactMarkdown>
    </div>
  );
}

function ProgressPanel({ activeStage, stageHistory, researching }) {
  if (!researching && !activeStage) return null;
  const progress = activeStage?.progress || 0.05;
  return (
    <div className="progress-panel">
      <div className="progress-header">
        <div className="progress-eyebrow">
          <div className="stage-dot" /> Researching
        </div>
        <span className="progress-label">{activeStage?.label || "Preparing…"}</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${Math.max(progress * 100, 5)}%` }} />
      </div>
      <div className="progress-stages">
        {stageHistory.map((item, i) => (
          <div key={`${item.agent}-${i}`} className="progress-stage-row">
            <div className="stage-dot" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--sky-400)" }} />
            <span className="stage-agent">{item.agent}</span>
            <span className="stage-action">{item.stage?.label || item.action}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AnswerTab({ result, onResearch, onExportPdf, onExportDocx }) {
  const answer = result?.final_answer;
  const reasoning = result?.reasoning;
  if (!answer) return <div className="content-card"><div className="empty-state"><div className="empty-state-icon">✦</div>No answer generated yet.</div></div>;

  return (
    <div className="tab-content-area">
      <div className="content-card">
        <div className="confidence-badge">
          <Icons.Check /> Confidence {Math.round((answer.confidence || 0) * 100)}%
        </div>
        <MarkdownAnswer text={answer.answer} />
        {!!answer.citations?.length && (
          <div className="references">
            <h3 className="card-title" style={{ fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)" }}>References</h3>
            {answer.citations.map((c) => (
              <a key={c.number} href={c.url} className="reference-link" target="_blank" rel="noreferrer">
                <span style={{ color: "var(--text-muted)", flexShrink: 0 }}>[{c.number}]</span>
                {c.title || c.domain} <Icons.ExternalLink />
              </a>
            ))}
          </div>
        )}
      </div>

      {!!reasoning?.key_findings?.length && (
        <div className="content-card">
          <h3 className="card-title">Key Findings</h3>
          <div className="findings-grid">
            {reasoning.key_findings.map((f) => <div key={f} className="finding-item">{f}</div>)}
          </div>
        </div>
      )}

      {!!result.followups?.length && (
        <div className="content-card">
          <h3 className="card-title">Explore Further</h3>
          <div className="followups-grid">
            {result.followups.map((q) => (
              <button key={q} className="followup-btn" onClick={() => onResearch(q)}>
                <Icons.Search /> {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="content-card">
        <h3 className="card-title">Export Results</h3>
        <div className="export-row">
          <button className="btn btn-ghost" onClick={onExportPdf} id="export-pdf"><Icons.FileDown /> Download PDF</button>
          <button className="btn btn-ghost" onClick={onExportDocx} id="export-docx"><Icons.FileDown /> Download Word</button>
        </div>
      </div>
    </div>
  );
}

function SourcesTab({ result }) {
  const rows = result?.sources_table || [];
  if (!rows.length) return <div className="content-card"><div className="empty-state"><div className="empty-state-icon">⊞</div>No sources were retrieved.</div></div>;

  return (
    <div className="tab-content-area">
      <div className="content-card table-wrapper">
        <table>
          <thead>
            <tr><th>Source</th><th>Domain</th><th>Scraped</th><th>Preview</th></tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.url}>
                <td><a href={row.url} target="_blank" rel="noreferrer">{row.title || row.url}</a></td>
                <td style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>{row.domain}</td>
                <td><span style={{ color: row.scraped ? "var(--emerald-400)" : "var(--text-muted)", fontSize: "0.8rem" }}>{row.scraped ? "✓" : "—"}</span></td>
                <td style={{ maxWidth: 320 }}>{row.snippet}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ReasoningTab({ result }) {
  const reasoning = result?.reasoning;
  const queryPlan = result?.query_plan;
  if (!reasoning && !queryPlan) return <div className="content-card"><div className="empty-state"><div className="empty-state-icon">⊙</div>No reasoning trace available.</div></div>;

  const flowStages = [
    { label: "Your Question", text: result.query },
    { label: "Key Concepts Identified", text: queryPlan?.keywords?.length ? queryPlan.keywords.join(" · ") : "Topic and intent identified" },
    { label: "Source Insights Extracted", text: result.stats?.successful_scrapes ? `Insights extracted from ${result.stats.successful_scrapes} sources` : `Reviewed ${result.stats?.source_count || 0} sources` },
    { label: "Cross-Validation", text: reasoning ? `${Math.round((reasoning.confidence || 0) * 100)}% confidence across sources` : "Cross-checked for consistency" },
    { label: "Answer Synthesized", text: reasoning?.reasoning_summary || "Final answer composed from validated sources" },
  ];

  return (
    <div className="tab-content-area">
      <div className="content-card">
        <h3 className="card-title">How this answer was derived</h3>
        <div className="flow-list">
          {flowStages.map((stage, i) => (
            <div key={stage.label} className="flow-item">
              <div className="flow-step-num">{i + 1}</div>
              <div className="flow-step-content">
                <div className="flow-step-label">{stage.label}</div>
                <div className="flow-step-text">{stage.text}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
      {!!reasoning?.steps?.length && (
        <div className="content-card">
          <h3 className="card-title">Detailed Reasoning Steps</h3>
          <div className="reasoning-steps">
            {reasoning.steps.map((step) => (
              <div key={step.step_number} className="reasoning-step">
                <div className="reasoning-step-num">{step.step_number}</div>
                <div>
                  <div className="reasoning-step-action">{step.action}</div>
                  <p className="reasoning-step-detail">{step.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function GraphTab({ result }) {
  const graph = result?.graph;
  const [helpOpen, setHelpOpen] = useState(false);
  if (!graph?.stats?.nodes) return <div className="content-card"><div className="empty-state"><div className="empty-state-icon">⬡</div>Knowledge graph is empty or unavailable.</div></div>;

  const domainCount = graph.stats.top_domains?.length ?? 0;

  return (
    <div className="tab-content-area">
      <div className="content-card">

        {/* Stat pill strip */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "rgba(124,58,237,0.12)", border: "1px solid rgba(124,58,237,0.2)", borderRadius: "20px", padding: "4px 12px", fontSize: "0.8rem", color: "#a78bfa" }}>
              <span>⬡</span> <strong>{graph.stats.nodes}</strong> <span style={{ color: "var(--text-muted)" }}>nodes</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: "20px", padding: "4px 12px", fontSize: "0.8rem", color: "#60a5fa" }}>
              <span>↔</span> <strong>{graph.stats.edges}</strong> <span style={{ color: "var(--text-muted)" }}>connections</span>
            </div>
            {domainCount > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "rgba(16,185,129,0.07)", border: "1px solid rgba(16,185,129,0.18)", borderRadius: "20px", padding: "4px 12px", fontSize: "0.8rem", color: "#34d399" }}>
                <span>🌐</span> <strong>{domainCount}</strong> <span style={{ color: "var(--text-muted)" }}>websites</span>
              </div>
            )}
          </div>
        </div>

        {/* Collapsible plain-English explainer */}
        <div style={{ marginBottom: "0.75rem", background: "rgba(99,102,241,0.07)", border: "1px solid rgba(99,102,241,0.2)", borderRadius: "10px", overflow: "hidden" }}>
          <button
            onClick={() => setHelpOpen(o => !o)}
            style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", background: "none", border: "none", cursor: "pointer", color: "var(--text-primary)" }}>
            <span style={{ fontSize: "0.84rem", fontWeight: "600", display: "flex", alignItems: "center", gap: "7px" }}>
              <span>💡</span> What am I looking at?
            </span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", transition: "transform 0.2s", display: "inline-block", transform: helpOpen ? "rotate(180deg)" : "none" }}>▾</span>
          </button>
          {helpOpen && (
            <div style={{ padding: "0 14px 14px", borderTop: "1px solid rgba(99,102,241,0.15)" }}>
              <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", marginTop: "10px", marginBottom: "12px", lineHeight: "1.6" }}>
                This is a visual map of all the information DoraEngine gathered from the web to answer your question.
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: "9px" }}>
                {[
                  ["🫧", "Each bubble", "is a snippet of content from a real webpage — like a note DoraEngine jotted down during research."],
                  ["↔", "A line between bubbles", "means those two snippets are about a similar topic. More lines = more important idea."],
                  ["🎨", "Colours", "represent different websites. Same colour = same source. Check the legend inside the graph (top-right) to see which colour is which site."],
                  ["👆", "Hover over any bubble", "to read a preview of that content. Drag to explore, scroll to zoom, or click \"Fit view\" to reset."],
                ].map(([icon, bold, rest]) => (
                  <div key={bold} style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                    <span style={{ fontSize: "1rem", flexShrink: 0, marginTop: "1px" }}>{icon}</span>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: "1.55" }}>
                      <strong style={{ color: "var(--text-primary)" }}>{bold}</strong> {rest}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Graph iframe */}
        <iframe className="graph-frame" srcDoc={graph.html} title="Knowledge Graph" sandbox="allow-scripts allow-same-origin" />

        <div style={{ marginTop: "0.6rem", fontSize: "0.74rem", color: "var(--text-muted)", display: "flex", gap: "1.25rem", flexWrap: "wrap" }}>
          <span><span style={{ color: "#7c3aed" }}>—</span> Same topic</span>
          <span><span style={{ color: "#3b82f6" }}>—</span> Same article</span>
          <span style={{ marginLeft: "auto" }}>A guide is available inside the map ↗</span>
        </div>
      </div>

      {!!graph.stats.top_domains?.length && (
        <div className="content-card">
          <h3 className="card-title">Top Websites in Graph</h3>
          <div className="domains-chart">
            {graph.stats.top_domains.map((entry) => (
              <div key={entry.domain} className="domain-row">
                <span className="domain-label">{entry.domain}</span>
                <div className="domain-bar-track">
                  <div className="domain-bar-fill" style={{ width: `${Math.min(entry.count * 10, 100)}%` }} />
                </div>
                <span className="domain-count">{entry.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   RESEARCH PAGE (main playground — centered)
   ───────────────────────────────────────────────────────────────────────────── */

function ResearchPage({ user, config, token }) {
  const [query, setQuery] = useState(() => sessionStorage.getItem("dora_query") || "");
  const [result, setResult] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem("dora_result")) || null; }
    catch { return null; }
  });
  const [researching, setResearching] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState(() => sessionStorage.getItem("dora_tab") || RESEARCH_TABS[0].id);
  const [activeStage, setActiveStage] = useState(null);
  const [stageHistory, setStageHistory] = useState([]);

  useEffect(() => {
    sessionStorage.setItem("dora_query", query);
  }, [query]);

  useEffect(() => {
    sessionStorage.setItem("dora_tab", activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (result) sessionStorage.setItem("dora_result", JSON.stringify(result));
    else sessionStorage.removeItem("dora_result");
  }, [result]);

  const requiresApiKey = user?.plan_code === "free" && !user?.has_groq_api_key;
  const stats = result?.stats || null;

  async function handleResearch(nextQuery = query) {
    if (!nextQuery.trim() || researching || requiresApiKey) return;
    setQuery(nextQuery);
    setError("");
    setResult(null);
    setResearching(true);
    setActiveStage(config.agent_stages?.[0] || null);
    setStageHistory([]);
    setActiveTab(RESEARCH_TABS[0].id);

    try {
      await streamResearch(token, nextQuery, {
        onStage: (payload) => {
          if (payload.stage) setActiveStage(payload.stage);
          setStageHistory((cur) => [...cur, payload]);
        },
        onComplete: (payload) => {
          setResult(payload);
          if (!payload.success) setError(payload.error || "Research failed");
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
    if (!result?.final_answer) return;
    try {
      const blob = await exportDocument(token, type, {
        query: result.query,
        answer: result.final_answer.answer,
        sources: result.sources_table?.slice(0, 15) || [],
        confidence: result.final_answer.confidence,
        timestamp: new Date().toISOString(),
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `DoraEngine_${result.query.slice(0, 30).replace(/\s+/g, "_")}.${type === "pdf" ? "pdf" : "docx"}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="app-main-inner">
      {requiresApiKey && (
        <div className="api-key-banner">
          <div className="api-key-banner-text">
            <Icons.Warning />
            Free plan requires a GROQ API key. Add yours in <strong>Profile → API Keys</strong> to start researching.
          </div>
        </div>
      )}

      <div className="research-header">
        <h1 className="research-header-title">Research Playground</h1>
        <p className="research-header-sub">Ask anything — DoraEngine will research, reason, and cite its sources.</p>
      </div>

      <div className="search-wrapper">
        <div className="search-box">
          <span style={{ color: "var(--text-muted)", flexShrink: 0 }}><Icons.Search /></span>
          <input className="search-box-input" value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleResearch()}
            placeholder="Ask anything… I'll research, verify, and explain it."
            disabled={researching || requiresApiKey} aria-label="Research query" />
          <button className="btn btn-primary"
            onClick={() => handleResearch()}
            disabled={researching || requiresApiKey || !query.trim()}
            id="research-submit">
            {researching ? <div className="spinner" /> : <Icons.Send />}
            {researching ? "Researching…" : "Research"}
          </button>
        </div>

        {!result && !researching && !!config.suggestions?.length && (
          <div className="search-suggestions">
            {config.suggestions.map((s) => (
              <button key={s} className="suggestion-chip" onClick={() => handleResearch(s)}>{s}</button>
            ))}
          </div>
        )}
      </div>

      <ProgressPanel activeStage={activeStage} stageHistory={stageHistory} researching={researching} />

      {error && <div className="error-banner"><Icons.X /> {error}</div>}

      {stats && (
        <div className="stats-row">
          <div className="stat-card"><span className="stat-label">Research time</span><span className="stat-value">{stats.total_time_seconds}s</span></div>
          <div className="stat-card"><span className="stat-label">Sources</span><span className="stat-value">{stats.display_source_count}</span></div>
          <div className="stat-card"><span className="stat-label">Confidence</span><span className="stat-value">{stats.confidence_percent}%</span></div>
        </div>
      )}

      {result?.success && (
        <>
          <div className="result-tabs" role="tablist">
            {RESEARCH_TABS.map((tab) => (
              <button key={tab.id} role="tab" aria-selected={activeTab === tab.id}
                className={`result-tab ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)} id={`tab-${tab.id}`}>
                <span>{tab.icon}</span><span>{tab.label}</span>
              </button>
            ))}
          </div>
          {activeTab === "answer"    && <AnswerTab result={result} onResearch={handleResearch} onExportPdf={() => handleExport("pdf")} onExportDocx={() => handleExport("docx")} />}
          {activeTab === "sources"   && <SourcesTab result={result} />}
          {activeTab === "reasoning" && <ReasoningTab result={result} />}
          {activeTab === "graph"     && <GraphTab result={result} />}
        </>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   PROFILE PAGE — GROQ key only (Tavily removed from user-facing UI)
   ───────────────────────────────────────────────────────────────────────────── */

function ProfilePage({ user, token, onUserUpdate }) {
  const [groqKey, setGroqKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [error, setError] = useState("");

  const isFree = user?.plan_code === "free";
  const initials = (user?.email || "U").charAt(0).toUpperCase();
  const planNames = {
    free: "Free Plan",
    standard_daily: "Standard Daily",
    standard_monthly: "Standard Monthly",
  };

  async function handleSave() {
    setSaving(true);
    setError("");
    setSuccessMsg("");
    try {
      const payload = {};
      if (groqKey.trim()) payload.groq_api_key = groqKey.trim();
      const response = await updateProfile(token, payload);
      onUserUpdate(response.user);
      setSuccessMsg("API key updated successfully.");
      setGroqKey("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="profile-page app-main-inner">
      <div className="profile-header-card">
        <div className="profile-avatar">{initials}</div>
        <div className="profile-info">
          <div className="profile-name">{user?.email}</div>
          <div className="profile-email">{user?.email}</div>
          <div className="profile-meta-row">
            <div className="profile-meta-pill">{user?.mobile || "—"}</div>
            <div className="profile-meta-pill">{planNames[user?.plan_code] || "Free"}</div>
          </div>
        </div>
      </div>

      <div className="profile-section-card">
        <div className="profile-section-header">
          <div className="profile-section-title">Account Information</div>
          <div className="profile-section-subtitle">Read-only. Contact support to update.</div>
        </div>
        <div className="profile-section-body">
          {[
            { label: "Email", value: user?.email },
            { label: "Mobile", value: user?.mobile },
            { label: "Plan", value: planNames[user?.plan_code] },
            { label: "Verified", value: user?.is_verified ? "✓ Verified" : "Not verified" },
            { label: "Member since", value: user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—" },
          ].map(({ label, value }) => (
            <div key={label} className="profile-readonly-row">
              <span className="profile-readonly-label">{label}</span>
              <span className="profile-readonly-value">{value || "—"}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="profile-section-card">
        <div className="profile-section-header">
          <div className="profile-section-title">GROQ API Key</div>
          <div className="profile-section-subtitle">
            {isFree
              ? "Required for the Free plan — used for all your research queries."
              : "Your paid plan uses DoraEngine's platform key. You may optionally override it."}
          </div>
        </div>
        <div className="profile-section-body">
          <div className="profile-readonly-row">
            <span className="profile-readonly-label">Current key</span>
            <span className={`profile-key-status ${user?.has_groq_api_key ? "key-status-set" : "key-status-unset"}`}>
              {user?.has_groq_api_key ? <><Icons.Check /> Stored</> : <><Icons.X /> Not set</>}
            </span>
          </div>

          <div className="field">
            <label className="field-label" htmlFor="profile-groq-key">
              {isFree ? "GROQ API Key *" : "GROQ API Key (optional override)"}
            </label>
            <input id="profile-groq-key" type="password" className="field-input"
              value={groqKey} onChange={(e) => setGroqKey(e.target.value)}
              placeholder={user?.has_groq_api_key ? "Enter new key to replace existing…" : "gsk_..."}
              autoComplete="off" />
            {isFree && !user?.has_groq_api_key && (
              <span className="field-hint">
                Required for Free plan.{" "}
                <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer">
                  Create a key at console.groq.com →
                </a>
              </span>
            )}
          </div>

          {successMsg && <div className="success-alert"><Icons.Check /> {successMsg}</div>}
          {error && <div className="auth-error"><Icons.X /> {error}</div>}

          <div className="profile-save-row">
            <button className="btn btn-primary"
              onClick={handleSave} disabled={saving || !groqKey.trim()} id="profile-save-btn">
              {saving ? <><div className="spinner" /> Saving…</> : "Save API key"}
            </button>
          </div>
        </div>
      </div>

      {/* MVP: Tavily key removed from user-facing profile — managed backend-only */}
      {/* Future: Research preferences, export format defaults */}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   APP SHELL
   ───────────────────────────────────────────────────────────────────────────── */

function AppShell({ user, token, config, plans, onLogout, onUserUpdate, onPlanChange }) {
  const [page, setPage] = useState(() => sessionStorage.getItem("dora_page") || "research");

  useEffect(() => {
    sessionStorage.setItem("dora_page", page);
  }, [page]);

  return (
    <div className="app-root">
      <AppTopbar user={user} page={page} onNavigate={setPage} onLogout={onLogout} />
      <div className="app-body">
        {/* MVP: History sidebar removed — re-enable when history feature ships */}
        <main className="app-main">
          {page === "research" && (
            <ResearchPage user={user} config={config} token={token} />
          )}
          {page === "plans" && (
            <PlanSelectionPage
              plans={plans}
              user={user}
              currentPlanCode={user?.plan_code}
              onSelect={(planCode) => onPlanChange(planCode, setPage)}
              onSkip={() => setPage("research")}
              isChanging
            />
          )}
          {page === "profile" && (
            <ProfilePage user={user} token={token} onUserUpdate={onUserUpdate} />
          )}
        </main>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   ROOT APP — state machine
   Screens: landing | auth | plan_select | groq_key | payment | app
            | forgot_password | reset_password
   ───────────────────────────────────────────────────────────────────────────── */

export default function RootApp() {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY) || "");
  const [user, setUser] = useState(null);
  const [config, setConfig] = useState({ suggestions: [], agent_stages: [] });
  const [plans, setPlans] = useState([]);

  const [screen, setScreen] = useState("landing");
  const [authMode, setAuthMode] = useState("login");
  const [pendingPlanCode, setPendingPlanCode] = useState(null);
  const [devOtp, setDevOtp] = useState("");
  const [resetPasswordEmail, setResetPasswordEmail] = useState("");
  const [resetPasswordToken, setResetPasswordToken] = useState("");

  const [groqSaving, setGroqSaving] = useState(false);
  const [groqError, setGroqError]   = useState("");

  // Prevents session-restore from overriding the reset_password screen.
  const resetPasswordRef = useRef(false);
  const skipFetchMeRef = useRef(false);

  // Boot: detect password-reset link (?reset_email=...&reset_token=...)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const rEmail = params.get("reset_email");
    const rToken = params.get("reset_token");
    if (rEmail && rToken) {
      resetPasswordRef.current = true;
      setResetPasswordEmail(decodeURIComponent(rEmail));
      setResetPasswordToken(rToken);
      history.replaceState({}, document.title, window.location.pathname);
      setScreen("reset_password");
    }
  }, []);

  // Boot: load config + plans
  useEffect(() => {
    fetchConfig().then(setConfig).catch(() => {});
    fetchPlans().then((p) => setPlans(p.plans || [])).catch(() => {});
  }, []);

  // Boot: restore session for returning users
  useEffect(() => {
    if (!token) {
      setUser(null);
      if (!resetPasswordRef.current) setScreen("landing");
      return;
    }
    if (skipFetchMeRef.current) {
      skipFetchMeRef.current = false;
      return;
    }
    fetchMe(token)
      .then((payload) => {
        const u = payload.user;
        setUser(u);
        if (u.plan_code === "free" && !u.has_groq_api_key) {
          setScreen("groq_key");
        } else {
          setScreen("app");
        }
      })
      .catch(() => {
        localStorage.removeItem(STORAGE_KEY);
        setToken("");
        setScreen("landing");
      });
  }, [token]);

  // Auth flow — handles both login and direct signup
  function handleAuthSuccess(payload, mode) {
    skipFetchMeRef.current = true;
    const u = payload.user;
    localStorage.setItem(STORAGE_KEY, payload.token);
    setToken(payload.token);
    setUser(u);

    if (mode === "signup") {
      // New user: always pick a plan first
      setScreen("plan_select");
    } else {
      // Returning login
      if (u.plan_code === "free" && !u.has_groq_api_key) {
        setScreen("groq_key");
      } else {
        setScreen("app");
      }
    }
  }

  // OTP verified
  function handleOtpVerified(updatedUser) {
    setUser(updatedUser);
    setDevOtp("");
    // After verification: always go to plan selection for new signups
    // For returning logins (re-verification): go to app or groq_key
    if (!updatedUser.plan_code || updatedUser.plan_code === "free") {
      if (!updatedUser.has_groq_api_key) {
        // New user: show plan selection
        setScreen("plan_select");
      } else {
        setScreen("app");
      }
    } else {
      setScreen("app");
    }
  }

  // Plan selection
  async function handlePlanSelect(planCode) {
    setPendingPlanCode(planCode);
    if (planCode === "free") {
      setScreen("groq_key");
    } else {
      setScreen("payment");
    }
  }

  async function handlePaymentDone(updatedUser) {
    if (updatedUser) {
      setUser(updatedUser);
      setScreen("app");
      setPendingPlanCode(null);
    }
  }

  async function handleGroqKeySave(key) {
    setGroqSaving(true);
    setGroqError("");
    try {
      if (pendingPlanCode === "free" || !user?.plan_code || user.plan_code !== "free") {
        if (pendingPlanCode === "free") {
          const planRes = await updatePlan(token, { plan_code: "free" });
          setUser(planRes.user);
        }
      }
      const response = await updateProfile(token, { groq_api_key: key });
      setUser(response.user);
      setPendingPlanCode(null);
      setScreen("app");
    } catch (err) {
      setGroqError(err.message);
    } finally {
      setGroqSaving(false);
    }
  }

  // In-app plan change
  async function handleInAppPlanChange(planCode, navigate) {
    if (planCode === "free") {
      try {
        const response = await updatePlan(token, { plan_code: planCode });
        setUser(response.user);
        if (!response.user.has_groq_api_key) {
          setPendingPlanCode(planCode);
          setScreen("groq_key");
        } else {
          navigate?.("research");
        }
      } catch (err) {
        console.error("Plan change failed:", err);
      }
    } else {
      setPendingPlanCode(planCode);
      setScreen("payment");
    }
  }

  function handleLogout() {
    localStorage.removeItem(STORAGE_KEY);
    sessionStorage.clear();
    setToken("");
    setUser(null);
    setPendingPlanCode(null);
    setScreen("landing");
  }

  const pendingPlan = plans.find((p) => p.code === pendingPlanCode) || null;

  // ── Screen render ────────────────────────────────────────────────────────────

  if (screen === "landing") {
    return (
      <LandingPage
        onLogin={() => { setAuthMode("login"); setScreen("auth"); }}
        onSignUp={() => { setAuthMode("signup"); setScreen("auth"); }}
      />
    );
  }

  if (screen === "auth") {
    return (
      <AuthPage
        defaultMode={authMode}
        onBack={() => setScreen("landing")}
        onSuccess={handleAuthSuccess}
        onForgotPassword={() => setScreen("forgot_password")}
      />
    );
  }

  if (screen === "otp_verify" && user) {
    return (
      <OtpVerifyPage
        user={user}
        token={token}
        devOtp=""
        onVerified={handleOtpVerified}
        onBack={() => { handleLogout(); setScreen("auth"); }}
      />
    );
  }

  if (screen === "plan_select") {
    return (
      <PlanSelectionPage
        plans={plans}
        user={user}
        currentPlanCode={user?.plan_code}
        onSelect={handlePlanSelect}
        onSkip={() => setScreen("app")}
        isChanging={false}
      />
    );
  }

  if (screen === "groq_key") {
    return (
      <GroqKeyPage
        onSave={handleGroqKeySave}
        onSkip={() => setScreen("app")}
        loading={groqSaving}
        error={groqError}
      />
    );
  }

  if (screen === "payment" && pendingPlan) {
    return (
      <PaymentPage
        plan={pendingPlan}
        user={user}
        token={token}
        onPaymentDone={handlePaymentDone}
        onBack={() => setScreen("plan_select")}
      />
    );
  }

  if (screen === "app" && user) {
    return (
      <AppShell
        user={user}
        token={token}
        config={config}
        plans={plans}
        onLogout={handleLogout}
        onUserUpdate={setUser}
        onPlanChange={handleInAppPlanChange}
      />
    );
  }

  if (screen === "forgot_password") {
    return (
      <ForgotPasswordPage
        onBack={() => { setAuthMode("login"); setScreen("auth"); }}
      />
    );
  }

  if (screen === "reset_password") {
    return (
      <ResetPasswordPage
        email={resetPasswordEmail}
        token={resetPasswordToken}
        onSuccess={() => {
          setResetPasswordEmail("");
          setResetPasswordToken("");
          resetPasswordRef.current = false;
          setAuthMode("login");
          setScreen("auth");
        }}
      />
    );
  }

  // Loading / fallback
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="spinner spinner-dark" style={{ width: 32, height: 32 }} />
    </div>
  );
}
