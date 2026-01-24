/**
 * Studio Suite Component
 * 
 * Right sidebar top section with Studio generation tools.
 * Uses placeholder functionality until API keys are added.
 */

'use client';

import { useState, useEffect } from 'react';
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
import { GenerationModal, ContentType } from './GenerationModal';
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
  const { loading, error: apiError, errorDetails, handleRequest, clearError, apiClient } = useApi();
  const { selectedSources } = useSourceContext();
  const [generating, setGenerating] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState<string | object | null>(null);
  const [modalContentType, setModalContentType] = useState<ContentType>('text');
  const [modalTitle, setModalTitle] = useState<string>('Generated Content');
  const [modalError, setModalError] = useState<string | null>(null);

  // Watch for API errors and update modal error
  useEffect(() => {
    if (apiError && isModalOpen) {
      setModalError(apiError);
      setModalContent(null);
    }
  }, [apiError, isModalOpen]);
  
  // Also watch errorDetails for more detailed error info
  useEffect(() => {
    if (errorDetails && isModalOpen) {
      const errorMessage = errorDetails.message || 'An error occurred during generation';
      setModalError(errorMessage);
      setModalContent(null);
    }
  }, [errorDetails, isModalOpen]);

  // Determine content type based on task type and response structure
  const determineContentType = (taskType: string, result: any): ContentType => {
    // Check if result has a 'content' field (markdown/text) or 'data' field (JSON)
    if (result?.content) {
      // Mind maps, reports, infographics, slide decks return markdown
      if (['mind_map', 'report', 'infographic', 'slide_deck'].includes(taskType)) {
        return 'markdown';
      }
      return 'text';
    }
    
    // Quiz and flashcards return structured JSON data
    if (result?.data) {
      return 'json';
    }
    
    // Default to text
    return 'text';
  };

  // Format content for display
  const formatContent = (taskType: string, result: any): string | object => {
    if (result?.content) {
      return result.content;
    }
    
    if (result?.data) {
      return result;
    }
    
    return result || '';
  };

  // Get display title based on task type
  const getTitleForType = (type: string): string => {
    const tool = STUDIO_TOOLS.find(t => t.type === type);
    return tool ? `Generated ${tool.title}` : 'Generated Content';
  };

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
    setModalError(null);
    
    // Open modal with loading state
    setIsModalOpen(true);
    setModalTitle(getTitleForType(type));
    setModalContent(null);
    
    try {
      const result = await handleRequest(() =>
        apiClient.generateStudio(type as any, sourceIds)
      );
      
      // Wait a bit for error state to update (React state updates are async)
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Check if there was an error (check both immediately and after state update)
      if (errorDetails || apiError) {
        const errorMessage = errorDetails?.message || apiError || 'An error occurred during generation';
        setModalError(errorMessage);
        setModalContent(null);
      } else if (result) {
        const contentType = determineContentType(type, result);
        const formattedContent = formatContent(type, result);
        
        // Validate quiz data structure
        if (type === 'quiz' && formattedContent && typeof formattedContent === 'object') {
          const quizData = (formattedContent as any).data || formattedContent;
          if (!quizData.questions || !Array.isArray(quizData.questions) || quizData.questions.length === 0) {
            setModalError('Quiz was generated but has an invalid structure. Please try again.');
            setModalContent(null);
            return;
          }
        }
        
        setModalContentType(contentType);
        setModalContent(formattedContent);
        setModalError(null);
      } else {
        // If we have error details, use them; otherwise show generic message
        const errorMessage = errorDetails?.message || apiError || 'No content was generated. Please check the backend logs for details.';
        setModalError(errorMessage);
        setModalContent(null);
      }
    } catch (err: any) {
      // Use standardized error handling
      const apiError = err.apiError || handleApiError(err);
      const errorMessage = getUserFriendlyMessage(apiError);
      setModalError(errorMessage);
      setModalContent(null);
    } finally {
      setGenerating(null);
    }
  };

  // Handle save action
  const handleSave = async (content: string) => {
    try {
      // Create a blob and download the file
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${modalTitle.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      // Error already handled by error state
      // Fallback: copy to clipboard
      try {
        await navigator.clipboard.writeText(content);
        alert('Content copied to clipboard');
      } catch (clipboardErr) {
        // Silently fail - user can try again
      }
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 flex items-center px-4 border-b border-border-default">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-text-secondary" />
          <h2 className="text-lg font-medium text-text-primary">Studio</h2>
        </div>
      </div>

      {/* Error Display */}
      {(localError || apiError) && (
        <div className="p-3 mx-4 mt-2 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-xs text-red-700 font-medium">
              {localError || (typeof apiError === 'string' ? apiError : apiError || 'An error occurred')}
            </p>
            <button
              onClick={() => {
                setLocalError(null);
                clearError();
              }}
              className="text-xs text-red-600 hover:text-red-800 mt-1 underline cursor-pointer"
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

      {/* Generation Modal */}
      <GenerationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSave}
        title={modalTitle}
        contentType={modalContentType}
        content={modalContent}
        loading={generating !== null}
        error={modalError}
      />
    </div>
  );
}

