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
    body: JSON.stringify(payload),
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

export async function fetchHistory(token) {
  const response = await fetch(buildUrl("/api/history"), {
    headers: authHeaders(token),
  });
  return readJson(response);
}

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
    throw new Error(text || "Failed to export PDF");
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
