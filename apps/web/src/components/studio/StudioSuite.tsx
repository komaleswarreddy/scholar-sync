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
  AlertCircle,
  Settings
} from 'lucide-react';
import { StudioCard } from './StudioCard';
import { GenerationModal, ContentType } from './GenerationModal';
import { useApi } from '@/hooks/useApi';
import { useSourceContext } from '@/contexts/SourceContext';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';

const STUDIO_TOOLS = [
  { icon: <Network className="w-5 h-5" />, title: 'Mind Map', type: 'mind_map' },
  { icon: <FileText className="w-5 h-5" />, title: 'Reports', type: 'report' },
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
  
  // Store last generation parameters for retry
  const [lastGenerationType, setLastGenerationType] = useState<string | null>(null);
  const [lastSourceIds, setLastSourceIds] = useState<string[]>([]);
  const [lastCustomInstructions, setLastCustomInstructions] = useState<string>('');
  const [sourceCount, setSourceCount] = useState<number>(0);
  
  // Custom instructions state
  const [customInstructions, setCustomInstructions] = useState<string>('');
  const [showCustomInstructions, setShowCustomInstructions] = useState<boolean>(false);

  // Watch for API errors and update modal error
  useEffect(() => {
    if (isModalOpen) {
      if (errorDetails?.message) {
        setModalError(errorDetails.message);
        setModalContent(null);
      } else if (apiError) {
        setModalError(typeof apiError === 'string' ? apiError : 'An error occurred during generation');
        setModalContent(null);
      }
    }
  }, [apiError, errorDetails, isModalOpen]);

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
      const content = result.content;
      // Validate content is not empty
      if (typeof content === 'string' && !content.trim()) {
        return null; // Return null to trigger error display
      }
      
      // If content is a string and we have a task type, wrap it in an object with task_type
      // This helps the GenerationModal correctly identify the content type
      if (typeof content === 'string' && taskType) {
        return {
          task_type: taskType,
          content: content
        };
      }
      
      // If result already has task_type, preserve it and all other fields (like image_url for infographics)
      if (result.task_type) {
        const formatted: any = {
          task_type: result.task_type,
          content: content
        };
        // Preserve infographic-specific fields
        if (result.image_url) formatted.image_url = result.image_url;
        if (result.revised_prompt) formatted.revised_prompt = result.revised_prompt;
        if (result.image_error) formatted.image_error = result.image_error;
        return formatted;
      }
      
      return content;
    }
    
    if (result?.data) {
      // For structured data (quiz, flashcards), validate it's not empty
      if (Array.isArray(result.data) && result.data.length === 0) {
        return null; // Return null to trigger error display
      }
      if (typeof result.data === 'object' && Object.keys(result.data).length === 0) {
        return null; // Return null to trigger error display
      }
      
      // Ensure task_type is included
      if (result.task_type) {
        return result;
      } else if (taskType) {
        return {
          task_type: taskType,
          ...result
        };
      }
      
      return result;
    }
    
    // If result is empty string or falsy, return null
    if (!result || (typeof result === 'string' && !result.trim())) {
      return null;
    }
    
    // If result is an object without task_type, add it
    if (typeof result === 'object' && !result.task_type && taskType) {
      return {
        task_type: taskType,
        ...result
      };
    }
    
    return result;
  };

  // Get display title based on task type
  const getTitleForType = (type: string): string => {
    const tool = STUDIO_TOOLS.find(t => t.type === type);
    return tool ? `Generated ${tool.title}` : 'Generated Content';
  };

  const handleGenerate = async (type: string, sourceIdsOverride?: string[], customInstructionsOverride?: string) => {
    const sourceIds = sourceIdsOverride || Array.from(selectedSources);
    const instructions = customInstructionsOverride !== undefined ? customInstructionsOverride : customInstructions;
    
    if (sourceIds.length === 0) {
      setLocalError('Please select at least one source to generate content');
      return;
    }
    
    // Check network status
    if (!navigator.onLine) {
      setLocalError('Network disconnected. Please check your internet connection.');
      return;
    }
    
    // Store generation parameters for retry
    setLastGenerationType(type);
    setLastSourceIds(sourceIds);
    setLastCustomInstructions(customInstructions);
    setSourceCount(sourceIds.length);
    
    setGenerating(type);
    setLocalError(null);
    setModalError(null);
    
    // Open modal with loading state
    setIsModalOpen(true);
    setModalTitle(getTitleForType(type));
    setModalContent(null);
    
    try {
      const result = await handleRequest(() =>
        apiClient.generateStudio(type as any, sourceIds, instructions.trim() || undefined)
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
        
        // Check if formatted content is null or empty
        if (formattedContent === null || formattedContent === undefined) {
          const errorMessage = errorDetails?.message || apiError || 'No content was generated. The model may have been blocked or returned empty content. Please try again.';
          setModalError(errorMessage);
          setModalContent(null);
          return;
        }
        
        // Validate quiz data structure
        if (type === 'quiz' && formattedContent && typeof formattedContent === 'object') {
          const quizData = (formattedContent as any).data || formattedContent;
          if (!quizData.questions || !Array.isArray(quizData.questions) || quizData.questions.length === 0) {
            setModalError('Quiz was generated but has an invalid structure. Please try again.');
            setModalContent(null);
            return;
          }
        }
        
        // Validate flashcards data structure
        if (type === 'flashcards' && formattedContent && typeof formattedContent === 'object') {
          const flashcardsData = (formattedContent as any).data || formattedContent;
          if (Array.isArray(flashcardsData) && flashcardsData.length === 0) {
            setModalError('Flashcards were generated but the list is empty. Please try again.');
            setModalContent(null);
            return;
          }
        }
        
        setModalContentType(contentType);
        setModalContent(formattedContent);
        setModalError(null);
        
        // Auto-save the generated feature
        const featureType = type;
        window.dispatchEvent(new CustomEvent('studioFeatureGenerated', {
          detail: {
            type: featureType,
            title: getTitleForType(type),
            content: formattedContent
          }
        }));
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


  // Handle save action - feature is already auto-saved, just close modal
  const handleSave = async (_content: string) => {
    setIsModalOpen(false);
    setModalContent(null);
    setModalError(null);
  };

  // Handle retry - regenerate with last parameters
  const handleRetry = async () => {
    if (lastGenerationType && lastSourceIds.length > 0) {
      // Restore custom instructions for retry
      setCustomInstructions(lastCustomInstructions);
      await handleGenerate(lastGenerationType, lastSourceIds, lastCustomInstructions);
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
        <div className="p-3 mx-4 mt-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-xs text-red-700 dark:text-red-300 font-medium">
              {localError || (typeof apiError === 'string' ? apiError : apiError || 'An error occurred')}
            </p>
            <button
              onClick={() => {
                setLocalError(null);
                clearError();
              }}
              className="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 mt-1 underline cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Custom Instructions Section */}
      <div className="px-4 pt-2 pb-3 border-b border-border-default">
        <div className="flex items-center justify-between mb-2">
          <button
            onClick={() => setShowCustomInstructions(!showCustomInstructions)}
            className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            <Settings className="w-4 h-4" />
            <span>Custom Instructions</span>
            {showCustomInstructions && customInstructions && (
              <span className="text-xs bg-accent-blue/10 text-accent-blue px-2 py-0.5 rounded-full">
                Active
              </span>
            )}
          </button>
          {showCustomInstructions && customInstructions && (
            <button
              onClick={() => {
                setCustomInstructions('');
                setShowCustomInstructions(false);
              }}
              className="text-xs text-text-tertiary hover:text-text-secondary"
            >
              Clear
            </button>
          )}
        </div>
        {showCustomInstructions && (
          <textarea
            value={customInstructions}
            onChange={(e) => setCustomInstructions(e.target.value)}
            placeholder="Add custom instructions for generation (e.g., 'Focus on pages 10-12 only', 'Make it suitable for beginners')"
            className="w-full min-h-[80px] px-3 py-2 text-sm bg-surface-subtle border border-border-default rounded-lg text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-blue/20 focus:border-accent-blue resize-none"
            disabled={generating !== null || loading}
          />
        )}
      </div>

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
        onRetry={handleRetry}
        title={modalTitle}
        contentType={modalContentType}
        content={modalContent}
        loading={generating !== null}
        loadingType={generating || undefined}
        sourceCount={sourceCount}
        customInstructions={lastCustomInstructions}
        error={modalError}
      />
    </div>
  );
}

