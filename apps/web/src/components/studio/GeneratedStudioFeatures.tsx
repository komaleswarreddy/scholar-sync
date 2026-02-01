/**
 * Generated Studio Features Component
 * 
 * Displays all automatically saved studio-generated features.
 * Shows them in a scrollable list below the Studio Suite.
 */

'use client';

import { useState, useEffect } from 'react';
import { FileText, X, Download } from 'lucide-react';
import { GenerationModal } from './GenerationModal';

interface GeneratedFeature {
  id: string;
  type: string;
  title: string;
  content: any;
  timestamp: Date;
}

export function GeneratedStudioFeatures() {
  const [features, setFeatures] = useState<GeneratedFeature[]>([]);
  const [selectedFeature, setSelectedFeature] = useState<GeneratedFeature | null>(null);

  // Load features from localStorage on mount
  useEffect(() => {
    const savedFeatures = localStorage.getItem('generatedStudioFeatures');
    if (savedFeatures) {
      try {
        const parsed = JSON.parse(savedFeatures);
        // Convert timestamp strings back to Date objects
        const featuresWithDates = parsed.map((f: any) => ({
          ...f,
          timestamp: new Date(f.timestamp)
        }));
        setFeatures(featuresWithDates);
      } catch (e) {
        console.error('Failed to load generated features:', e);
      }
    }
  }, []);

  // Listen for new feature generation events
  useEffect(() => {
    const handleFeatureGenerated = (event: CustomEvent) => {
      const { type, title, content } = event.detail;
      const newFeature: GeneratedFeature = {
        id: `feature-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        type,
        title,
        content,
        timestamp: new Date()
      };
      
      setFeatures(prev => {
        const updated = [newFeature, ...prev];
        // Save to localStorage
        localStorage.setItem('generatedStudioFeatures', JSON.stringify(updated));
        return updated;
      });
    };

    window.addEventListener('studioFeatureGenerated' as any, handleFeatureGenerated as EventListener);
    return () => {
      window.removeEventListener('studioFeatureGenerated' as any, handleFeatureGenerated as EventListener);
    };
  }, []);

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent opening modal when clicking delete
    setFeatures(prev => {
      const updated = prev.filter(f => f.id !== id);
      localStorage.setItem('generatedStudioFeatures', JSON.stringify(updated));
      return updated;
    });
    if (selectedFeature?.id === id) {
      setSelectedFeature(null);
    }
  };

  const handleDownload = (feature: GeneratedFeature, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent opening modal when clicking download
    try {
      const content = typeof feature.content === 'string' 
        ? feature.content 
        : JSON.stringify(feature.content, null, 2);
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${feature.title.toLowerCase().replace(/\s+/g, '-')}-${feature.id}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download:', err);
    }
  };


  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-border-default flex-shrink-0">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-text-secondary" />
          <h2 className="text-lg font-medium text-text-primary">Generated Features</h2>
          {features.length > 0 && (
            <span className="text-xs text-text-secondary bg-surface-hover px-2 py-0.5 rounded-full">
              {features.length}
            </span>
          )}
        </div>
      </div>

      {/* Features List */}
      <div className="flex-1 overflow-y-auto">
        {features.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6">
            <FileText className="w-12 h-12 text-text-tertiary mb-3 opacity-50" />
            <p className="text-sm text-text-secondary">
              Generated features will appear here automatically
            </p>
          </div>
        ) : (
          <div className="p-4 space-y-3">
            {features.map((feature) => (
              <div
                key={feature.id}
                onClick={() => setSelectedFeature(feature)}
                className="bg-surface-subtle rounded-lg border border-border-default overflow-hidden cursor-pointer hover:bg-surface-hover transition-colors"
              >
                {/* Feature Header */}
                <div className="p-3 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-text-primary truncate">
                      {feature.title}
                    </h3>
                    <p className="text-xs text-text-secondary mt-0.5">
                      {formatDate(feature.timestamp)} • {feature.type.replace('_', ' ')}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 ml-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={(e) => handleDownload(feature, e)}
                      className="p-1.5 hover:bg-surface-hover rounded transition-colors"
                      title="Download"
                    >
                      <Download className="w-3.5 h-3.5 text-text-secondary" />
                    </button>
                    <button
                      onClick={(e) => handleDelete(feature.id, e)}
                      className="p-1.5 hover:bg-surface-hover rounded transition-colors"
                      title="Delete"
                    >
                      <X className="w-3.5 h-3.5 text-text-secondary" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Feature Modal */}
      {selectedFeature && (
        <GenerationModal
          isOpen={!!selectedFeature}
          onClose={() => setSelectedFeature(null)}
          title={selectedFeature.title}
          content={selectedFeature.content}
          contentType="text"
        />
      )}
    </div>
  );
}
