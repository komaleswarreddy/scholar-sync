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

import { useState, useEffect, useRef } from 'react';
import { Checkbox } from '../ui/Checkbox';
import { Button } from '../ui/Button';
import { FileText, Plus, X, Loader2, AlertCircle, CheckCircle2, Trash2 } from 'lucide-react';
import { useApi } from '@/hooks/useApi';
import { useSourceContext } from '@/contexts/SourceContext';

interface Source {
  id: string;
  title: string;
  type?: string;
  status: 'processing' | 'indexed' | 'error';
  created_at?: string;
  chunks_count?: number;
  error_message?: string;
}

export function SourceList() {
  const { selectedSources, toggleSource, removeSource, clearSelection } = useSourceContext();
  const [sources, setSources] = useState<Source[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [localError, setLocalError] = useState<string | null>(null);
  
  // Task E.c: State to track which specific item is being deleted
  const [deletingId, setDeletingId] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { loading, error: apiError, handleRequest, apiClient } = useApi();

  useEffect(() => {
    loadSources();
    const interval = setInterval(() => {
        loadSources();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadSources = async () => {
    try {
      const result = await handleRequest(() => apiClient.listSources());
      if (result && Array.isArray(result)) {
        setSources(result as Source[]);
      } else {
        setSources([]);
      }
    } catch (error) {
      console.error('Failed to load sources:', error);
      setSources([]);
    }
  };

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

    setIsUploading(true);
    setUploadProgress(0);
    setLocalError(null);

    try {
      const result = await apiClient.uploadSource(file, file.name, (percent) => {
        setUploadProgress(percent);
      });

      if (result) {
        await loadSources(); 
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    } catch (err: any) {
      setLocalError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  // Task E: Optimized Deletion Flow
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
      const result = await handleRequest(() => apiClient.deleteSource(sourceId));
      
      if (result !== null) {
        // Task E.e: Refresh list and clean selection context
        removeSource(sourceId); 
        await loadSources();
      }
    } catch (err: any) {
      // Task E.d: Graceful error handling
      setLocalError(err.response?.data?.detail || "Failed to delete source.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface border-r border-border-default">
      <div className="p-4 border-b border-border-default">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-text-primary" />
            <h2 className="text-lg font-bold text-text-primary tracking-tight">Sources</h2>
          </div>
          {selectedSources.size > 0 && (
            <button 
              onClick={clearSelection}
              className="text-[11px] font-medium text-text-tertiary hover:text-text-primary transition-colors"
            >
              Deselect all
            </button>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt"
          onChange={handleFileChange}
          className="hidden"
        />

        <Button
          variant="secondary"
          size="md"
          onClick={handleUpload}
          disabled={isUploading || loading}
          className="w-full flex flex-col items-center justify-center gap-1 rounded-xl py-3 border-dashed border-2 bg-surface-subtle"
        >
          {isUploading ? (
            <div className="w-full px-2">
              <div className="flex justify-between text-[10px] mb-1.5 font-medium">
                <span className="flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin" /> Uploading...
                </span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full h-1.5 bg-border-default rounded-full overflow-hidden">
                <div 
                  className="h-full bg-text-primary transition-all duration-300" 
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Plus className="w-4 h-4" /> 
              <span className="font-semibold text-sm">Add documents</span>
            </div>
          )}
        </Button>

        {(localError || apiError) && (
          <div className="mt-3 p-2.5 rounded-xl bg-red-50 border border-red-200 flex items-start gap-2">
            <AlertCircle className="w-3.5 h-3.5 text-red-600 mt-0.5" />
            <p className="text-xs text-red-700 flex-1 leading-relaxed">{localError || apiError}</p>
            <button onClick={() => setLocalError(null)}>
              <X className="w-3.5 h-3.5 text-red-400 hover:text-red-600" />
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {loading && sources.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-text-tertiary mb-3" />
            <p className="text-text-tertiary text-xs font-medium">Loading library...</p>
          </div>
        ) : sources.length === 0 ? (
          <div className="text-center py-12 px-6">
            <p className="text-text-secondary text-sm font-semibold mb-1">No sources connected</p>
            <p className="text-text-tertiary text-xs">Upload a file to start research</p>
          </div>
        ) : (
          <div className="space-y-1">
            {sources.map((source) => {
              const isSelected = selectedSources.has(source.id);
              const isDeleting = deletingId === source.id;
              
              return (
                <div
                  key={source.id}
                  className={`flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-all group relative
                    ${isSelected ? 'bg-surface-hover border border-border-default' : 'hover:bg-surface-subtle border border-transparent'}`}
                  onClick={() => !isDeleting && toggleSource(source.id)}
                >
                  <div className="mt-0.5">
                    <Checkbox checked={isSelected} onChange={() => {}} disabled={isDeleting} />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      {source.status === 'processing' && (
                        <span className="text-[9px] font-bold uppercase bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded flex items-center gap-1">
                          <Loader2 className="w-2.5 h-2.5 animate-spin" /> processing
                        </span>
                      )}
                      {source.status === 'indexed' && (
                        <span className="text-[9px] font-bold uppercase bg-green-50 text-green-600 px-1.5 py-0.5 rounded flex items-center gap-1">
                          <CheckCircle2 className="w-2.5 h-2.5" /> ready
                        </span>
                      )}
                      {source.status === 'error' && (
                        <span 
                          className="text-[9px] font-bold uppercase bg-red-50 text-red-600 px-1.5 py-0.5 rounded flex items-center gap-1"
                        >
                          <AlertCircle className="w-2.5 h-2.5" /> error
                        </span>
                      )}
                    </div>

                    <p className={`text-sm font-semibold truncate ${isSelected ? 'text-text-primary' : 'text-text-secondary'}`}>
                      {source.title}
                    </p>
                    
                    {source.status === 'error' && source.error_message && (
                      <div className="mt-1.5 p-2 rounded-lg bg-red-50 border border-red-200">
                        <p className="text-[10px] text-red-700 leading-relaxed">
                          {source.error_message}
                        </p>
                      </div>
                    )}
                    
                    <div className="flex items-center gap-2 mt-1.5">
                        <p className="text-[10px] font-bold text-text-tertiary uppercase">
                            {source.chunks_count || 0} chunks
                        </p>
                        <span className="text-text-tertiary text-[10px]">•</span>
                        <p className="text-[10px] font-medium text-text-tertiary">
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
                    className={`p-1.5 rounded-lg transition-all 
                      ${isDeleting ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 text-text-tertiary hover:text-red-600 hover:bg-red-50'}`}
                  >
                    {isDeleting ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-red-600" />
                    ) : (
                      <Trash2 className="w-3.5 h-3.5" />
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
            <p className="text-[10px] text-text-tertiary font-medium">
              {sources.length} total sources in library
            </p>
        </div>
      </div>
    </div>
  );
}