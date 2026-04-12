const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

function buildUrl(path) {
  return `${API_BASE_URL}${path}`;
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

export async function exportPdf(payload) {
  const response = await fetch(buildUrl("/api/export/pdf"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Failed to export PDF");
  }

  return response.blob();
}

export async function streamResearch(query, handlers) {
  const response = await fetch(buildUrl("/api/research/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
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
