/**
 * Source List Component 
 * Tasks Implemented:
 * - A: Already connected - Local duplicate check & verify error handling
 * - B: File Validation (Size & Type)
 * - C: Upload Progress Indicator
 * - D: Handle upload errors gracefully with user-friendly messages (UI Error State)
 * - E: Refresh source list after successful upload
 * - F: Show processing status (processing → indexed) via Polling
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { Checkbox } from '../ui/Checkbox';
import { Button } from '../ui/Button';
import { FileText, Plus, X, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useApi } from '@/hooks/useApi';
import { useSourceContext } from '@/contexts/SourceContext';

interface Source {
  id: string;
  title: string;
  type?: string;
  status: 'processing' | 'indexed' | 'error'; // Task F: Added Status
  created_at?: string;
  chunks_count?: number;
}

export function SourceList() {
  const { selectedSources, toggleSource } = useSourceContext();
  const [sources, setSources] = useState<Source[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0); // Task C: Progress state
  const [localError, setLocalError] = useState<string | null>(null); // Task D: Local error handling
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { loading, error: apiError, handleRequest, apiClient } = useApi();

  // Load sources on mount
  useEffect(() => {
    loadSources();
    
    // Task F: Simple Polling - Refresh list every 10 seconds to update processing status
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
    setLocalError(null); // Clear errors when starting new flow
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // --- TASK A: Already Connected Check (Local) ---
    const isAlreadyConnected = sources.some(
      (s) => s.title.toLowerCase() === file.name.toLowerCase()
    );
    if (isAlreadyConnected) {
      setLocalError("This file is already connected as a source.");
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    // --- TASK B: File Validation ---
    const MAX_SIZE = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['application/pdf', 'text/plain'];
    const allowedExtensions = ['.pdf', '.txt'];
    
    // Check both MIME type and file extension (some browsers don't set MIME type correctly)
    const hasValidType = allowedTypes.includes(file.type);
    const hasValidExtension = allowedExtensions.some(ext => 
      file.name.toLowerCase().endsWith(ext)
    );
    
    if (!hasValidType && !hasValidExtension) {
      setLocalError("Only PDF and TXT files are supported.");
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    if (file.size > MAX_SIZE) {
      setLocalError("File is too large. Limit is 10MB.");
      return;
    }

    setIsUploading(true);
    setUploadProgress(0); // Reset progress
    setLocalError(null);

    try {
      // Call upload directly to get better error handling
      console.log('📤 Starting file upload:', file.name, file.size, 'bytes');
      const result = await apiClient.uploadSource(file, file.name, (percent) => {
        setUploadProgress(percent); // Update progress state from Axios
        console.log(`📤 Upload progress: ${percent}%`);
      });

      console.log('✅ Upload successful:', result);
      
      if (result) {
        // --- TASK E: Refresh list ---
        await loadSources(); 
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    } catch (err: any) {
      // Task D: Handle upload errors gracefully with user-friendly messages
      console.error('❌ Upload error:', err);
      console.error('❌ Error details:', {
        code: err.code,
        message: err.message,
        response: err.response?.data,
        status: err.response?.status
      });
      
      let msg = "Upload failed. Please check your connection and try again.";
      
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        msg = "Upload timed out. The file might be too large or the server is taking too long. Please try again with a smaller file.";
      } else if (err.response?.data?.detail) {
        msg = err.response.data.detail;
      } else if (err.response?.status === 403) {
        msg = "Access denied. Please check your authentication.";
      } else if (err.response?.status === 401) {
        msg = "Authentication failed. Please sign in again.";
      } else if (err.message) {
        msg = err.message;
      }
      
      setLocalError(msg);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDelete = async (sourceId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this source?')) return;

    const result = await handleRequest(() => apiClient.deleteSource(sourceId));
    if (result !== null) {
      await loadSources();
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface">
      {/* Header Section */}
      <div className="p-4 border-b border-border-default">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-text-secondary" />
            <h2 className="text-lg font-semibold text-text-primary">Sources</h2>
          </div>
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
          className="w-full flex flex-col items-center justify-center gap-1 rounded-2xl py-3"
        >
          {isUploading ? (
            <div className="w-full px-2">
              <div className="flex justify-between text-[10px] mb-1">
                <span className="flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin" /> Uploading...
                </span>
                <span>{uploadProgress}%</span>
              </div>
              {/* Task C: Progress Bar Visual */}
              <div className="w-full h-1 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-accent-blue transition-all duration-300" 
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Plus className="w-5 h-5" /> 
              <span>Add sources</span>
            </div>
          )}
        </Button>

        {/* Task D: Graceful Error Display (Handles local validation & API errors) */}
        {(localError || apiError) && (
          <div className="mt-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20 flex items-start gap-2">
            <AlertCircle className="w-3 h-3 text-red-400 mt-0.5" />
            <p className="text-xs text-red-400 flex-1">{localError || apiError}</p>
            <button onClick={() => setLocalError(null)}>
              <X className="w-3 h-3 text-red-400" />
            </button>
          </div>
        )}
      </div>

      {/* Source List Section */}
      <div className="flex-1 overflow-y-auto p-2">
        {loading && sources.length === 0 ? (
          <div className="text-center py-8">
            <Loader2 className="w-6 h-6 animate-spin mx-auto text-accent-blue mb-2" />
            <p className="text-text-secondary text-sm">Fetching sources...</p>
          </div>
        ) : sources.length === 0 ? (
          <div className="text-center py-8 px-4">
            <p className="text-text-secondary text-sm mb-1">No sources yet</p>
            <p className="text-text-tertiary text-xs">Upload a PDF to start research</p>
          </div>
        ) : (
          <div className="space-y-1">
            {sources.map((source) => {
              const isSelected = selectedSources.has(source.id);
              
              return (
                <div
                  key={source.id}
                  className={`flex items-start gap-3 p-3 rounded-2xl cursor-pointer transition-all group
                    ${isSelected ? 'bg-surface-hover shadow-sm' : 'hover:bg-surface-hover'}`}
                  onClick={() => toggleSource(source.id)}
                >
                  <Checkbox checked={isSelected} onChange={() => {}} />
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className={`w-4 h-4 ${source.status === 'error' ? 'text-red-400' : 'text-red-400'}`} />
                      
                      {/* TASK F: Enhanced Status Badges */}
                      {source.status === 'processing' && (
                        <span className="text-[10px] bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded flex items-center gap-1 animate-pulse">
                          <Loader2 className="w-2 h-2 animate-spin" /> processing
                        </span>
                      )}
                      {source.status === 'indexed' && (
                        <span className="text-[10px] bg-green-500/10 text-green-400 px-1.5 py-0.5 rounded flex items-center gap-1">
                          <CheckCircle2 className="w-2 h-2" /> ready
                        </span>
                      )}
                      {source.status === 'error' && (
                        <span className="text-[10px] bg-red-500/10 text-red-400 px-1.5 py-0.5 rounded flex items-center gap-1">
                          <AlertCircle className="w-2 h-2" /> error
                        </span>
                      )}
                    </div>

                    <p className={`text-sm font-medium line-clamp-2 ${isSelected ? 'text-text-primary' : 'text-text-secondary'}`}>
                      {source.title}
                    </p>
                    
                    <div className="flex items-center gap-2 mt-1">
                        <p className="text-[10px] text-text-tertiary uppercase">
                            {source.chunks_count || 0} chunks
                        </p>
                        <span className="text-text-tertiary text-[10px]">•</span>
                        <p className="text-[10px] text-text-tertiary">
                            {source.created_at ? new Date(source.created_at).toLocaleDateString() : 'Just now'}
                        </p>
                    </div>
                  </div>
                  
                  <button
                    onClick={(e) => handleDelete(source.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-text-tertiary hover:text-red-400 transition-all"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Section - Selection Counter */}
      <div className="p-4 border-t border-border-default bg-surface-subtle">
        <p className="text-xs text-text-tertiary text-center">
          {selectedSources.size} of {sources.length} sources selected
        </p>
      </div>
    </div>
  );
}