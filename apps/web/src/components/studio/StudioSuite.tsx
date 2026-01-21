/**
 * Studio Suite Component
 * 
 * Right sidebar top section with Studio generation tools.
 * Uses placeholder functionality until API keys are added.
 */

'use client';

import { useState } from 'react';
import { 
  FileQuestion, 
  Layers, 
  Network, 
  FileText, 
  Presentation, 
  Image as ImageIcon,
  AlertCircle
} from 'lucide-react';
import { StudioCard } from './StudioCard';
import { useApi } from '@/hooks/useApi';
import { useSourceContext } from '@/contexts/SourceContext';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';

const STUDIO_TOOLS = [
  { icon: <Network className="w-5 h-5" />, title: 'Mind Map', type: 'mind_map' },
  { icon: <FileText className="w-5 h-5" />, title: 'Reports', type: 'reports' },
  { icon: <Layers className="w-5 h-5" />, title: 'Flashcards', type: 'flashcards' },
  { icon: <FileQuestion className="w-5 h-5" />, title: 'Quiz', type: 'quiz' },
  { icon: <ImageIcon className="w-5 h-5" />, title: 'Infographic', type: 'infographic' },
  { icon: <Presentation className="w-5 h-5" />, title: 'Slide Deck', type: 'slide_deck' },
];

export function StudioSuite() {
  const { loading, error, handleRequest, apiClient } = useApi();
  const { selectedSources } = useSourceContext();
  const [generating, setGenerating] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleGenerate = async (type: string) => {
    const sourceIds = Array.from(selectedSources);
    
    if (sourceIds.length === 0) {
      setLocalError('Please select at least one source to generate content');
      return;
    }
    
    // Check network status
    if (!navigator.onLine) {
      setLocalError('Network disconnected. Please check your internet connection.');
      return;
    }
    
    setGenerating(type);
    setLocalError(null);
    
    try {
      const result = await handleRequest(() =>
        apiClient.generateStudio(type as any, sourceIds)
      );
      
      if (result) {
        // TODO: Display the generated content in a modal or new view
        alert(`${type} generated successfully!`);
      }
    } catch (err: any) {
      console.error('Generation error:', err);
      // Use standardized error handling
      const apiError = err.apiError || handleApiError(err);
      const errorMessage = getUserFriendlyMessage(apiError);
      setLocalError(errorMessage);
    } finally {
      setGenerating(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border-default">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-text-secondary" />
          <h2 className="text-lg font-medium text-text-primary">Studio</h2>
        </div>
      </div>

      {/* Error Display */}
      {(localError || error) && (
        <div className="p-3 mx-4 mt-2 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-xs text-red-700 font-medium">
              {localError || (typeof error === 'string' ? error : error?.message || 'An error occurred')}
            </p>
            <button
              onClick={() => setLocalError(null)}
              className="text-xs text-red-600 hover:text-red-800 mt-1 underline"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Studio Grid */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="grid grid-cols-2 gap-3">
          {STUDIO_TOOLS.map((tool) => {
            const isGenerating = generating === tool.type;
            return (
              <StudioCard
                key={tool.type}
                icon={tool.icon}
                title={tool.title}
                onClick={() => !isGenerating && handleGenerate(tool.type)}
                disabled={isGenerating || loading}
              />
            );
          })}
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-border-default">
        <p className="text-xs text-text-tertiary text-center">
          Select sources to generate content
        </p>
      </div>
    </div>
  );
}

