const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

function buildUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function readJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.error || "Request failed");
  }
  return data;
}

export async function fetchConfig() {
  const response = await fetch(buildUrl("/api/config"));
  return readJson(response);
}

export async function fetchPlans() {
  const response = await fetch(buildUrl("/api/plans"));
  return readJson(response);
}

export async function signup(payload) {
  const response = await fetch(buildUrl("/api/auth/signup"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email_verified: false, ...payload }),
  });
  return readJson(response);
}

export async function login(payload) {
  const response = await fetch(buildUrl("/api/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJson(response);
}

export async function fetchMe(token) {
  const response = await fetch(buildUrl("/api/auth/me"), {
    headers: authHeaders(token),
  });
  return readJson(response);
}

// ── OTP Verification ───────────────────────────────────────────────────────────

export async function sendOtp(token) {
  const response = await fetch(buildUrl("/api/auth/send-otp"), {
    method: "POST",
    headers: authHeaders(token),
  });
  return readJson(response);
}

export async function verifyOtp(token, otp_code) {
  const response = await fetch(buildUrl("/api/auth/verify-otp"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(token),
    },
    body: JSON.stringify({ otp_code }),
  });
  return readJson(response);
}

// ──────────────────────────────────────────────────────────────────────────────

// ── Password Reset ─────────────────────────────────────────────────────────────

export async function forgotPassword(email) {
  const response = await fetch(buildUrl("/api/auth/forgot-password"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  return readJson(response);
}

export async function resetPassword(email, token, new_password) {
  const response = await fetch(buildUrl("/api/auth/reset-password"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, token, new_password }),
  });
  return readJson(response);
}

// ──────────────────────────────────────────────────────────────────────────────

// ── Payments Integration ──────────────────────────────────────────────────────

export async function createPaymentOrder(token, payload) {
  const response = await fetch(buildUrl("/api/payments/create-order"), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify(payload),
  });
  return readJson(response);
}

export async function verifyPaymentSignature(token, payload) {
  const response = await fetch(buildUrl("/api/payments/verify"), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify(payload),
  });
  return readJson(response);
}

// ──────────────────────────────────────────────────────────────────────────────
export async function updateProfile(token, payload) {
  const response = await fetch(buildUrl("/api/profile"), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(token),
    },
    body: JSON.stringify(payload),
  });
  return readJson(response);
}

export async function updatePlan(token, payload) {
  const response = await fetch(buildUrl("/api/profile/plan"), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(token),
    },
    body: JSON.stringify(payload),
  });
  return readJson(response);
}

// MVP: History fetch disabled — endpoint is commented out on backend
// export async function fetchHistory(token) {
//   const response = await fetch(buildUrl("/api/history"), {
//     headers: authHeaders(token),
//   });
//   return readJson(response);
// }

export async function exportDocument(token, type, payload) {
  const response = await fetch(buildUrl(`/api/export/${type}`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(token),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Failed to export");
  }

  return response.blob();
}

export async function streamResearch(token, query, handlers) {
  const response = await fetch(buildUrl("/api/research/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...authHeaders(token),
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok || !response.body) {
    const message = await response.text();
    throw new Error(message || "Unable to start research");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const rawEvent of events) {
      const line = rawEvent
        .split("\n")
        .find((entry) => entry.startsWith("data: "));

      if (!line) {
        continue;
      }

      const payload = JSON.parse(line.slice(6));
      if (payload.type === "stage") {
        handlers.onStage?.(payload);
      } else if (payload.type === "complete") {
        handlers.onComplete?.(payload.result);
      } else if (payload.type === "error") {
        throw new Error(payload.error || "Research failed");
      }
    }
  }
}
