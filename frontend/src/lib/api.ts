// src/lib/api.ts

// Use environment variable for API base URL
// - In development: empty string (Vite proxy handles /api/* requests)
// - In production: full Railway URL (or empty if served from Flask)
const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function postJob(endpoint: string, body: Record<string, unknown>): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    // Try to extract error message from response body
    let errorMsg = `Request failed: ${res.status}`;
    try {
      const errBody = await res.json();
      errorMsg = errBody.message || errBody.error || errorMsg;
    } catch {
      // response wasn't JSON, use default
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

export async function fetchJobResult(jobId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/job/${jobId}`);
  if (!res.ok) throw new Error(`Failed to fetch job: ${res.status}`);
  return res.json();
}

export async function cancelJob(jobId: string): Promise<void> {
  await fetch(`${API_BASE}/api/job/${jobId}/cancel`, { method: "POST" });
}

export type SSECallback = {
  onMessage?: (msg: string) => void;
  onComplete?: () => void;
  onError?: (err: string) => void;
};

export function streamJob(jobId: string, cb: SSECallback): () => void {
  let attempts = 0;
  let es: EventSource | null = null;

  function connect() {
    es = new EventSource(`${API_BASE}/api/job/${jobId}/stream`);

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.heartbeat) return;
        if (data.message) cb.onMessage?.(data.message);
        if (data.status === "completed") {
          es?.close();
          cb.onComplete?.();
        }
        if (data.status === "failed") {
          es?.close();
          cb.onError?.(data.error || "Analysis failed");
        }
        if (data.status === "cancelled") {
          es?.close();
          cb.onError?.("Analysis cancelled");
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es?.close();
      attempts++;
      if (attempts < 3) {
        setTimeout(connect, Math.pow(2, attempts) * 1000);
      } else {
        cb.onError?.("Connection lost");
      }
    };
  }

  connect();
  return () => es?.close();
}

export async function checkHealth(): Promise<Record<string, boolean>> {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.json();
  } catch {
    return { status: false } as any;
  }
}

export type AnalysisMode = "comprehensive" | "key-claims" | "bias-analysis" | "lie-detection" | "manipulation" | "llm-output";

export const MODE_ENDPOINTS: Record<AnalysisMode, string> = {
  "comprehensive": "/api/comprehensive-analysis",
  "key-claims": "/api/key-claims",
  "bias-analysis": "/api/bias",
  "lie-detection": "/api/lie-detection",
  "manipulation": "/api/manipulation",
  "llm-output": "/api/check",
};

export const MODE_INFO: Record<AnalysisMode, { label: string; description: string }> = {
  "comprehensive": { label: "Comprehensive Analysis", description: "Full verification -- checks source, author & content quality" },
  "key-claims": { label: "Key Claims", description: "Verify 2-3 main arguments" },
  "bias-analysis": { label: "Bias Analysis", description: "Detect political or ideological bias" },
  "lie-detection": { label: "Deception Detection", description: "Find linguistic markers of deception and disinformation" },
  "manipulation": { label: "Manipulation Check", description: "Detect agenda & fact distortion" },
  "llm-output": { label: "LLM Output", description: "Verify AI-generated content" },
};

export function buildRequestBody(
  mode: AnalysisMode,
  content: string,
  sourceUrl?: string,
  sourceContext?: Record<string, unknown>
): Record<string, unknown> {
  const base: Record<string, unknown> = { content };

  switch (mode) {
    case "comprehensive":
      if (sourceUrl) base.source_url = sourceUrl;
      return base;
    case "key-claims":
      if (sourceContext) base.source_context = sourceContext;
      return base;
    case "bias-analysis":
      base.text = content;
      if (sourceUrl) base.publication_url = sourceUrl;
      if (sourceContext) base.source_context = sourceContext;
      return base;
    case "lie-detection":
      base.text = content;
      if (sourceContext) base.source_context = sourceContext;
      return base;
    case "manipulation":
      if (sourceUrl) base.source_info = sourceUrl;
      if (sourceContext) base.source_credibility = sourceContext;
      return base;
    case "llm-output":
      base.input_type = "html";
      return base;
    default:
      return base;
  }
}