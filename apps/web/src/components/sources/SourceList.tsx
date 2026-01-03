/**
 * Source List Component
 * 
 * Left sidebar showing all uploaded sources.
 * Uses placeholder data until API keys are added.
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { Checkbox } from '../ui/Checkbox';
import { Button } from '../ui/Button';
import { FileText, Globe, Plus, Search, ArrowRight, Upload, X } from 'lucide-react';
import { useApi } from '@/hooks/useApi';
import { useSourceContext } from '@/contexts/SourceContext';

interface Source {
  id: string;
  title: string;
  type?: string;
  file_type?: string;
  created_at?: string;
  uploadedAt?: string;
}

export function SourceList() {
  const { selectedSources, toggleSource } = useSourceContext();
  const [sources, setSources] = useState<Source[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { loading, error, handleRequest, apiClient } = useApi();

  // Load sources on mount
  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    try {
      const result = await handleRequest(() => apiClient.listSources());
      if (result && Array.isArray(result)) {
        setSources(result as Source[]);
      } else {
        console.warn('Unexpected response format:', result);
        setSources([]);
      }
    } catch (error) {
      console.error('Failed to load sources:', error);
      setSources([]);
    }
  };


  const handleUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) {
      console.log('No file selected');
      return;
    }

    console.log('Starting upload:', file.name, file.type, file.size);
    setIsUploading(true);
    try {
      console.log('Calling uploadSource API...');
      const result = await handleRequest(() =>
        apiClient.uploadSource(file, file.name)
      );
      console.log('Upload result:', result);
      if (result) {
        console.log('Upload successful, reloading sources...');
        await loadSources(); // Reload sources list
        // Reset file input
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        console.warn('Upload returned no result');
      }
    } catch (err) {
      console.error('Upload error:', err);
      alert(`Upload failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
      console.log('Upload finished');
    }
  };

  const handleDelete = async (sourceId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this source?')) return;

    const result = await handleRequest(() => apiClient.deleteSource(sourceId));
    if (result !== null) {
      await loadSources();
      // Note: selectedSources is managed by context, deletion handled automatically
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
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
          className="w-full flex items-center justify-center gap-2 rounded-2xl py-3"
        >
          {isUploading ? (
            <>
              <div className="w-5 h-5 border-2 border-text-primary border-t-transparent rounded-full animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <Plus className="w-5 h-5" />
              Add sources
            </>
          )}
        </Button>
        {error && (
          <div className="mt-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-xs text-red-400">{error}</p>
          </div>
        )}
        
        {/* Deep Research Card */}
        <div className="mt-3 p-3 rounded-2xl bg-accent-green/10 border border-accent-green/20">
          <p className="text-xs text-text-primary leading-relaxed">
            Try Deep Research for an in-depth report and new sources!
          </p>
        </div>
        
        {/* Search Bar */}
        <div className="mt-3 flex items-center gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              placeholder="Search the web for new sources"
              className="w-full bg-surface border border-border-default rounded-full px-4 py-2 pl-10 text-sm text-text-primary placeholder-text-tertiary focus:outline-none focus:border-border-active"
            />
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
          </div>
          <select className="bg-surface border border-border-default rounded-full px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-border-active">
            <option>Web</option>
            <option>Fast Research</option>
          </select>
          <button className="p-2 rounded-full hover:bg-surface-hover transition-colors">
            <ArrowRight className="w-4 h-4 text-text-secondary" />
          </button>
        </div>
        
        {/* Select All */}
        <div className="mt-3 flex items-center gap-2">
          <Checkbox id="select-all" />
          <label htmlFor="select-all" className="text-sm text-text-secondary cursor-pointer">
            Select all sources
          </label>
        </div>
      </div>

      {/* Source List */}
      <div className="flex-1 overflow-y-auto p-2">
        {loading && sources.length === 0 ? (
          <div className="text-center py-8 px-4">
            <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-text-secondary text-sm">Loading sources...</p>
          </div>
        ) : sources.length === 0 ? (
          <div className="text-center py-8 px-4">
            <p className="text-text-secondary text-sm mb-2">No sources yet</p>
            <p className="text-text-tertiary text-xs">
              Upload a document to get started
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {sources.map((source) => {
              const isSelected = selectedSources.has(source.id);
              const sourceType = source.file_type || 'pdf';
              
              return (
                <div
                  key={source.id}
                  className={`
                    flex items-center gap-3 p-3 rounded-2xl cursor-pointer
                    transition-colors duration-200 group
                    ${isSelected 
                      ? 'bg-surface-hover' 
                      : 'hover:bg-surface-hover'
                    }
                  `}
                  onClick={() => toggleSource(source.id)}
                >
                  <Checkbox
                    checked={isSelected}
                    onChange={() => toggleSource(source.id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                  
                  <div className="flex-1 min-w-0">
                    {sourceType === 'pdf' || sourceType === 'application/pdf' ? (
                      <FileText className="w-4 h-4 text-red-400 mb-1" />
                    ) : (
                      <Globe className="w-4 h-4 text-accent-blue mb-1" />
                    )}
                    <p
                      className={`
                        text-sm line-clamp-2
                        ${isSelected ? 'text-text-primary' : 'text-text-secondary'}
                      `}
                    >
                      {source.title}
                    </p>
                    <p className="text-xs text-text-tertiary mt-1">
                      {source.created_at 
                        ? new Date(source.created_at).toLocaleDateString()
                        : 'Recently uploaded'}
                    </p>
                  </div>
                  
                  <button
                    onClick={(e) => handleDelete(source.id, e)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-full hover:bg-surface text-text-secondary hover:text-red-400"
                    title="Delete source"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-border-default">
        <p className="text-xs text-text-tertiary text-center">
          {selectedSources.size} of {sources.length} selected
        </p>
      </div>
    </div>
  );
}

