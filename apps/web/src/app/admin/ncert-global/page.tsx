/**
 * Admin: NCERT global corpus — upload (class / subject / optional chapter), list, delete, ingestion run costs.
 */

'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAdminPortalApi } from '@/hooks/useAdminPortalApi';
import { apiClient } from '@/lib/api-client';
import {
  Upload,
  Trash2,
  RefreshCw,
  ChevronRight,
  Loader2,
  BookOpen,
  DollarSign,
} from 'lucide-react';
import { DEFAULT_NCERT_SUBJECTS_BY_CLASS } from '@/config/ncertSubjectsByClass';

type WizardStep = 1 | 2 | 3 | 4;

interface DocRow {
  id: string;
  class_num: number;
  subject: string;
  chapter_no?: number | null;
  chapter_name?: string | null;
  title: string;
  original_filename: string;
  status: string;
  chunks_count: number;
  error_message?: string | null;
  uploaded_by_clerk_user_id: string;
  created_at?: string | null;
}

interface RunRow {
  id: string;
  document_id: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  context_llm_prompt_tokens: number;
  context_llm_completion_tokens: number;
  context_llm_cost_usd: number;
  embedding_prompt_tokens: number;
  embedding_cost_usd: number;
  total_cost_usd: number;
  chunks_processed: number;
  error_message?: string | null;
}

function formatUsd(n: number | undefined | null): string {
  if (n == null || Number.isNaN(n)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(n);
}

export default function NcertGlobalAdminPage() {
  const { ready } = useAdminPortalApi();
  const [mounted, setMounted] = useState(false);
  const [step, setStep] = useState<WizardStep>(1);
  const [classNum, setClassNum] = useState<number | null>(null);
  const [subject, setSubject] = useState<string>('');
  const [chapterNo, setChapterNo] = useState<string>('');
  const [chapterName, setChapterName] = useState('');
  const [title, setTitle] = useState('');
  const [pdfPassword, setPdfPassword] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const [subjectsByClass, setSubjectsByClass] = useState<Record<string, string[]>>(
    () => ({ ...DEFAULT_NCERT_SUBJECTS_BY_CLASS })
  );
  const [documents, setDocuments] = useState<DocRow[]>([]);
  const [listTotal, setListTotal] = useState(0);
  const [listLoading, setListLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runsForDoc, setRunsForDoc] = useState<RunRow[] | null>(null);
  const [runDetail, setRunDetail] = useState<RunRow | null>(null);
  const [runsLoading, setRunsLoading] = useState(false);

  const loadSubjects = useCallback(async () => {
    if (!ready) return;
    try {
      const data = await apiClient.getNcertSubjectsByClass();
      if (data && typeof data === 'object' && Object.keys(data).length > 0) {
        setSubjectsByClass(data as Record<string, string[]>);
      }
    } catch {
      // Backend slow / pool busy / offline — wizard still works from bundled defaults.
      setSubjectsByClass({ ...DEFAULT_NCERT_SUBJECTS_BY_CLASS });
    }
  }, [ready]);

  const loadDocuments = useCallback(async () => {
    if (!ready) return;
    setListLoading(true);
    try {
      const res = await apiClient.listNcertGlobalDocuments({ limit: 500 });
      setDocuments(res.documents || []);
      setListTotal(res.total ?? (res.documents?.length || 0));
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load documents');
    } finally {
      setListLoading(false);
    }
  }, [ready]);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    void loadSubjects();
    void loadDocuments();
  }, [ready, loadSubjects, loadDocuments]);

  const hasProcessing = documents.some((d) => d.status === 'processing');
  useEffect(() => {
    if (!hasProcessing || !ready) return;
    const t = setInterval(() => void loadDocuments(), 10000);
    return () => clearInterval(t);
  }, [hasProcessing, ready, loadDocuments]);

  const subjectsForClass =
    classNum != null ? subjectsByClass[String(classNum)] || subjectsByClass[classNum as unknown as string] || [] : [];

  const resetWizard = () => {
    setStep(1);
    setClassNum(null);
    setSubject('');
    setChapterNo('');
    setChapterName('');
    setTitle('');
    setPdfPassword('');
    setFile(null);
    setError(null);
  };

  const handleUpload = async () => {
    if (!ready || classNum == null || !subject || !file) {
      setError('Complete all steps and choose a PDF.');
      return;
    }
    setUploading(true);
    setError(null);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('class_num', String(classNum));
    fd.append('subject', subject);
    fd.append('title', title.trim() || file.name);
    const cn = chapterNo.trim();
    if (cn) fd.append('chapter_no', cn);
    if (chapterName.trim()) fd.append('chapter_name', chapterName.trim());
    if (pdfPassword) fd.append('pdf_password', pdfPassword);
    try {
      await apiClient.uploadNcertGlobalDocument(fd);
      resetWizard();
      await loadDocuments();
    } catch (e: any) {
      const d = e?.response?.data?.detail;
      setError(typeof d === 'string' ? d : e?.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!ready) return;
    if (!confirm('Delete this NCERT document, its storage file, and all Pinecone vectors for it?')) return;
    try {
      await apiClient.deleteNcertGlobalDocument(id);
      await loadDocuments();
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Delete failed');
    }
  };

  const openRuns = async (documentId: string) => {
    if (!ready) return;
    setRunsLoading(true);
    setRunsForDoc([]);
    setRunDetail(null);
    try {
      const res = await apiClient.listNcertGlobalIngestionRuns({ document_id: documentId, limit: 50 });
      setRunsForDoc(res.runs || []);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load runs');
    } finally {
      setRunsLoading(false);
    }
  };

  const openRunDetail = async (runId: string) => {
    if (!ready) return;
    try {
      const r = await apiClient.getNcertGlobalIngestionRun(runId);
      setRunDetail(r as RunRow);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load run');
    }
  };

  if (!mounted || !ready) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="w-8 h-8 animate-spin text-text-tertiary" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary flex items-center gap-2">
          <BookOpen className="w-7 h-7 text-accent-blue" />
          NCERT global library
        </h1>
        <p className="text-text-secondary text-sm mt-1">
          Uploads go to Supabase <code className="text-xs bg-surface-subtle px-1 rounded">global/ncert/</code> and
          Pinecone namespace <code className="text-xs bg-surface-subtle px-1 rounded">NcertDataGlobal</code>.
        </p>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-100 text-red-800 text-sm">{error}</div>
      )}

      {/* Wizard */}
      <section className="rounded-2xl border border-border-default bg-surface p-6 space-y-6">
        <h2 className="text-lg font-medium text-text-primary">New upload</h2>

        <div className="flex flex-wrap gap-2 text-xs font-medium text-text-tertiary">
          {[1, 2, 3, 4].map((s) => (
            <span
              key={s}
              className={`px-2 py-1 rounded-md ${step === s ? 'bg-accent-blue/15 text-accent-blue' : 'bg-surface-subtle'}`}
            >
              {s}. {s === 1 ? 'Class' : s === 2 ? 'Subject' : s === 3 ? 'Chapter (optional)' : 'PDF & title'}
            </span>
          ))}
        </div>

        {step === 1 && (
          <div className="space-y-3">
            <p className="text-sm text-text-secondary">Select class (Class 12 only)</p>
            <div className="flex flex-wrap gap-2">
              {[12].map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => {
                    setClassNum(c);
                    setSubject('');
                    setStep(2);
                  }}
                  className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                    classNum === c
                      ? 'border-accent-blue bg-accent-blue/10 text-accent-blue'
                      : 'border-border-default hover:bg-surface-hover'
                  }`}
                >
                  Class {c}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 2 && classNum != null && (
          <div className="space-y-3">
            <button type="button" onClick={() => setStep(1)} className="text-xs text-accent-blue">
              ← Back
            </button>
            <p className="text-sm text-text-secondary">Class {classNum} — choose subject</p>
            <div className="flex flex-wrap gap-2">
              {subjectsForClass.map((sub) => (
                <button
                  key={sub}
                  type="button"
                  onClick={() => {
                    setSubject(sub);
                    setStep(3);
                  }}
                  className={`px-3 py-2 rounded-lg border text-sm capitalize ${
                    subject === sub
                      ? 'border-accent-blue bg-accent-blue/10 text-accent-blue'
                      : 'border-border-default hover:bg-surface-hover'
                  }`}
                >
                  {sub.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
            {subjectsForClass.length === 0 && (
              <p className="text-sm text-amber-700">No subjects loaded. Check admin access and config.</p>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4 max-w-md">
            <button type="button" onClick={() => setStep(2)} className="text-xs text-accent-blue">
              ← Back
            </button>
            <p className="text-sm text-text-secondary">Optional chapter metadata (stored on every chunk)</p>
            <label className="block text-sm">
              <span className="text-text-secondary">Chapter number</span>
              <input
                type="number"
                min={1}
                className="mt-1 w-full rounded-lg border border-border-default bg-background px-3 py-2 text-sm"
                value={chapterNo}
                onChange={(e) => setChapterNo(e.target.value)}
                placeholder="e.g. 5"
              />
            </label>
            <label className="block text-sm">
              <span className="text-text-secondary">Chapter name</span>
              <input
                className="mt-1 w-full rounded-lg border border-border-default bg-background px-3 py-2 text-sm"
                value={chapterName}
                onChange={(e) => setChapterName(e.target.value)}
                placeholder="e.g. Acids, Bases and Salts"
              />
            </label>
            <button
              type="button"
              onClick={() => setStep(4)}
              className="flex items-center gap-1 text-sm font-medium text-accent-blue"
            >
              Continue <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4 max-w-lg">
            <button type="button" onClick={() => setStep(3)} className="text-xs text-accent-blue">
              ← Back
            </button>
            <label className="block text-sm">
              <span className="text-text-secondary">Display title</span>
              <input
                className="mt-1 w-full rounded-lg border border-border-default bg-background px-3 py-2 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Defaults to filename"
              />
            </label>
            <label className="block text-sm">
              <span className="text-text-secondary">PDF file</span>
              <input
                type="file"
                accept=".pdf,application/pdf"
                className="mt-1 w-full text-sm"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <label className="block text-sm">
              <span className="text-text-secondary">PDF password (if encrypted)</span>
              <input
                type="password"
                className="mt-1 w-full rounded-lg border border-border-default bg-background px-3 py-2 text-sm"
                value={pdfPassword}
                onChange={(e) => setPdfPassword(e.target.value)}
                autoComplete="off"
              />
            </label>
            <button
              type="button"
              disabled={uploading || !file || classNum == null || !subject}
              onClick={() => void handleUpload()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-blue text-white text-sm font-medium disabled:opacity-50"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              Upload &amp; ingest
            </button>
          </div>
        )}
      </section>

      {/* Table */}
      <section className="rounded-2xl border border-border-default bg-surface overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border-default">
          <h2 className="text-lg font-medium text-text-primary">Documents ({listTotal})</h2>
          <button
            type="button"
            onClick={() => void loadDocuments()}
            className="p-2 rounded-lg border border-border-default hover:bg-surface-hover"
            aria-label="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${listLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-subtle text-text-secondary text-left">
              <tr>
                <th className="px-4 py-2 font-medium">Class</th>
                <th className="px-4 py-2 font-medium">Subject</th>
                <th className="px-4 py-2 font-medium">Chapter</th>
                <th className="px-4 py-2 font-medium">Title</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Chunks</th>
                <th className="px-4 py-2 font-medium">Uploaded</th>
                <th className="px-4 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {listLoading && documents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-text-tertiary">
                    <Loader2 className="w-6 h-6 animate-spin inline" />
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-text-tertiary">
                    No NCERT global documents yet.
                  </td>
                </tr>
              ) : (
                documents.map((d) => (
                  <tr key={d.id} className="border-t border-border-default hover:bg-surface-hover/50">
                    <td className="px-4 py-2">{d.class_num}</td>
                    <td className="px-4 py-2 capitalize">{d.subject.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-2">
                      {d.chapter_no != null ? `Ch. ${d.chapter_no}` : '—'}
                      {d.chapter_name ? ` ${d.chapter_name}` : ''}
                    </td>
                    <td className="px-4 py-2 max-w-[200px] truncate" title={d.title}>
                      {d.title}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={
                          d.status === 'indexed'
                            ? 'text-green-700'
                            : d.status === 'processing'
                              ? 'text-amber-700'
                              : 'text-red-700'
                        }
                      >
                        {d.status}
                      </span>
                      {d.error_message && (
                        <span className="block text-xs text-red-600 truncate max-w-[140px]" title={d.error_message}>
                          {d.error_message}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2">{d.chunks_count}</td>
                    <td className="px-4 py-2 text-text-tertiary whitespace-nowrap">
                      {d.created_at ? new Date(d.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-2 whitespace-nowrap space-x-2">
                      <button
                        type="button"
                        className="text-accent-blue text-xs font-medium"
                        onClick={() => void openRuns(d.id)}
                      >
                        Runs
                      </button>
                      <button
                        type="button"
                        className="text-red-600 text-xs font-medium inline-flex items-center gap-1"
                        onClick={() => void handleDelete(d.id)}
                      >
                        <Trash2 className="w-3 h-3" /> Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Runs panel */}
      {runsForDoc !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
          role="dialog"
          onClick={(e) => e.target === e.currentTarget && setRunsForDoc(null)}
        >
          <div className="bg-surface rounded-2xl border border-border-default max-w-lg w-full max-h-[80vh] overflow-hidden flex flex-col shadow-xl">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border-default">
              <h3 className="font-medium text-text-primary">Ingestion runs</h3>
              <button type="button" className="text-sm text-text-secondary" onClick={() => setRunsForDoc(null)}>
                Close
              </button>
            </div>
            <div className="p-4 overflow-y-auto space-y-2">
              {runsLoading ? (
                <Loader2 className="w-6 h-6 animate-spin mx-auto" />
              ) : (runsForDoc || []).length === 0 ? (
                <p className="text-text-secondary text-sm">No runs found.</p>
              ) : (
                (runsForDoc || []).map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => void openRunDetail(r.id)}
                    className="w-full text-left p-3 rounded-lg border border-border-default hover:bg-surface-hover flex justify-between gap-2"
                  >
                    <span className="text-sm font-mono truncate">{r.id}</span>
                    <span className="text-xs text-text-secondary shrink-0">{r.status}</span>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {runDetail && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/40"
          role="dialog"
          onClick={(e) => e.target === e.currentTarget && setRunDetail(null)}
        >
          <div className="bg-surface rounded-2xl border border-border-default max-w-md w-full shadow-xl p-6 space-y-4">
            <div className="flex items-center gap-2 text-text-primary font-medium">
              <DollarSign className="w-5 h-5 text-accent-blue" />
              Run cost breakdown
            </div>
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="text-text-secondary">Status</dt>
              <dd>{runDetail.status}</dd>
              <dt className="text-text-secondary">Chunks</dt>
              <dd>{runDetail.chunks_processed}</dd>
              <dt className="text-text-secondary">Context LLM (prompt tok)</dt>
              <dd>{runDetail.context_llm_prompt_tokens}</dd>
              <dt className="text-text-secondary">Context LLM (completion tok)</dt>
              <dd>{runDetail.context_llm_completion_tokens}</dd>
              <dt className="text-text-secondary">Context LLM cost</dt>
              <dd>{formatUsd(runDetail.context_llm_cost_usd)}</dd>
              <dt className="text-text-secondary">Embedding (tok)</dt>
              <dd>{runDetail.embedding_prompt_tokens}</dd>
              <dt className="text-text-secondary">Embedding cost</dt>
              <dd>{formatUsd(runDetail.embedding_cost_usd)}</dd>
              <dt className="text-text-secondary font-semibold">Total</dt>
              <dd className="font-semibold">{formatUsd(runDetail.total_cost_usd)}</dd>
            </dl>
            {runDetail.error_message && (
              <p className="text-xs text-red-600">{runDetail.error_message}</p>
            )}
            <button
              type="button"
              className="w-full py-2 rounded-lg border border-border-default text-sm font-medium"
              onClick={() => setRunDetail(null)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
