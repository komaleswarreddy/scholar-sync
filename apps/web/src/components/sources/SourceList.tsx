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

import { useState, useRef } from 'react';
import { Checkbox } from '../ui/Checkbox';
import { Button } from '../ui/Button';
import { FileText, Plus, X, Loader2, AlertCircle, CheckCircle2, Trash2, File, Globe, FileType } from 'lucide-react';
import { useSources, useUploadSource, useDeleteSource } from '@/hooks/useSources';
import { useSourceContext } from '@/contexts/SourceContext';
import { SourceItemSkeleton } from './SourceItemSkeleton';

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

export function SourceList() {
  const { selectedSources, toggleSource, removeSource, clearSelection } = useSourceContext();
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
  
  // Task C.a & C.b: Use TanStack Query for sources with loading states and caching
  const { data: sources = [], isLoading, error: apiError } = useSources();
  const uploadMutation = useUploadSource();
  const deleteMutation = useDeleteSource();

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

    const isAlreadyConnected = sources.some(
      (s) => s.title.toLowerCase() === file.name.toLowerCase()
    );
    if (isAlreadyConnected) {
      setLocalError("This file is already connected.");
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    const MAX_SIZE = 10 * 1024 * 1024;
    const allowedExtensions = ['.pdf', '.txt'];
    const hasValidExtension = allowedExtensions.some(ext => 
      file.name.toLowerCase().endsWith(ext)
    );
    
    if (!hasValidExtension) {
      setLocalError("Only PDF and TXT files are supported.");
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
      await uploadMutation.mutateAsync({
        file,
        title: file.name,
        pdfPassword: password || undefined,
        onProgress: (percent) => {
          setUploadProgress(percent);
        },
      });
      
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

  return (
    <div className="flex flex-col h-full bg-surface border-r border-border-default">
      <div className="h-14 flex items-center px-4 border-b border-border-default">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-text-primary" />
            <h2 className="text-lg font-bold text-text-primary tracking-tight">Sources</h2>
          </div>
          {selectedSources.size > 0 && (
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
          accept=".pdf,.txt"
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

        {(localError || apiError) && (
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
        {loading && sources.length === 0 ? (
          <div className="space-y-1">
            {[1, 2, 3, 4].map((i) => (
              <SourceItemSkeleton key={i} />
            ))}
          </div>
        ) : sources.length === 0 ? (
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
          <div className="space-y-1.5">
            {sources.map((source) => {
              const isSelected = selectedSources.has(source.id);
              const isDeleting = deletingId === source.id;
              // Use type or file_type from API, or infer from title
              const sourceType = source.type || source.file_type || 
                (source.title?.toLowerCase().endsWith('.pdf') ? 'pdf' : 
                 source.title?.toLowerCase().endsWith('.txt') ? 'text' : 'text');
              const fileType = getFileTypeIcon(sourceType);
              const IconComponent = fileType.icon;
              // Map status: 'completed' -> 'indexed', 'failed' -> 'error'
              const mappedStatus = source.status === 'completed' ? 'indexed' :
                                   source.status === 'failed' ? 'error' : source.status;
              
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
                  <div className="mt-0.5 flex-shrink-0">
                    <Checkbox checked={isSelected} onChange={() => {}} disabled={isDeleting} />
                  </div>
                  
                  {/* File Type Icon */}
                  <div className={`flex-shrink-0 w-8 h-8 rounded-lg ${fileType.bgColor} border ${fileType.borderColor} flex items-center justify-center mt-0.5`}>
                    <IconComponent className={`w-4 h-4 ${fileType.color}`} />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
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

                    <p className={`text-sm font-semibold truncate mb-1 ${isSelected ? 'text-text-primary' : 'text-text-secondary'}`}>
                      {source.title}
                    </p>
                    
                    {mappedStatus === 'error' && source.error_message && (
                      <div className="mt-1.5 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                        <p className="text-xs text-red-600 leading-relaxed">
                          {source.error_message}
                        </p>
                      </div>
                    )}
                    
                    <div className="flex items-center gap-2 mt-1.5">
                        <p className="text-xs font-medium text-text-tertiary">
                            {source.chunks_count || 0} chunks
                        </p>
                        <span className="text-text-tertiary text-xs">•</span>
                        <p className="text-xs font-medium text-text-tertiary">
                            {source.created_at ? new Date(source.created_at).toLocaleDateString(undefined, {
                              month: 'short',
                              day: 'numeric'
                            }) : 'Just now'}
                        </p>
                    </div>
                  </div>
                  
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
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="p-4 border-t border-border-default bg-surface-subtle">
        <div className="flex flex-col gap-1">
            <p className="text-xs font-bold text-text-primary">
              {selectedSources.size} selected
            </p>
            <p className="text-xs text-text-tertiary font-medium">
              {sources.length} total sources in library
            </p>
        </div>
      </div>
    </div>
  );
}