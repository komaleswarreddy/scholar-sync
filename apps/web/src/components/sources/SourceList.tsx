/**
 * Source List Component 
 * Implementation of Sections A-E:
 * - A: Duplicate checks
 * - B: Size/Type validation
 * - C: Upload progress
 * - D: Selection persistence & count
 * - E: Deletion with confirmation, loading states, and error handling
 */

'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { Checkbox } from '../ui/Checkbox';
import { Button } from '../ui/Button';
import { FileText, Plus, X, Loader2, AlertCircle, CheckCircle2, Trash2, File, Globe, FileType, ExternalLink, ChevronRight } from 'lucide-react';
import { useUploadSource, useDeleteSource } from '@/hooks/useSources';
import { useCombinedSources } from '@/hooks/useCombinedSources';
import { useSourceContext } from '@/contexts/SourceContext';
import { useNotebookScopeId } from '@/contexts/NotebookContext';
import { SourceItemSkeleton } from './SourceItemSkeleton';
import { getSourceToneStyle } from '@/lib/notebook-ui-tokens';
import {
  extractNcertDocumentIdFromVirtualSource,
  isVirtualNcertSourceId,
  ncertDocumentFileUrl,
} from '@/lib/tutor-ncert-source';

type SourceListVariant = 'dashboard' | 'notebook';

interface SourceListProps {
  variant?: SourceListVariant;
  onOpenQuestionPaper?: (source: { id: string; title: string }) => void;
}

interface Source {
  id: string;
  title: string;
  type?: 'pdf' | 'text' | 'url' | string;
  file_type?: string; // API might return file_type
  status: 'processing' | 'indexed' | 'error' | 'completed' | 'failed';
  created_at?: string;
  chunks_count?: number;
  error_message?: string;
}

// Helper function to get file type icon and color
function getFileTypeIcon(type?: string) {
  const normalizedType = type?.toLowerCase();
  
  if (normalizedType === 'pdf' || normalizedType?.includes('pdf')) {
    return {
      icon: FileText,
      color: 'text-red-500',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/20',
    };
  }
  
  if (normalizedType === 'url' || normalizedType?.includes('url') || normalizedType?.includes('http')) {
    return {
      icon: Globe,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/20',
    };
  }
  
  // Default to text file
  return {
    icon: FileType,
    color: 'text-accent-blue',
    bgColor: 'bg-accent-blue/10',
    borderColor: 'border-accent-blue/20',
  };
}

export function SourceList({ variant = 'dashboard', onOpenQuestionPaper }: SourceListProps) {
  const isNotebook = variant === 'notebook';
  const notebookId = useNotebookScopeId();
  const { displaySources, isLoading, isError, error: apiError } = useCombinedSources(notebookId);
  const {
    selectedSources,
    toggleSource,
    removeSource,
    clearSelection,
    queueUploadAutoSummary,
    setSelectedSources,
  } = useSourceContext();

  const [uploadProgress, setUploadProgress] = useState(0);
  const [localError, setLocalError] = useState<string | null>(null);
  const [pdfPassword, setPdfPassword] = useState<string>('');
  const [showPasswordInput, setShowPasswordInput] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [passwordAttempts, setPasswordAttempts] = useState(0);
  const MAX_PASSWORD_ATTEMPTS = 3;
  
  // Task E.c: State to track which specific item is being deleted
  const [deletingId, setDeletingId] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Drop IDs that are no longer in the library (deleted docs, stale localStorage).
  useEffect(() => {
    if (isLoading && displaySources.length === 0) return;
    const validIds = new Set(
      displaySources.map((s) => String(s.id).trim()).filter((id) => id.length > 0)
    );
    setSelectedSources((prev) => {
      const next = new Set<string>();
      for (const raw of prev) {
        const id = String(raw).trim();
        if (id && validIds.has(id)) next.add(id);
      }
      if (next.size === prev.size) {
        for (const raw of prev) {
          if (!next.has(String(raw).trim())) return next;
        }
        return prev;
      }
      return next;
    });
  }, [displaySources, isLoading, setSelectedSources]);

  const selectedCountInLibrary = useMemo(() => {
    const valid = new Set(
      displaySources.map((s) => String(s.id).trim()).filter((id) => id.length > 0)
    );
    const seen = new Set<string>();
    for (const raw of selectedSources) {
      const id = String(raw).trim();
      if (id && valid.has(id)) seen.add(id);
    }
    return seen.size;
  }, [displaySources, selectedSources]);
  /** Only show fetch banner when the list is empty — background refetch failures keep cached sources visible. */
  const showSourcesFetchError = Boolean(isError && apiError && displaySources.length === 0);
  const uploadMutation = useUploadSource(notebookId);
  const deleteMutation = useDeleteSource(notebookId);

  // Task C.a: Loading state from TanStack Query
  const loading = isLoading;
  const isUploading = uploadMutation.isPending;

  const handleUpload = () => {
    setLocalError(null);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const isAlreadyConnected = displaySources.some(
      (s) => s.title.toLowerCase() === file.name.toLowerCase()
    );
    if (isAlreadyConnected) {
      setLocalError("This file is already connected.");
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    const MAX_SIZE = 10 * 1024 * 1024;
    const allowedExtensions = ['.pdf', '.txt', '.png', '.jpg', '.jpeg', '.webp', '.gif'];
    const hasValidExtension = allowedExtensions.some(ext => 
      file.name.toLowerCase().endsWith(ext)
    );
    
    if (!hasValidExtension) {
      setLocalError("Only PDF, TXT, and image files (PNG, JPG, WEBP) are supported.");
      return;
    }

    if (file.size > MAX_SIZE) {
      setLocalError("File limit is 10MB.");
      return;
    }

    // Try uploading immediately (without password first)
    await performUpload(file, '');
  };

  const performUpload = async (file: File, password: string, isRetry: boolean = false) => {
    setUploadProgress(0);
    if (!isRetry) {
      setLocalError(null);
    }

    try {
      // Task C.a: Use TanStack Query mutation with loading state
      const uploadResult = await uploadMutation.mutateAsync({
        file,
        title: file.name,
        pdfPassword: password || undefined,
        onProgress: (percent) => {
          setUploadProgress(percent);
        },
      });

      if (uploadResult && typeof uploadResult === 'object' && 'id' in uploadResult && uploadResult.id) {
        queueUploadAutoSummary(String(uploadResult.id));
      }

      // Reset state on success
      if (fileInputRef.current) fileInputRef.current.value = '';
      setShowPasswordInput(false);
      setSelectedFile(null);
      setPdfPassword('');
      setPasswordAttempts(0);
      setLocalError(null);
    } catch (err: any) {
      const errorMessage = err.message || "Upload failed.";
      
      // Check if error is about password-protected PDF
      const isPasswordError = errorMessage.toLowerCase().includes('password-protected') || 
                             errorMessage.toLowerCase().includes('encrypted') ||
                             errorMessage.toLowerCase().includes('password') ||
                             errorMessage.toLowerCase().includes('incorrect password');
      
      if (isPasswordError && !password) {
        // PDF is password-protected and no password was provided
        // Show password input dialog (first attempt)
        setSelectedFile(file);
        setShowPasswordInput(true);
        setPdfPassword('');
        setPasswordAttempts(0);
        setLocalError("This PDF is password-protected. Please enter the password to continue.");
      } else if (isPasswordError && password) {
        // Password was provided but incorrect
        const newAttempts = passwordAttempts + 1;
        setPasswordAttempts(newAttempts);
        
        if (newAttempts >= MAX_PASSWORD_ATTEMPTS) {
          // Max attempts reached - fail the upload
          setLocalError(`Upload failed: Incorrect password after ${MAX_PASSWORD_ATTEMPTS} attempts. Please verify the password and try again.`);
          setShowPasswordInput(false);
          setSelectedFile(null);
          setPdfPassword('');
          setPasswordAttempts(0);
          if (fileInputRef.current) fileInputRef.current.value = '';
        } else {
          // Still have attempts left - show error and keep dialog open
          const remaining = MAX_PASSWORD_ATTEMPTS - newAttempts;
          setLocalError(`Incorrect password. ${remaining} attempt${remaining > 1 ? 's' : ''} remaining.`);
          setPdfPassword(''); // Clear password field for retry
          setShowPasswordInput(true);
        }
      } else {
        // Other errors (not password-related)
        setLocalError(errorMessage);
        setShowPasswordInput(false);
        setSelectedFile(null);
        setPdfPassword('');
        setPasswordAttempts(0);
      }
    } finally {
      setUploadProgress(0);
    }
  };

  const handlePasswordConfirm = () => {
    if (selectedFile && pdfPassword.trim()) {
      // Clear error message but keep dialog open in case of retry
      performUpload(selectedFile, pdfPassword, true);
    }
  };

  const handlePasswordCancel = () => {
    setShowPasswordInput(false);
    setSelectedFile(null);
    setPdfPassword('');
    setPasswordAttempts(0);
    setLocalError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Task E: Optimized Deletion Flow with TanStack Query
  const handleDelete = async (sourceId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (isVirtualNcertSourceId(sourceId)) return;
    // Task E.a & E.b: Confirmation logic
    const confirmed = window.confirm(
      "Are you sure you want to delete this source? This will remove all processed data and cannot be undone."
    );
    if (!confirmed) return;

    // Task E.c: Set loading state
    setDeletingId(sourceId);
    setLocalError(null);

    try {
      // Task C.c: Optimistic update handled by TanStack Query
      await deleteMutation.mutateAsync(sourceId);
      
      // Task E.e: Clean selection context
      removeSource(sourceId);
    } catch (err: any) {
      // Task E.d: Graceful error handling
      setLocalError(err.message || "Failed to delete source.");
    } finally {
      setDeletingId(null);
    }
  };

  const renderSourceRow = (source: Source) => {
    const sourceKey = String(source.id).trim();
    const isSelected = [...selectedSources].some((x) => String(x).trim() === sourceKey);
    const isDeleting = deletingId === source.id;
    const isVirtual = isVirtualNcertSourceId(source.id);
    const ncertDocId = isVirtual ? extractNcertDocumentIdFromVirtualSource(source.id) : null;
    const sourceType =
      source.type ||
      source.file_type ||
      (source.title?.toLowerCase().endsWith('.pdf')
        ? 'pdf'
        : source.title?.toLowerCase().endsWith('.txt')
          ? 'text'
          : 'text');
    const mappedStatus =
      source.status === 'completed'
        ? 'indexed'
        : source.status === 'failed'
          ? 'error'
          : source.status;

    if (isNotebook) {
      const toneStyle = getSourceToneStyle(sourceType);
      const ToneIcon = toneStyle.Icon;
      return (
        <li
          key={source.id}
          className={`notebook-source-item group cursor-pointer ${isSelected ? 'border-[rgba(15,122,82,0.35)] bg-[var(--color-brand-surface)]' : ''} ${isDeleting ? 'opacity-50 pointer-events-none' : ''}`}
          onClick={() => !isDeleting && toggleSource(source.id)}
        >
          <div onClick={(e) => e.stopPropagation()} role="presentation">
            <Checkbox
              checked={isSelected}
              onChange={() => toggleSource(source.id)}
              disabled={isDeleting}
            />
          </div>
          <div
            className="notebook-source-icon"
            style={{ backgroundColor: toneStyle.bg, color: toneStyle.color }}
          >
            <ToneIcon className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-semibold text-[var(--color-home-text)] truncate">
              {source.title}
            </p>
            <div className="flex items-center gap-2 mt-1">
              {isVirtual ? (
                <span className="text-[10px] font-semibold uppercase text-[var(--color-brand-text)]">
                  NCERT
                </span>
              ) : null}
              {mappedStatus === 'processing' && (
                <span className="text-[10px] font-semibold uppercase text-blue-600 flex items-center gap-1">
                  <Loader2 className="w-2.5 h-2.5 animate-spin" /> processing
                </span>
              )}
              {mappedStatus === 'indexed' && (
                <span className="text-[10px] font-semibold uppercase text-[var(--color-brand-text)]">
                  ready
                </span>
              )}
              {mappedStatus === 'error' && (
                <span className="text-[10px] font-semibold uppercase text-red-600">error</span>
              )}
              <span className="text-[11px] text-[var(--color-home-label)]">
                {isVirtual && source.chunks_count == null
                  ? 'Loading index…'
                  : `${source.chunks_count ?? 0} chunks`}
              </span>
            </div>
            {mappedStatus === 'error' && source.error_message && (
              <p className="text-[11px] text-red-600 mt-1 leading-snug">{source.error_message}</p>
            )}
            {ncertDocId ? (
              <a
                href={ncertDocumentFileUrl(ncertDocId)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 mt-1.5 text-[11px] font-medium text-[var(--color-brand-text)] hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                View PDF
                <ExternalLink className="w-3 h-3" />
              </a>
            ) : null}
            {onOpenQuestionPaper &&
            !isVirtual &&
            mappedStatus === 'indexed' &&
            (sourceType === 'pdf' || source.title?.toLowerCase().endsWith('.pdf')) ? (
              <button
                type="button"
                className="inline-flex items-center gap-1 mt-1.5 text-[11px] font-semibold text-[var(--color-brand-text)] hover:underline"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenQuestionPaper({ id: source.id, title: source.title });
                }}
              >
                Browse questions
                <ChevronRight className="w-3 h-3" />
              </button>
            ) : null}
          </div>
          {!isVirtual ? (
          <button
            type="button"
            onClick={(e) => handleDelete(source.id, e)}
            disabled={isDeleting}
            className="p-1.5 rounded-lg text-[var(--color-home-label)] hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
            title="Delete source"
            aria-label="Delete source"
          >
            {isDeleting ? (
              <Loader2 className="w-4 h-4 animate-spin text-red-500" />
            ) : (
              <Trash2 className="w-4 h-4" />
            )}
          </button>
          ) : null}
        </li>
      );
    }

    const fileType = getFileTypeIcon(sourceType);
    const IconComponent = fileType.icon;

    return (
      <div
        key={source.id}
        className={`flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-all group relative
          ${isSelected
            ? 'bg-surface-hover border-2 border-accent-blue shadow-sm'
            : 'border border-transparent hover:bg-surface-hover hover:border-border-default hover:shadow-sm'
          }
          ${isDeleting ? 'opacity-50 pointer-events-none' : ''}
        `}
        onClick={() => !isDeleting && toggleSource(source.id)}
      >
        <div
          className="mt-0.5 flex-shrink-0"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
          role="presentation"
        >
          <Checkbox
            checked={isSelected}
            onChange={() => toggleSource(source.id)}
            disabled={isDeleting}
          />
        </div>
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-lg ${fileType.bgColor} border ${fileType.borderColor} flex items-center justify-center mt-0.5`}
        >
          <IconComponent className={`w-4 h-4 ${fileType.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            {isVirtual && (
              <span className="text-xs font-bold uppercase bg-green-500/10 text-green-600 px-1.5 py-0.5 rounded border border-green-500/20">
                NCERT
              </span>
            )}
            {mappedStatus === 'processing' && (
              <span className="text-xs font-bold uppercase bg-blue-500/10 text-blue-500 px-1.5 py-0.5 rounded flex items-center gap-1 border border-blue-500/20">
                <Loader2 className="w-2.5 h-2.5 animate-spin" /> processing
              </span>
            )}
            {mappedStatus === 'indexed' && (
              <span className="text-xs font-bold uppercase bg-green-500/10 text-green-500 px-1.5 py-0.5 rounded flex items-center gap-1 border border-green-500/20">
                <CheckCircle2 className="w-2.5 h-2.5" /> ready
              </span>
            )}
            {mappedStatus === 'error' && (
              <span className="text-xs font-bold uppercase bg-red-500/10 text-red-500 px-1.5 py-0.5 rounded flex items-center gap-1 border border-red-500/20">
                <AlertCircle className="w-2.5 h-2.5" /> error
              </span>
            )}
          </div>
          <p
            className={`text-sm font-semibold truncate mb-1 ${isSelected ? 'text-text-primary' : 'text-text-secondary'}`}
          >
            {source.title}
          </p>
          {mappedStatus === 'error' && source.error_message && (
            <div className="mt-1.5 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-xs text-red-600 leading-relaxed">{source.error_message}</p>
            </div>
          )}
          {ncertDocId ? (
            <a
              href={ncertDocumentFileUrl(ncertDocId)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-1.5 text-xs font-medium text-accent-blue hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              View PDF
              <ExternalLink className="w-3 h-3" />
            </a>
          ) : null}
          <div className="flex items-center gap-2 mt-1.5">
            <p className="text-xs font-medium text-text-tertiary">{source.chunks_count || 0} chunks</p>
            <span className="text-text-tertiary text-xs">•</span>
            <p className="text-xs font-medium text-text-tertiary">
              {source.created_at
                ? new Date(source.created_at).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                  })
                : 'Just now'}
            </p>
          </div>
        </div>
        {!isVirtual ? (
        <button
          onClick={(e) => handleDelete(source.id, e)}
          disabled={isDeleting}
          className={`p-1.5 rounded-lg transition-all flex-shrink-0
            ${isDeleting
              ? 'opacity-100'
              : 'opacity-0 group-hover:opacity-100 text-text-tertiary hover:text-red-500 hover:bg-red-500/10'
            }`}
          title="Delete source"
          aria-label="Delete source"
        >
          {isDeleting ? (
            <Loader2 className="w-4 h-4 animate-spin text-red-500" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
        </button>
        ) : null}
      </div>
    );
  };

  const uploadControls = (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,.gif,image/*"
        onChange={handleFileChange}
        className="hidden"
      />
      {showPasswordInput && selectedFile && (
        <div
          className={`mb-3 p-3 rounded-lg border ${isNotebook ? 'border-[var(--color-home-border)] bg-[#FAFBFA]' : 'bg-surface-hover border-border-default'}`}
        >
          <div className="flex items-start gap-2 mb-2">
            <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className={`text-sm font-medium ${isNotebook ? 'text-[var(--color-home-text)]' : 'text-text-primary'} mb-1`}>
                Password Required
              </p>
              <p className={`text-xs ${isNotebook ? 'text-[var(--color-home-text-muted)]' : 'text-text-secondary'}`}>
                This PDF is password-protected. Please enter the password to continue.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <input
              type="password"
              value={pdfPassword}
              onChange={(e) => setPdfPassword(e.target.value)}
              placeholder="Enter PDF password"
              className="flex-1 px-3 py-2 text-sm border border-border-default rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-blue/50"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && pdfPassword.trim()) handlePasswordConfirm();
                else if (e.key === 'Escape') handlePasswordCancel();
              }}
              autoFocus
            />
            <Button variant="primary" size="sm" onClick={handlePasswordConfirm} disabled={isUploading || !pdfPassword.trim()}>
              {isUploading ? 'Uploading...' : 'Try'}
            </Button>
            <Button variant="secondary" size="sm" onClick={handlePasswordCancel} disabled={isUploading}>
              Cancel
            </Button>
          </div>
        </div>
      )}
      {(localError || showSourcesFetchError) && (
        <div className="mb-3 p-2.5 rounded-xl bg-red-50 border border-red-200 flex items-start gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-red-600 mt-0.5" />
          <p className="text-xs text-red-700 flex-1 leading-relaxed">
            {localError ||
              (typeof apiError === 'string'
                ? apiError
                : apiError?.message || apiError?.toString() || 'An error occurred')}
          </p>
          <button type="button" onClick={() => setLocalError(null)} className="cursor-pointer hover:opacity-70">
            <X className="w-3.5 h-3.5 text-red-400" />
          </button>
        </div>
      )}
      {isUploading && (
        <div className="mb-3 space-y-1">
          <div className="flex justify-between text-xs font-medium">
            <span className="flex items-center gap-1.5">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--color-brand-text)]" />
              Uploading…
            </span>
            <span>{uploadProgress}%</span>
          </div>
          <div className="w-full h-1.5 bg-[var(--color-home-border)] rounded-full overflow-hidden">
            <div className="h-full bg-[var(--color-brand-primary)] transition-all" style={{ width: `${uploadProgress}%` }} />
          </div>
        </div>
      )}
    </>
  );

  if (isNotebook) {
    return (
      <div className="flex flex-col h-full min-h-0 flex-1">
        <div className="notebook-col-header px-4 pt-1">
          <span>SOURCES</span>
          <div className="flex items-center gap-3">
            {selectedCountInLibrary > 0 && (
              <button type="button" onClick={clearSelection} className="notebook-link-btn text-[11px]">
                Deselect
              </button>
            )}
            <button
              type="button"
              className="notebook-link-btn"
              onClick={handleUpload}
              disabled={isUploading || loading || showPasswordInput}
            >
              + Upload
            </button>
          </div>
        </div>
        <div className="px-4 pb-2">{uploadControls}</div>
        <div className="notebook-source-list--scroll px-3 pb-2">
          {loading && displaySources.length === 0 ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <SourceItemSkeleton key={i} />
              ))}
            </div>
          ) : displaySources.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-[13px] font-semibold text-[var(--color-home-text)]">No sources yet</p>
              <p className="text-[12px] text-[var(--color-home-text-muted)] mt-1 mb-3">
                Upload PDF or text files to start
              </p>
              <button type="button" className="notebook-link-btn" onClick={handleUpload}>
                + Add your first source
              </button>
            </div>
          ) : (
            <ul className="notebook-source-list">{displaySources.map((source) => renderSourceRow(source))}</ul>
          )}
        </div>
        {displaySources.length > 0 && (
          <p className="px-4 pb-2 text-[11px] text-[var(--color-home-label)] flex-shrink-0">
            {selectedCountInLibrary} selected · {displaySources.length} total
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-surface border-r border-border-default">
      <div className="h-14 flex items-center px-4 border-b border-border-default">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-text-primary" />
            <h2 className="text-lg font-bold text-text-primary tracking-tight">Sources</h2>
          </div>
          {selectedCountInLibrary > 0 && (
            <button 
              onClick={clearSelection}
              className="text-xs font-medium text-text-tertiary hover:text-text-primary transition-colors"
            >
              Deselect all
            </button>
          )}
        </div>
      </div>

      <div className="p-4 border-b border-border-default">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,.gif,image/*"
          onChange={handleFileChange}
          className="hidden"
        />

        {/* Password Input Dialog - Only shown when PDF is password-protected */}
        {showPasswordInput && selectedFile && (
          <div className="mb-4 p-4 bg-surface-hover rounded-lg border border-border-default">
            <div className="flex items-start gap-2 mb-3">
              <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-text-primary mb-1">
                  Password Required
                </p>
                <p className="text-xs text-text-secondary">
                  This PDF is password-protected. Please enter the password to continue.
                </p>
                {passwordAttempts > 0 && (
                  <p className="text-xs text-amber-600 mt-1 font-medium">
                    Attempt {passwordAttempts} of {MAX_PASSWORD_ATTEMPTS}
                  </p>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <input
                type="password"
                value={pdfPassword}
                onChange={(e) => setPdfPassword(e.target.value)}
                placeholder="Enter PDF password"
                className="flex-1 px-3 py-2 text-sm bg-surface border border-border-default rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-blue/50"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && pdfPassword.trim()) {
                    handlePasswordConfirm();
                  } else if (e.key === 'Escape') {
                    handlePasswordCancel();
                  }
                }}
                autoFocus
              />
              <Button
                variant="primary"
                size="sm"
                onClick={handlePasswordConfirm}
                disabled={isUploading || !pdfPassword.trim()}
                className="px-4"
              >
                {isUploading ? 'Uploading...' : 'Try Password'}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handlePasswordCancel}
                disabled={isUploading}
                className="px-4"
              >
                Cancel
              </Button>
            </div>
            {localError && (
              <p className={`text-xs mt-2 flex items-center gap-1 ${
                localError.includes('attempts remaining') || localError.includes('Incorrect password')
                  ? 'text-amber-600'
                  : 'text-red-500'
              }`}>
                <AlertCircle className="w-3 h-3" />
                {localError}
              </p>
            )}
          </div>
        )}

        <Button
          variant="secondary"
          size="md"
          onClick={handleUpload}
          disabled={isUploading || loading || showPasswordInput}
          className="w-full flex flex-col items-center justify-center gap-2 rounded-xl py-3 border-dashed border-2 border-border-default hover:border-border-active hover:bg-surface-hover transition-all"
        >
          {isUploading ? (
            <div className="w-full px-2 space-y-2">
              <div className="flex justify-between items-center text-xs font-medium">
                <span className="flex items-center gap-1.5 text-text-primary">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-blue" /> 
                  <span>Uploading...</span>
                </span>
                <span className="text-text-secondary font-semibold">{uploadProgress}%</span>
              </div>
              <div className="w-full h-2 bg-border-default rounded-full overflow-hidden">
                <div 
                  className="h-full bg-accent-blue transition-all duration-300 rounded-full shadow-sm" 
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-text-primary">
              <Plus className="w-5 h-5" /> 
              <span className="font-semibold text-sm">Add documents</span>
            </div>
          )}
        </Button>

        {(localError || showSourcesFetchError) && (
          <div className="mt-3 p-2.5 rounded-xl bg-red-50 border border-red-200 flex items-start gap-2">
            <AlertCircle className="w-3.5 h-3.5 text-red-600 mt-0.5" />
            <p className="text-xs text-red-700 flex-1 leading-relaxed">
              {localError || (typeof apiError === 'string' 
                ? apiError 
                : apiError?.message || apiError?.toString() || 'An error occurred')}
            </p>
            <button 
              onClick={() => {
                setLocalError(null);
                // Note: apiError from TanStack Query will persist until query is refetched
                // This is expected behavior - the error will clear on next successful fetch
              }}
              className="cursor-pointer hover:opacity-70 transition-opacity"
            >
              <X className="w-3.5 h-3.5 text-red-400 hover:text-red-600" />
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {loading && displaySources.length === 0 ? (
          <div className="space-y-1">
            {[1, 2, 3, 4].map((i) => (
              <SourceItemSkeleton key={i} />
            ))}
          </div>
        ) : displaySources.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-6">
            <div className="w-16 h-16 rounded-full bg-surface-hover flex items-center justify-center mb-4">
              <FileText className="w-8 h-8 text-text-tertiary" />
            </div>
            <p className="text-text-primary text-base font-semibold mb-1">No sources connected</p>
            <p className="text-text-secondary text-sm text-center mb-4">
              Upload PDF or text files to start researching
            </p>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleUpload}
              className="flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              <span>Add your first source</span>
            </Button>
          </div>
        ) : (
          <div className="space-y-1.5">{displaySources.map((source) => renderSourceRow(source))}</div>
        )}
      </div>

      <div className="p-4 border-t border-border-default bg-surface-subtle">
        <div className="flex flex-col gap-1">
            <p className="text-xs font-bold text-text-primary">
              {selectedCountInLibrary} selected
            </p>
            <p className="text-xs text-text-tertiary font-medium">
              {displaySources.length} total sources in library
            </p>
        </div>
      </div>
    </div>
  );
}