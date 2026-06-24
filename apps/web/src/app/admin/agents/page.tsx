/**
 * Agents Page
 *
 * Admin page for managing and monitoring LLM-calling agents.
 */

'use client';

import { useEffect, useMemo, useState } from 'react';
import { useAdminPortalApi } from '@/hooks/useAdminPortalApi';
import { apiClient } from '@/lib/api-client';
import { Download, RefreshCw, Search, X, Loader2, ChevronUp, ChevronDown } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { AdminTableSkeleton } from '@/components/skeleton';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

type AgentRow = {
  agent_id: string;
  agent_label: string;
  description: string;
  category: 'generation' | 'utility' | string;
  calls: number;
  tokens_in: number;
  tokens_out: number;
  tokens_total: number;
  cost_total: number;
  latency_avg_ms: number;
  latency_p95_ms: number;
  error_count: number;
  error_rate: number;
  providers: Record<string, number>;
  models: Record<string, number>;
  feature_tags: Record<string, number>;
  last_seen_at: string | null;
};

type SortKey = 'agent_label' | 'calls' | 'tokens_total' | 'cost_total' | 'latency_avg_ms' | 'latency_p95_ms' | 'error_rate';

const DAY_OPTIONS = [7, 14, 30, 60, 90];

function formatNum(n: number | null | undefined): string {
  return new Intl.NumberFormat('en-US').format(Number(n || 0));
}

function formatPct(v: number | null | undefined): string {
  return `${(Number(v || 0) * 100).toFixed(2)}%`;
}

function formatMoney(v: number | null | undefined): string {
  return `$${Number(v || 0).toFixed(4)}`;
}

function formatMs(v: number | null | undefined): string {
  return `${Number(v || 0).toFixed(1)} ms`;
}

function formatDate(iso?: string | null): string {
  if (!iso) return '-';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? '-' : d.toLocaleString();
}

function deltaClass(v: number | null | undefined): string {
  if (v == null) return 'text-text-tertiary';
  if (v > 0) return 'text-red-500';
  if (v < 0) return 'text-green-500';
  return 'text-text-tertiary';
}

export default function AgentsPage() {
  const { ready } = useAdminPortalApi();
  const [days, setDays] = useState<number>(30);
  const [compareEnabled, setCompareEnabled] = useState<boolean>(true);
  const [compareDays, setCompareDays] = useState<number>(30);
  const [search, setSearch] = useState<string>('');
  const [includeUtility, setIncludeUtility] = useState<boolean>(false);
  const [agentFilter, setAgentFilter] = useState<string>('all');
  const [sortKey, setSortKey] = useState<SortKey>('calls');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<any>(null);
  const [rows, setRows] = useState<AgentRow[]>([]);
  const [series, setSeries] = useState<any[]>([]);
  const [recent, setRecent] = useState<any[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  const fetchAll = async (showSpinner: boolean) => {
    if (!ready) return;
    if (showSpinner) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const [summaryRes, detailRes, tsRes, recentRes] = await Promise.all([
        apiClient.getAgentSummary(days, compareEnabled ? compareDays : 0),
        apiClient.getAgentDetails(days),
        apiClient.getAgentTimeseries(days),
        apiClient.getAgentRecent(80),
      ]);
      setSummary(summaryRes || null);
      setRows((detailRes?.rows || []) as AgentRow[]);
      setSeries(tsRes?.series || []);
      setRecent(recentRes?.rows || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to load agents data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAll(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, days, compareDays, compareEnabled]);

  const filteredRows = useMemo(() => {
    let out = [...rows];
    if (!includeUtility) {
      out = out.filter((r) => r.category === 'generation');
    }
    if (agentFilter !== 'all') {
      out = out.filter((r) => r.agent_id === agentFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      out = out.filter(
        (r) =>
          r.agent_label.toLowerCase().includes(q) ||
          r.agent_id.toLowerCase().includes(q) ||
          (r.description || '').toLowerCase().includes(q)
      );
    }
    out.sort((a, b) => {
      const av: any = a[sortKey];
      const bv: any = b[sortKey];
      if (typeof av === 'string' || typeof bv === 'string') {
        const cmp = String(av).localeCompare(String(bv));
        return sortDir === 'asc' ? cmp : -cmp;
      }
      const cmp = Number(av || 0) - Number(bv || 0);
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return out;
  }, [rows, agentFilter, search, sortKey, sortDir]);

  const selected = useMemo(
    () => filteredRows.find((r) => r.agent_id === selectedAgentId) || null,
    [filteredRows, selectedAgentId]
  );

  const chartData = useMemo(() => {
    return {
      labels: series.map((d: any) => d.date),
      datasets: [
        {
          label: 'Calls',
          data: series.map((d: any) => Number(d.calls || 0)),
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59,130,246,0.15)',
          yAxisID: 'y',
          tension: 0.3,
        },
        {
          label: 'Cost ($)',
          data: series.map((d: any) => Number(d.cost || 0)),
          borderColor: '#10B981',
          backgroundColor: 'rgba(16,185,129,0.15)',
          yAxisID: 'y1',
          tension: 0.3,
        },
      ],
    };
  }, [series]);

  const chartOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#9AA0A6' } } },
    scales: {
      x: { ticks: { color: '#9AA0A6' }, grid: { color: 'rgba(255,255,255,0.04)' } },
      y: { ticks: { color: '#9AA0A6' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y1: { ticks: { color: '#9AA0A6' }, position: 'right', grid: { drawOnChartArea: false } },
    },
  };

  const onSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const exportCsv = async () => {
    try {
      const blob = await apiClient.downloadAgentCsv(days);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `agents_${days}d.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      // no-op: page-level errors already visible via API interceptor
    }
  };

  const allAgentOptions = useMemo(
    () => {
      const source = includeUtility ? rows : rows.filter((r) => r.category === 'generation');
      const uniq = Array.from(new Map(source.map((r) => [r.agent_id, r.agent_label])).entries());
      return [{ id: 'all', label: 'All agents' }, ...uniq.map(([id, label]) => ({ id, label }))];
    },
    [rows, includeUtility]
  );

  if (loading) return <AdminTableSkeleton />;

  return (
    <div className="h-full">
      <div className="mb-6 flex flex-wrap gap-3 items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Agents</h1>
          <p className="text-sm text-text-secondary mt-1">
            Manage and monitor LLM agents in the system
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <select
            className="px-3 py-2 rounded-lg bg-surface border border-border-default text-sm text-text-primary"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            {DAY_OPTIONS.map((d) => (
              <option key={d} value={d}>
                Last {d} days
              </option>
            ))}
          </select>
          <label className="text-xs text-text-secondary flex items-center gap-2 px-2">
            <input
              type="checkbox"
              checked={compareEnabled}
              onChange={(e) => setCompareEnabled(e.target.checked)}
            />
            Compare
          </label>
          <label className="text-xs text-text-secondary flex items-center gap-2 px-2">
            <input
              type="checkbox"
              checked={includeUtility}
              onChange={(e) => {
                setIncludeUtility(e.target.checked);
                setAgentFilter('all');
              }}
            />
            Include utility model calls (embedding, moderation, rerank)
          </label>
          {compareEnabled && (
            <select
              className="px-3 py-2 rounded-lg bg-surface border border-border-default text-sm text-text-primary"
              value={compareDays}
              onChange={(e) => setCompareDays(Number(e.target.value))}
            >
              {DAY_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  Prev {d} days
                </option>
              ))}
            </select>
          )}
          <button
            onClick={() => fetchAll(false)}
            className="px-3 py-2 rounded-lg bg-surface border border-border-default text-sm text-text-primary hover:bg-surface-hover inline-flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={exportCsv}
            className="px-3 py-2 rounded-lg bg-accent-blue text-white text-sm hover:opacity-90 inline-flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-500">
          {error}
        </div>
      )}

      <div className="mb-4 bg-surface rounded-xl border border-border-default p-4 text-sm text-text-secondary">
        <span className="font-medium text-text-primary">How to read this page:</span>{' '}
        <span>Generation agents create text answers/summaries. Utility model calls are support stages like embeddings, rerank, and moderation.</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-4 mb-6">
        <div className="bg-surface rounded-xl border border-border-default p-4">
          <p className="text-xs text-text-secondary">Total Calls</p>
          <p className="text-2xl font-semibold text-text-primary">{formatNum(summary?.totals?.total_calls)}</p>
          <p className={`text-xs ${deltaClass(summary?.deltas?.calls_pct)}`}>
            {summary?.deltas?.calls_pct == null ? '-' : `${summary.deltas.calls_pct.toFixed(2)}% vs previous`}
          </p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-4">
          <p className="text-xs text-text-secondary">Total Cost</p>
          <p className="text-2xl font-semibold text-text-primary">{formatMoney(summary?.totals?.total_cost)}</p>
          <p className={`text-xs ${deltaClass(summary?.deltas?.cost_pct)}`}>
            {summary?.deltas?.cost_pct == null ? '-' : `${summary.deltas.cost_pct.toFixed(2)}% vs previous`}
          </p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-4">
          <p className="text-xs text-text-secondary">Total Tokens</p>
          <p className="text-2xl font-semibold text-text-primary">{formatNum(summary?.totals?.total_tokens)}</p>
          <p className={`text-xs ${deltaClass(summary?.deltas?.tokens_pct)}`}>
            {summary?.deltas?.tokens_pct == null ? '-' : `${summary.deltas.tokens_pct.toFixed(2)}% vs previous`}
          </p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-4">
          <p className="text-xs text-text-secondary">Avg Latency</p>
          <p className="text-2xl font-semibold text-text-primary">{formatMs(summary?.totals?.avg_latency_ms)}</p>
          <p className={`text-xs ${deltaClass(summary?.deltas?.latency_pct)}`}>
            {summary?.deltas?.latency_pct == null ? '-' : `${summary.deltas.latency_pct.toFixed(2)}% vs previous`}
          </p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-4">
          <p className="text-xs text-text-secondary">P95 Latency</p>
          <p className="text-2xl font-semibold text-text-primary">{formatMs(summary?.totals?.p95_latency_ms)}</p>
          <p className="text-xs text-text-tertiary">Across active agents</p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-4">
          <p className="text-xs text-text-secondary">Error Rate</p>
          <p className="text-2xl font-semibold text-text-primary">{formatPct(summary?.totals?.error_rate)}</p>
          <p className="text-xs text-text-tertiary">
            Active agents: {formatNum(summary?.totals?.active_agents)}
          </p>
        </div>
      </div>

      <div className="bg-surface rounded-2xl border border-border-default p-5 mb-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Calls and Cost Trend</h2>
        <div className="h-72">
          <Line data={chartData} options={chartOptions} />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-surface rounded-2xl border border-border-default p-5">
          <div className="flex flex-wrap gap-2 mb-4 items-center">
            <div className="relative">
              <Search className="w-4 h-4 text-text-tertiary absolute left-3 top-2.5" />
              <input
                className="pl-9 pr-3 py-2 rounded-lg bg-surface-hover border border-border-default text-sm text-text-primary"
                placeholder="Search agents..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <select
              className="px-3 py-2 rounded-lg bg-surface-hover border border-border-default text-sm text-text-primary"
              value={agentFilter}
              onChange={(e) => setAgentFilter(e.target.value)}
            >
              {allAgentOptions.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border-default">
                <tr className="text-left text-text-secondary">
                  {[
                    ['agent_label', 'Agent'],
                    ['calls', 'Calls'],
                    ['tokens_total', 'Tokens'],
                    ['cost_total', 'Cost'],
                    ['latency_avg_ms', 'Avg Latency'],
                    ['latency_p95_ms', 'P95'],
                    ['error_rate', 'Error Rate'],
                  ].map(([key, label]) => (
                    <th key={key} className="py-2 pr-4">
                      <button
                        className="inline-flex items-center gap-1 hover:text-text-primary"
                        onClick={() => onSort(key as SortKey)}
                      >
                        {label}
                        {sortKey === key ? (
                          sortDir === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                        ) : null}
                      </button>
                    </th>
                  ))}
                  <th className="py-2 pr-4 text-left">Last Seen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-default">
                {filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-6 text-center text-text-secondary">
                      No agent data for selected filters.
                    </td>
                  </tr>
                ) : (
                  filteredRows.map((r) => (
                    <tr
                      key={r.agent_id}
                      onClick={() => setSelectedAgentId(r.agent_id)}
                      className="hover:bg-surface-hover cursor-pointer"
                    >
                      <td className="py-3 pr-4">
                        <div className="font-medium text-text-primary">{r.agent_label}</div>
                        <div className="text-xs text-text-tertiary flex items-center gap-2">
                          <span>{r.agent_id}</span>
                          <span className={`px-2 py-0.5 rounded ${
                            r.category === 'generation'
                              ? 'bg-blue-500/15 text-blue-400'
                              : 'bg-yellow-500/15 text-yellow-400'
                          }`}>
                            {r.category}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-text-primary">{formatNum(r.calls)}</td>
                      <td className="py-3 pr-4 text-text-primary">{formatNum(r.tokens_total)}</td>
                      <td className="py-3 pr-4 text-text-primary">{formatMoney(r.cost_total)}</td>
                      <td className="py-3 pr-4 text-text-primary">{formatMs(r.latency_avg_ms)}</td>
                      <td className="py-3 pr-4 text-text-primary">{formatMs(r.latency_p95_ms)}</td>
                      <td className="py-3 pr-4 text-text-primary">{formatPct(r.error_rate)}</td>
                      <td className="py-3 pr-4 text-text-secondary">{formatDate(r.last_seen_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-surface rounded-2xl border border-border-default p-5">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Recent Agent Runs</h2>
          <div className="space-y-3 max-h-[560px] overflow-y-auto pr-1">
            {recent.length === 0 ? (
              <p className="text-sm text-text-secondary">No recent runs.</p>
            ) : (
              recent.map((row, idx) => (
                <a
                  key={`${row.trace_id}-${idx}`}
                  href={`/admin/pipeline?trace_id=${encodeURIComponent(row.trace_id)}`}
                  className="block p-3 rounded-lg border border-border-default hover:bg-surface-hover"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-text-primary">{row.agent_id}</p>
                      <p className="text-xs text-text-tertiary">{formatDate(row.timestamp)}</p>
                    </div>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        row.status === 'error' ? 'bg-red-500/15 text-red-500' : 'bg-green-500/15 text-green-500'
                      }`}
                    >
                      {row.status}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary mt-1">{row.agent_name}</p>
                  <p className="text-xs text-text-tertiary mt-1">Duration: {formatMs(row.duration_ms)}</p>
                  {row.error_message ? <p className="text-xs text-red-400 mt-1">{row.error_message}</p> : null}
                </a>
              ))
            )}
          </div>
        </div>
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 bg-black/40 flex justify-end">
          <div className="w-full max-w-xl h-full bg-surface border-l border-border-default p-6 overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-text-primary">{selected.agent_label}</h3>
              <button onClick={() => setSelectedAgentId(null)} className="p-2 rounded hover:bg-surface-hover">
                <X className="w-5 h-5 text-text-secondary" />
              </button>
            </div>
            <p className="text-sm text-text-secondary mb-4">{selected.description}</p>
            <div className="mb-4">
              <span className={`text-xs px-2 py-1 rounded ${
                selected.category === 'generation'
                  ? 'bg-blue-500/15 text-blue-400'
                  : 'bg-yellow-500/15 text-yellow-400'
              }`}>
                {selected.category === 'generation' ? 'Generation agent' : 'Utility model call'}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-5">
              <div className="rounded-lg border border-border-default p-3">
                <p className="text-xs text-text-secondary">Calls</p>
                <p className="text-lg font-semibold text-text-primary">{formatNum(selected.calls)}</p>
              </div>
              <div className="rounded-lg border border-border-default p-3">
                <p className="text-xs text-text-secondary">Cost</p>
                <p className="text-lg font-semibold text-text-primary">{formatMoney(selected.cost_total)}</p>
              </div>
              <div className="rounded-lg border border-border-default p-3">
                <p className="text-xs text-text-secondary">Avg Latency</p>
                <p className="text-lg font-semibold text-text-primary">{formatMs(selected.latency_avg_ms)}</p>
              </div>
              <div className="rounded-lg border border-border-default p-3">
                <p className="text-xs text-text-secondary">P95 Latency</p>
                <p className="text-lg font-semibold text-text-primary">{formatMs(selected.latency_p95_ms)}</p>
              </div>
            </div>

            <h4 className="text-sm font-semibold text-text-primary mb-2">Models</h4>
            <div className="mb-4 space-y-2">
              {Object.keys(selected.models || {}).length === 0 ? (
                <p className="text-sm text-text-secondary">No model usage data.</p>
              ) : (
                Object.entries(selected.models).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">{k}</span>
                    <span className="text-text-primary">{formatNum(v)}</span>
                  </div>
                ))
              )}
            </div>

            <h4 className="text-sm font-semibold text-text-primary mb-2">Providers</h4>
            <div className="mb-4 space-y-2">
              {Object.keys(selected.providers || {}).length === 0 ? (
                <p className="text-sm text-text-secondary">No provider usage data.</p>
              ) : (
                Object.entries(selected.providers).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">{k}</span>
                    <span className="text-text-primary">{formatNum(v)}</span>
                  </div>
                ))
              )}
            </div>

            <h4 className="text-sm font-semibold text-text-primary mb-2">Feature Tags</h4>
            <div className="space-y-2">
              {Object.keys(selected.feature_tags || {}).length === 0 ? (
                <p className="text-sm text-text-secondary">No feature tag data.</p>
              ) : (
                Object.entries(selected.feature_tags).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">{k}</span>
                    <span className="text-text-primary">{formatNum(v)}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}