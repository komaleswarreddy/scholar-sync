/**
 * Pipeline trace debugger — LangGraph nodes + nested retrieval spans.
 */

'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Loader2, RefreshCw, GitBranch } from 'lucide-react';

type SpanRecord = {
  span_id: string;
  name: string;
  parent_span_id: string | null;
  order: number;
  start_ms: number;
  end_ms: number;
  duration_ms: number;
  status: string;
  error_message?: string | null;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  feature_tag?: string | null;
};

type TraceRecord = {
  trace_id: string;
  tenant_id: string;
  user_id: string;
  started_at_ms: number;
  ended_at_ms: number;
  total_duration_ms: number;
  success: boolean;
  spans: SpanRecord[];
};

export default function PipelineTracePage() {
  const { getToken } = useAuth();
  const searchParams = useSearchParams();
  const traceIdFromUrl = searchParams.get('trace_id') || '';

  const [traceId, setTraceId] = useState(traceIdFromUrl);
  const [trace, setTrace] = useState<TraceRecord | null>(null);
  const [recent, setRecent] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SpanRecord | null>(null);
  const [recentScope, setRecentScope] = useState<'mine' | 'all' | null>(null);

  useEffect(() => {
    if (traceIdFromUrl) setTraceId(traceIdFromUrl);
  }, [traceIdFromUrl]);

  const loadTrace = useCallback(async () => {
    if (!getToken || !traceId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      apiClient.setTokenGetter(getToken);
      const data = await apiClient.getPipelineTrace(traceId.trim());
      setTrace(data as TraceRecord);
      setSelected(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load trace');
      setTrace(null);
    } finally {
      setLoading(false);
    }
  }, [getToken, traceId]);

  const loadRecent = useCallback(async () => {
    if (!getToken) return;
    setListLoading(true);
    try {
      apiClient.setTokenGetter(getToken);
      const data = await apiClient.listPipelineTracesRecent(40);
      setRecent(data?.traces || []);
      setRecentScope(data?.scope === 'all' ? 'all' : 'mine');
    } catch {
      setRecent([]);
      setRecentScope(null);
    } finally {
      setListLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (traceId.trim()) loadTrace();
  }, [traceId, loadTrace]);

  useEffect(() => {
    loadRecent();
  }, [loadRecent]);

  const sortedSpans = useMemo(() => {
    if (!trace?.spans?.length) return [];
    return [...trace.spans].sort((a, b) => a.start_ms - b.start_ms || a.order - b.order);
  }, [trace]);

  const displaySpans = useMemo(() => {
    if (!sortedSpans.length) return [];
    const hasChatRetrievalChildren = sortedSpans.some((s) => s.name.startsWith('Retrieval/'));
    const hasStudioRetrievalChildren = sortedSpans.some((s) => s.name.startsWith('StudioRetrieval/'));
    return sortedSpans.filter((s) => {
      // Parent aggregate is recorded with the same wall-clock start as the block but appended last;
      // sorting by start_ms would put it above the real first step (e.g. QueryRewrite). Hide the
      // wrapper when detailed sub-spans exist so order matches backend: QueryRewrite → VectorQuery → Generate.
      if (s.name === 'Retrieval' && hasChatRetrievalChildren) return false;
      if (s.name === 'StudioRetrieval' && hasStudioRetrievalChildren) return false;
      return true;
    });
  }, [sortedSpans]);

  const timeline = useMemo(() => {
    if (!trace || !displaySpans.length) return { total: 1, bars: [] as { span: SpanRecord; left: number; width: number }[] };
    const t0 = trace.started_at_ms;
    const t1 = trace.ended_at_ms || Math.max(...displaySpans.map((s) => s.end_ms));
    const total = Math.max(t1 - t0, 1);
    return {
      total,
      bars: displaySpans.map((span) => ({
        span,
        left: Math.max(((span.start_ms - t0) / total) * 100, 0),
        width: Math.max((span.duration_ms / total) * 100, 0.35),
      })),
    };
  }, [trace, displaySpans]);

  const llmMs = useMemo(() => {
    if (!displaySpans.length) return 0;
    const names = ['Generate', 'DirectChat', 'IntentClassify', 'WholeFileMapReduce'];
    const sub = ['query_rewrite', 'intent_classifier', 'chat_langgraph'];
    return displaySpans
      .filter(
        (s) =>
          names.some((n) => s.name.includes(n)) ||
          sub.some((k) => (s.feature_tag || '').includes(k) || s.name.includes(k))
      )
      .reduce((a, s) => a + s.duration_ms, 0);
  }, [displaySpans]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-start gap-3">
        <GitBranch className="w-8 h-8 text-accent-blue flex-shrink-0 mt-1" />
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Pipeline trace</h1>
          <p className="text-text-secondary text-sm mt-1">
            After each assistant reply, the browser <strong className="text-text-primary font-medium">Console</strong>{' '}
            logs a <code className="text-xs bg-surface px-1 rounded">[Pipeline trace]</code> line with the id; your
            API terminal prints <code className="text-xs bg-surface px-1 rounded">[PIPELINE_TRACE]</code>. Paste the
            UUID here or open the printed link. Recent traces lists your runs on this server process only.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <input
          type="text"
          value={traceId}
          onChange={(e) => setTraceId(e.target.value)}
          placeholder="trace_id (UUID)"
          className="flex-1 min-w-[240px] px-3 py-2 rounded-lg border border-border-default bg-background text-text-primary text-sm"
        />
        <button
          type="button"
          onClick={() => loadTrace()}
          disabled={loading || !traceId.trim()}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-blue text-white text-sm font-medium disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Load
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-red-200 text-sm">{error}</div>
      )}

      {trace && (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-4">
            <div className="p-4 rounded-xl border border-border-default bg-surface/50">
              <div className="flex flex-wrap gap-4 text-sm text-text-secondary mb-2">
                <span>
                  Total: <strong className="text-text-primary">{trace.total_duration_ms.toFixed(0)} ms</strong>
                </span>
                <span>
                  Spans: <strong className="text-text-primary">{displaySpans.length}</strong>
                </span>
                <span>
                  LLM-ish (est.): <strong className="text-text-primary">{llmMs.toFixed(0)} ms</strong>
                </span>
                <span>
                  Status:{' '}
                  <strong className={trace.success ? 'text-green-400' : 'text-amber-400'}>
                    {trace.success ? 'ok' : 'failed'}
                  </strong>
                </span>
              </div>
              <div className="border border-border-default rounded-lg bg-background p-2 space-y-1 max-h-80 overflow-y-auto">
                {timeline.bars.map(({ span, left, width }) => (
                  <div key={span.span_id} className="flex items-center gap-2 text-xs">
                    <span className="w-36 shrink-0 truncate text-text-secondary font-mono" title={span.name}>
                      {span.name.replace('StudioRetrieval/', 'S·').replace('Retrieval/', 'R·')}
                    </span>
                    <div className="flex-1 h-5 bg-surface rounded relative min-w-[120px]">
                      <button
                        type="button"
                        title={span.name}
                        onClick={() => setSelected(span)}
                        className={`absolute top-0.5 h-4 rounded-sm text-[9px] px-1 truncate text-left text-white shadow-sm transition-opacity hover:opacity-90 ${
                          span.status === 'error'
                            ? 'bg-red-500'
                            : span.name.startsWith('Retrieval/') || span.name.startsWith('StudioRetrieval/')
                              ? 'bg-violet-500'
                              : 'bg-emerald-600'
                        }`}
                        style={{ left: `${left}%`, width: `${Math.min(width, 100 - left)}%` }}
                      />
                    </div>
                    <span className="w-14 shrink-0 tabular-nums text-text-secondary">{span.duration_ms.toFixed(0)} ms</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-border-default overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-surface text-text-secondary text-left">
                  <tr>
                    <th className="px-3 py-2">Step</th>
                    <th className="px-3 py-2">ms</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Tag</th>
                  </tr>
                </thead>
                <tbody>
                  {displaySpans.map((s) => (
                    <tr
                      key={s.span_id}
                      className={`border-t border-border-default cursor-pointer hover:bg-surface-hover/50 ${
                        selected?.span_id === s.span_id ? 'bg-accent-blue/10' : ''
                      }`}
                      onClick={() => setSelected(s)}
                    >
                      <td className="px-3 py-2 font-mono text-xs text-text-primary">{s.name}</td>
                      <td className="px-3 py-2 tabular-nums">{s.duration_ms.toFixed(1)}</td>
                      <td className="px-3 py-2">{s.status}</td>
                      <td className="px-3 py-2 text-xs text-text-secondary">{s.feature_tag || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl border border-border-default bg-surface/30 p-4 min-h-[200px]">
            <h4 className="text-sm font-semibold text-text-primary mb-2">Span detail</h4>
            {selected ? (
              <div className="space-y-3 text-xs font-mono overflow-auto max-h-[70vh]">
                {selected.error_message && (
                  <div className="text-red-400">{selected.error_message}</div>
                )}
                <div>
                  <div className="text-text-secondary mb-1">input_summary</div>
                  <pre className="p-2 rounded bg-background border border-border-default whitespace-pre-wrap break-words">
                    {JSON.stringify(selected.input_summary, null, 2)}
                  </pre>
                </div>
                <div>
                  <div className="text-text-secondary mb-1">output_summary</div>
                  <pre className="p-2 rounded bg-background border border-border-default whitespace-pre-wrap break-words">
                    {JSON.stringify(selected.output_summary, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <p className="text-text-secondary text-sm">Select a row or bar.</p>
            )}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-border-default p-4">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 className="text-sm font-semibold text-text-primary">Recent traces</h3>
              <p className="text-xs text-text-secondary mt-0.5">
                {recentScope === 'all'
                  ? 'All users (admin view) — this API process only.'
                  : 'Your chats — this API process only; traces reset on server restart.'}
              </p>
            </div>
            <button
              type="button"
              onClick={loadRecent}
              className="text-xs text-accent-blue flex items-center gap-1"
            >
              {listLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
              Refresh
            </button>
          </div>
          <ul className="text-sm space-y-1">
            {recent.map((t) => (
              <li key={t.trace_id}>
                <button
                  type="button"
                  className="text-accent-blue hover:underline font-mono text-xs"
                  onClick={() => {
                    setTraceId(t.trace_id);
                    setTrace(null);
                  }}
                >
                  {t.trace_id}
                </button>
                <span className="text-text-secondary ml-2">
                  {t.total_duration_ms?.toFixed?.(0)} ms · {t.span_count} spans
                </span>
              </li>
            ))}
            {!recent.length && !listLoading && (
              <li className="text-text-secondary text-xs">No traces in this server process yet.</li>
            )}
          </ul>
        </div>
    </div>
  );
}
