// src/pages/Index.tsx
import { useState, useCallback, useRef } from "react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ModeSelector from "@/components/ModeSelector";
import ContentInput from "@/components/ContentInput";
import SourceCard from "@/components/SourceCard";
import ProgressLog from "@/components/ProgressLog";
import ReportRenderer from "@/components/ReportRenderer";
import {
  postJob, fetchJobResult, cancelJob, streamJob,
  type AnalysisMode, MODE_ENDPOINTS, buildRequestBody,
} from "@/lib/api";

type AppState = "idle" | "fetching" | "analyzing" | "done" | "error";

const Index = () => {
  const [mode, setMode] = useState<AnalysisMode>("comprehensive");
  const [content, setContent] = useState("");
  const [url, setUrl] = useState("");
  const [article, setArticle] = useState<Record<string, any> | null>(null);
  const [state, setState] = useState<AppState>("idle");
  const [messages, setMessages] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const closeStreamRef = useRef<(() => void) | null>(null);

  const reset = useCallback(() => {
    setState("idle");
    setMessages([]);
    setResult(null);
    setError(null);
  }, []);

  const fullReset = useCallback(() => {
    reset();
    setContent("");
    setUrl("");
    setArticle(null);
  }, [reset]);

  const handleFetchUrl = useCallback(async () => {
    if (!url) return;
    setState("fetching");
    setMessages(["Fetching article from URL..."]);

    try {
      const { job_id } = await postJob("/api/scrape-url", {
        url,
        extract_metadata: true,
        check_credibility: true,
        run_mbfc_if_missing: true,
      });

      closeStreamRef.current = streamJob(job_id, {
        onMessage: (msg) => setMessages((prev) => [...prev, msg]),
        onComplete: async () => {
          const job = await fetchJobResult(job_id);
          const r = job.result || job;
          setArticle(r);
          if (r.content) setContent(r.content);
          setState("idle");
          setMessages([]);
        },
        onError: (err) => {
          setError(err);
          setState("error");
        },
      });
    } catch (e: any) {
      setError(e.message);
      setState("error");
    }
  }, [url]);

  const handleAnalyze = useCallback(async () => {
    if (!content.trim()) return;
    setState("analyzing");
    setMessages(["Starting analysis..."]);
    setResult(null);
    setError(null);

    const sourceContext = article?.credibility
      ? {
          publication: article.publication_name,
          credibility_tier: article.credibility.tier,
          bias_rating: article.credibility.bias_rating,
          factual_reporting: article.credibility.factual_reporting,
        }
      : undefined;

    const body = buildRequestBody(mode, content, url || article?.url, sourceContext);

    try {
      const { job_id } = await postJob(MODE_ENDPOINTS[mode], body);

      closeStreamRef.current = streamJob(job_id, {
        onMessage: (msg) => setMessages((prev) => [...prev, msg]),
        onComplete: async () => {
          const job = await fetchJobResult(job_id);
          setResult(job.result || job);
          setState("done");
        },
        onError: (err) => {
          setError(err);
          setState("error");
        },
      });
    } catch (e: any) {
      setError(e.message);
      setState("error");
    }
  }, [content, mode, url, article]);

  const handleCancel = useCallback(async () => {
    closeStreamRef.current?.();
    setState("idle");
    setMessages([]);
  }, []);

  const isProcessing = state === "analyzing" || state === "fetching";

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        <div className="container max-w-3xl py-10">
          {/* Hero */}
          <h1 className="text-4xl md:text-5xl font-display text-center mb-10">
            AI Content Analyzer
          </h1>

          {/* Mode Selector */}
          <div className="mb-6">
            <ModeSelector selected={mode} onSelect={setMode} />
          </div>

          {/* Source Card */}
          {article && !isProcessing && state !== "done" && (
            <div className="mb-4">
              <SourceCard article={article} />
            </div>
          )}

          {/* Input */}
          {state !== "done" && (
            <div className="mb-4">
              <ContentInput
                content={content}
                onContentChange={setContent}
                url={url}
                onUrlChange={setUrl}
                onFetchUrl={handleFetchUrl}
                isFetching={state === "fetching"}
                mode={mode}
              />
            </div>
          )}

          {/* Actions */}
          {state === "idle" && (
            <div className="flex justify-center gap-3 mb-6">
              <button
                onClick={fullReset}
                className="rounded-lg border border-border px-5 py-2.5 text-sm font-medium hover:bg-secondary transition-colors"
              >
                Clear
              </button>
              <button
                onClick={handleAnalyze}
                disabled={!content.trim()}
                className="rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                Analyze
              </button>
            </div>
          )}

          {/* Progress */}
          {isProcessing && (
            <div className="mb-6">
              <ProgressLog
                messages={messages}
                isActive={true}
                onCancel={handleCancel}
              />
            </div>
          )}

          {/* Error */}
          {state === "error" && error && (
            <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 mb-6 text-center">
              <p className="text-sm text-destructive">{error}</p>
              <button
                onClick={reset}
                className="mt-2 text-xs text-muted-foreground hover:text-foreground underline"
              >
                Try again
              </button>
            </div>
          )}

          {/* Report */}
          {state === "done" && result && (
            <ReportRenderer mode={mode} data={result} onReset={fullReset} />
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Index;