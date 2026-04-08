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
  Settings,
  X,
  Check
} from 'lucide-react';
import { StudioCard } from './StudioCard';
import { GenerationModal, ContentType } from './GenerationModal';
import { Button } from '../ui/Button';
import { useApi } from '@/hooks/useApi';
import { useSourceContext } from '@/contexts/SourceContext';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import type { StudioReportFormat } from '@/lib/api-client';

const STUDIO_TOOLS = [
  { icon: <Network className="w-5 h-5" />, title: 'Mind Map', type: 'mind_map' },
  { icon: <FileText className="w-5 h-5" />, title: 'Reports', type: 'report' },
  { icon: <Layers className="w-5 h-5" />, title: 'Flashcards', type: 'flashcards' },
  { icon: <FileQuestion className="w-5 h-5" />, title: 'Quiz', type: 'quiz' },
  { icon: <ImageIcon className="w-5 h-5" />, title: 'Infographic', type: 'infographic' },
  { icon: <Presentation className="w-5 h-5" />, title: 'Slide Deck', type: 'slide_deck' },
];

type SlideDeckSpec = {
  format: 'detailed' | 'presenter';
  audience: 'beginner' | 'intermediate' | 'advanced' | 'executive';
  tone: 'professional' | 'friendly' | 'academic' | 'persuasive';
  length: 'short' | 'medium' | 'long';
  language: string;
  objective: string;
};

const DEFAULT_SLIDE_DECK_SPEC: SlideDeckSpec = {
  format: 'detailed',
  audience: 'intermediate',
  tone: 'professional',
  length: 'medium',
  language: 'English',
  objective: '',
};

type QuizSpec = {
  volume: 'fewer' | 'standard' | 'more';
  difficulty: 'easy' | 'medium' | 'hard';
  topicFocus: string;
};

const DEFAULT_QUIZ_SPEC: QuizSpec = {
  volume: 'standard',
  difficulty: 'medium',
  topicFocus: '',
};

type ReportSpec = {
  format: StudioReportFormat;
  retrievalFocus: string;
};

const DEFAULT_REPORT_SPEC: ReportSpec = {
  format: 'integrated',
  retrievalFocus: '',
};

const SLIDE_DECK_LANGUAGES = [
  'English',
  'Hindi',
  'Telugu',
  'Tamil',
  'Kannada',
  'Malayalam',
  'Marathi',
  'Gujarati',
  'Bengali',
  'Punjabi',
  'Urdu',
  'Spanish',
  'French',
  'German',
  'Italian',
  'Portuguese',
  'Dutch',
  'Russian',
  'Ukrainian',
  'Polish',
  'Turkish',
  'Arabic',
  'Persian',
  'Hebrew',
  'Chinese (Simplified)',
  'Chinese (Traditional)',
  'Japanese',
  'Korean',
  'Thai',
  'Vietnamese',
  'Indonesian',
  'Malay',
  'Filipino',
  'Swahili',
];

export function StudioSuite() {
  const { loading, error: apiError, errorDetails, handleRequest, clearError, apiClient } = useApi();
  const { selectedSources } = useSourceContext();
  const hasSelectedSources = selectedSources.size > 0;
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
  const [lastRetrievalFocus, setLastRetrievalFocus] = useState<string>('');
  const [lastReportFormat, setLastReportFormat] = useState<StudioReportFormat | null>(null);
  const [sourceCount, setSourceCount] = useState<number>(0);
  
  // Custom instructions state
  const [customInstructions, setCustomInstructions] = useState<string>('');
  const [showCustomInstructions, setShowCustomInstructions] = useState<boolean>(false);
  const [isSlideDeckConfigOpen, setIsSlideDeckConfigOpen] = useState<boolean>(false);
  const [slideDeckSpec, setSlideDeckSpec] = useState<SlideDeckSpec>(DEFAULT_SLIDE_DECK_SPEC);
  const [isQuizConfigOpen, setIsQuizConfigOpen] = useState<boolean>(false);
  const [quizSpec, setQuizSpec] = useState<QuizSpec>(DEFAULT_QUIZ_SPEC);
  const [isReportConfigOpen, setIsReportConfigOpen] = useState<boolean>(false);
  const [reportSpec, setReportSpec] = useState<ReportSpec>(DEFAULT_REPORT_SPEC);

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
  const formatContent = (taskType: string, result: any): string | object | null => {
    if (result?.content) {
      const content = result.content;
      // Validate content is not empty
      if (typeof content === 'string' && !content.trim()) {
        return null; // Return null to trigger error display
      }

      // Preserve full object fields (infographic structured data, image metadata, etc.).
      if (typeof result === 'object' && result !== null) {
        return {
          task_type: result.task_type || taskType,
          content,
          ...(result.infographic_data ? { infographic_data: result.infographic_data } : {}),
          ...(result.summary_bullets ? { summary_bullets: result.summary_bullets } : {}),
          ...(result.image_url ? { image_url: result.image_url } : {}),
          ...(result.image_error ? { image_error: result.image_error } : {}),
        };
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

  const buildSlideDeckInstructions = (spec: SlideDeckSpec): string => {
    const formatLabel = spec.format === 'detailed'
      ? 'Detailed deck with rich explanatory content and concrete examples'
      : 'Presenter deck with concise, high-signal bullets (still concrete, not vague titles only)';
    const lengthLabel = spec.length === 'short'
      ? '6-8 slides'
      : spec.length === 'medium'
      ? '10-12 slides'
      : '14-16 slides';

    const instructionLines = [
      'Slide deck requirements:',
      `- Format: ${formatLabel}`,
      `- Audience level: ${spec.audience}`,
      `- Tone: ${spec.tone}`,
      `- Target length: ${lengthLabel} (stay within this range)`,
      `- Language: ${spec.language}`,
      '- Bullets per slide: use **1–7** bullet lines per slide as needed—**never more than 7**; do **not** use the same number of bullets on every slide (no padding to 4 everywhere).',
      '- A single point may use **two lines** (continuation or sub-bullet under one main bullet) when it aids clarity; still cap at 7 top-level `-` bullets per slide.',
      '- Story: open with problem/topic → explain step by step → show **examples** and contrasts → **end with a dedicated conclusion slide** (main takeaways, what to remember). Slides must feel connected, not random.',
      '- Show don\'t tell: avoid empty phrases ("this is important", "many types", "affects performance"); prefer what it looks like, how it works, before/after, real examples from the source.',
      '- Hierarchy: short punchy slide titles; use Markdown **bold** on key terms or numbers in bullets; keep bullets scannable (not Word-document paragraphs).',
      '- Engagement: include at least a couple of "why" or comparison questions grounded in the material.',
      '- Output: Markdown only, one `# Slide N: Title` per slide, bullets underneath.',
    ];

    if (spec.objective.trim()) {
      instructionLines.push(
        `- Topic / deck focus: Emphasize "${spec.objective.trim()}" throughout; most slides should clearly support this focus while staying grounded in the retrieved source material.`,
      );
    } else {
      instructionLines.push(
        '- Scope: No narrow topic was specified. Cover the full breadth of the retrieved material across selected sources; distribute attention across major themes rather than one subsection.',
      );
    }
    return instructionLines.join('\n');
  };

  const buildQuizInstructions = (spec: QuizSpec): string => {
    const countRange =
      spec.volume === 'fewer'
        ? '3–4'
        : spec.volume === 'standard'
          ? '5–7'
          : '8–10';
    const difficultyBlock =
      spec.difficulty === 'easy'
        ? 'Easy: emphasize recall and simple paraphrase; use plain vocabulary; correct answers should stand out clearly from distractors.'
        : spec.difficulty === 'medium'
          ? 'Medium: mix comprehension and light application; plausible distractors; clear but not trivial wording.'
          : 'Hard: require inference, comparison, or multi-step reasoning; sophisticated distractors; precise terminology where appropriate.';

    const lines = [
      'Quiz generation requirements:',
      `1. Question count: Produce between ${countRange} questions (inclusive). Stay within this range.`,
      `2. Difficulty level (${spec.difficulty}): ${difficultyBlock}`,
    ];
    if (spec.topicFocus.trim()) {
      lines.push(
        `3. Topic focus: Prioritize questions about: "${spec.topicFocus.trim()}". Most items should clearly relate to this focus while staying grounded in the source material.`,
      );
    } else {
      lines.push(
        '3. Scope: The student did not specify a narrow topic. Cover the full breadth of the provided source material. Draw from across the retrieved context so all selected sources are represented; do not anchor the entire quiz on a single subsection.',
      );
    }
    lines.push(
      '4. Format: Each question must have exactly four options, exactly one correct_answer matching an option string, and a concise explanation. Follow the JSON schema exactly.',
    );
    return lines.join('\n');
  };

  /** Scoped instructions so the model maps only selected sources (matches API source_id filter). */
  const buildMindMapInstructions = (selectedSourceCount: number): string => {
    const lines = [
      'Mind map — scope (mandatory):',
      '- Retrieval uses only the currently selected source IDs; other uploads are excluded.',
      '- Ground every node in the retrieved excerpt; do not invent facts from outside the sources.',
      '- Structure: exactly one # heading = central hub; ## = major branches; ### and bullets = detail.',
    ];
    if (selectedSourceCount === 1) {
      lines.push(
        '- One source: center the map on that document\'s dominant theme and its key arguments, concepts, or steps.',
      );
    } else {
      lines.push(
        `- ${selectedSourceCount} sources: analyze all chosen documents together in one map.`,
        '- Find overarching themes, overlapping concepts, or sharp contrasts between texts; synthesize into a single integrated hub (not two disconnected mini-maps).',
        '- Use major branches to reflect each document\'s domain or theme when helpful, but every branch must tie back to the central hub.',
        '- Give fair coverage: if the excerpt clearly contains material from multiple sources, do not build the map from only one of them.',
      );
    }
    return lines.join('\n');
  };

  const handleMindMapGenerate = async () => {
    const n = selectedSources.size;
    const block = buildMindMapInstructions(n);
    const combined = [block, customInstructions.trim()].filter(Boolean).join('\n\n');
    await handleGenerate('mind_map', undefined, combined);
  };

  /**
   * Flashcards use broad retrieval only (STUDIO_BROAD_RETRIEVAL_QUERIES) on the server—no topic rewrite.
   * Scope here aligns the model with multi-source deck behavior.
   */
  const buildFlashcardInstructions = (selectedSourceCount: number): string => {
    const lines = [
      'Flashcards — scope (mandatory):',
      '- Retrieval uses only the currently selected source IDs; unselected uploads are excluded.',
      '- Front = question, key term, or short prompt; back = answer or concise explanation—both grounded in the retrieved excerpt.',
      '- Do not invent facts; cards must be reviewable from the source material.',
    ];
    if (selectedSourceCount === 1) {
      lines.push(
        '- Single source: prioritize core definitions, facts, and concepts from that document.',
      );
    } else {
      lines.push(
        `- ${selectedSourceCount} sources: one integrated deck across all selected materials.`,
        '- Extract important facts, definitions, and concepts from across the excerpt; give fair coverage so the deck reflects multiple sources when the excerpt contains them.',
      );
    }
    return lines.join('\n');
  };

  const handleFlashcardGenerate = async () => {
    const n = selectedSources.size;
    const block = buildFlashcardInstructions(n);
    const combined = [block, customInstructions.trim()].filter(Boolean).join('\n\n');
    await handleGenerate('flashcards', undefined, combined);
  };

  /**
   * Scope + synthesis rules for the user prompt. Per-format writing rules are enforced in
   * `packages/core/prompts/templates/studio/report_prompt.j2` via API field `report_format`.
   */
  const buildReportInstructions = (spec: ReportSpec, selectedSourceCount: number): string => {
    const formatUiName: Record<StudioReportFormat, string> = {
      integrated: 'Integrated synthesis',
      briefing: 'Executive briefing',
      study_guide: 'Study guide',
      newsletter: 'Newsletter style',
      thematic_summary: 'Thematic summary',
    };
    const lines = [
      'Tailored report — scope (mandatory):',
      '- Vector retrieval used only the currently selected sources; all other documents are excluded.',
      '- Ground every claim in the retrieved excerpt; do not invent facts from outside the sources.',
      `- Selected format: "${formatUiName[spec.format]}" — the server applies the matching REPORT FORMAT SPEC for \`${spec.format}\`.`,
    ];
    if (selectedSourceCount === 1) {
      lines.push(
        '- Single source: extract and structure the document’s dominant themes, claims, and implications.',
      );
    } else {
      lines.push(
        `- ${selectedSourceCount} sources: synthesize all selected materials into one cohesive document.`,
        '- Cross-reference facts and themes across texts where the excerpt supports it; surface overlaps and meaningful contrasts.',
        '- Avoid siloed “source A / source B” sections unless comparison is the clearest way to aid the reader.',
      );
    }
    return lines.join('\n');
  };

  const handleReportGenerate = async () => {
    const n = selectedSources.size;
    const block = buildReportInstructions(reportSpec, n);
    const combined = [block, customInstructions.trim()].filter(Boolean).join('\n\n');
    const focus = reportSpec.retrievalFocus.trim() || undefined;
    setIsReportConfigOpen(false);
    await handleGenerate('report', undefined, combined, focus, reportSpec.format);
  };

  const handleGenerate = async (
    type: string,
    sourceIdsOverride?: string[],
    customInstructionsOverride?: string,
    retrievalFocusOverride?: string,
    reportFormat?: StudioReportFormat,
  ) => {
    const sourceIds = sourceIdsOverride || Array.from(selectedSources);
    const instructions = customInstructionsOverride !== undefined ? customInstructionsOverride : customInstructions;
    const errorDetailsMessage = (errorDetails as { message?: string } | null | undefined)?.message;

    const retrievalForApi =
      retrievalFocusOverride !== undefined && retrievalFocusOverride.trim()
        ? retrievalFocusOverride.trim()
        : undefined;

    if (sourceIds.length === 0) {
      setLocalError('Please select at least one source to generate content');
      return;
    }

    if (type === 'infographic' && sourceIds.length !== 1) {
      setLocalError(
        'Infographic uses one document at a time. Select exactly one source, then try again.',
      );
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
    setLastCustomInstructions(instructions);
    setLastRetrievalFocus(
      retrievalFocusOverride !== undefined ? (retrievalFocusOverride.trim() || '') : '',
    );
    setLastReportFormat(type === 'report' ? (reportFormat ?? 'integrated') : null);
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
        apiClient.generateStudio(
          type as any,
          sourceIds,
          instructions.trim() || undefined,
          retrievalForApi,
          type === 'report' ? (reportFormat ?? 'integrated') : undefined,
        )
      );
      
      // Wait a bit for error state to update (React state updates are async)
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Check if there was an error (check both immediately and after state update)
      if (errorDetails || apiError) {
        const errorMessage = errorDetailsMessage || apiError || 'An error occurred during generation';
        setModalError(errorMessage);
        setModalContent(null);
      } else if (result) {
        const contentType = determineContentType(type, result);
        const formattedContent = formatContent(type, result);
        
        // Check if formatted content is null or empty
        if (formattedContent === null || formattedContent === undefined) {
          const errorMessage = errorDetailsMessage || apiError || 'No content was generated. The model may have been blocked or returned empty content. Please try again.';
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
        const errorMessage = errorDetailsMessage || apiError || 'No content was generated. Please check the backend logs for details.';
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
      await handleGenerate(
        lastGenerationType,
        lastSourceIds,
        lastCustomInstructions,
        lastRetrievalFocus.trim() || undefined,
        lastGenerationType === 'report' ? (lastReportFormat ?? 'integrated') : undefined,
      );
    }
  };

  const handleSlideDeckGenerate = async () => {
    const structuredSlideInstructions = buildSlideDeckInstructions(slideDeckSpec);
    const combinedInstructions = [structuredSlideInstructions, customInstructions.trim()]
      .filter(Boolean)
      .join('\n\n');
    setIsSlideDeckConfigOpen(false);
    await handleGenerate(
      'slide_deck',
      undefined,
      combinedInstructions,
      slideDeckSpec.objective.trim() || undefined,
    );
  };

  const handleQuizGenerate = async () => {
    const structuredQuizInstructions = buildQuizInstructions(quizSpec);
    const combinedInstructions = [structuredQuizInstructions, customInstructions.trim()]
      .filter(Boolean)
      .join('\n\n');
    setIsQuizConfigOpen(false);
    await handleGenerate(
      'quiz',
      undefined,
      combinedInstructions,
      quizSpec.topicFocus.trim() || undefined,
    );
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
            disabled={!hasSelectedSources}
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
              disabled={!hasSelectedSources}
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
            disabled={generating !== null || loading || !hasSelectedSources}
          />
        )}
      </div>

      {/* Studio Grid */}
      <div className="flex-1 overflow-y-auto p-4">
        {!hasSelectedSources && (
          <div className="mb-3 p-3 rounded-xl bg-surface-subtle border border-border-default">
            <p className="text-xs text-text-secondary leading-relaxed">
              Select at least one source to unlock Studio tools.
            </p>
          </div>
        )}
        <p className="text-xs text-text-tertiary mb-2">
          Infographic: select exactly one source. Flashcards, reports, mind maps, and other tools use only
          your <strong className="font-medium text-text-secondary">selected</strong> sources. Flashcards
          use broad retrieval across those sources to build one integrated deck.
        </p>
        <div className="grid grid-cols-2 gap-3">
          {STUDIO_TOOLS.map((tool) => {
            const isGenerating = generating === tool.type;
            const disabledNoSources = !hasSelectedSources;
            const infographicNeedsOne =
              tool.type === 'infographic' && selectedSources.size !== 1;
            return (
              <StudioCard
                key={tool.type}
                icon={tool.icon}
                title={tool.title}
                onClick={() => {
                  if (isGenerating) return;
                  if (tool.type === 'slide_deck') {
                    setIsSlideDeckConfigOpen(true);
                    return;
                  }
                  if (tool.type === 'quiz') {
                    setIsQuizConfigOpen(true);
                    return;
                  }
                  if (tool.type === 'mind_map') {
                    void handleMindMapGenerate();
                    return;
                  }
                  if (tool.type === 'flashcards') {
                    void handleFlashcardGenerate();
                    return;
                  }
                  if (tool.type === 'report') {
                    setIsReportConfigOpen(true);
                    return;
                  }
                  void handleGenerate(tool.type);
                }}
                disabled={isGenerating || loading || infographicNeedsOne || disabledNoSources}
                disabledHint={
                  disabledNoSources
                    ? 'Select at least one source to enable Studio generation.'
                    : infographicNeedsOne
                    ? 'Select exactly one source to create an infographic from that document.'
                    : undefined
                }
              />
            );
          })}
        </div>
      </div>

      {/* Slide Deck Customization Modal */}
      {isSlideDeckConfigOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
            onClick={() => setIsSlideDeckConfigOpen(false)}
            aria-hidden="true"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              role="dialog"
              aria-modal="true"
              className="bg-surface border border-border-default rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between p-5 border-b border-border-default">
                <h3 className="text-xl font-semibold text-text-primary">Customize Slide Deck</h3>
                <button
                  onClick={() => setIsSlideDeckConfigOpen(false)}
                  className="p-2 rounded-lg hover:bg-surface-hover text-text-secondary hover:text-text-primary"
                  aria-label="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-5 overflow-y-auto space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <button
                    onClick={() => setSlideDeckSpec((prev) => ({ ...prev, format: 'detailed' }))}
                    className={`rounded-xl border p-4 text-left transition-colors ${slideDeckSpec.format === 'detailed' ? 'border-accent-blue bg-accent-blue/10' : 'border-border-default bg-surface-subtle hover:bg-surface-hover'}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-base font-semibold text-text-primary">Detailed Deck</p>
                      {slideDeckSpec.format === 'detailed' && <Check className="w-4 h-4 text-accent-blue" />}
                    </div>
                    <p className="text-sm text-text-secondary">Comprehensive slides with context and explanations.</p>
                  </button>
                  <button
                    onClick={() => setSlideDeckSpec((prev) => ({ ...prev, format: 'presenter' }))}
                    className={`rounded-xl border p-4 text-left transition-colors ${slideDeckSpec.format === 'presenter' ? 'border-accent-blue bg-accent-blue/10' : 'border-border-default bg-surface-subtle hover:bg-surface-hover'}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-base font-semibold text-text-primary">Presenter Deck</p>
                      {slideDeckSpec.format === 'presenter' && <Check className="w-4 h-4 text-accent-blue" />}
                    </div>
                    <p className="text-sm text-text-secondary">Visual-first slides with concise talking points.</p>
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm text-text-secondary mb-2">Audience</label>
                    <select
                      value={slideDeckSpec.audience}
                      onChange={(e) => setSlideDeckSpec((prev) => ({ ...prev, audience: e.target.value as SlideDeckSpec['audience'] }))}
                      className="w-full px-3 py-2 text-sm bg-surface-subtle border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue/20 focus:border-accent-blue"
                    >
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                      <option value="executive">Executive</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-text-secondary mb-2">Tone</label>
                    <select
                      value={slideDeckSpec.tone}
                      onChange={(e) => setSlideDeckSpec((prev) => ({ ...prev, tone: e.target.value as SlideDeckSpec['tone'] }))}
                      className="w-full px-3 py-2 text-sm bg-surface-subtle border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue/20 focus:border-accent-blue"
                    >
                      <option value="professional">Professional</option>
                      <option value="friendly">Friendly</option>
                      <option value="academic">Academic</option>
                      <option value="persuasive">Persuasive</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-text-secondary mb-2">Length</label>
                    <select
                      value={slideDeckSpec.length}
                      onChange={(e) => setSlideDeckSpec((prev) => ({ ...prev, length: e.target.value as SlideDeckSpec['length'] }))}
                      className="w-full px-3 py-2 text-sm bg-surface-subtle border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue/20 focus:border-accent-blue"
                    >
                      <option value="short">Short (6-8)</option>
                      <option value="medium">Default (10-12)</option>
                      <option value="long">Long (14-16)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-text-secondary mb-2">Language</label>
                  <select
                    value={slideDeckSpec.language}
                    onChange={(e) => setSlideDeckSpec((prev) => ({ ...prev, language: e.target.value }))}
                    className="w-full px-3 py-2 text-sm bg-surface-subtle border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue/20 focus:border-accent-blue"
                  >
                    {SLIDE_DECK_LANGUAGES.map((lang) => (
                      <option key={lang} value={lang}>
                        {lang}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-text-secondary mb-2">What should this deck focus on?</label>
                  <p className="text-xs text-text-tertiary mb-2">
                    Optional. If you enter text here, we narrow vector search with a query rewriter (like Quiz topic focus),
                    then generate slides from those chunks. Leave blank to search broadly across your selected sources.
                  </p>
                  <textarea
                    value={slideDeckSpec.objective}
                    onChange={(e) => setSlideDeckSpec((prev) => ({ ...prev, objective: e.target.value }))}
                    placeholder="Describe the goal, audience outcome, and key points to emphasize."
                    className="w-full min-h-[90px] px-3 py-2 text-sm bg-surface-subtle border border-border-default rounded-lg text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-blue/20 focus:border-accent-blue resize-none"
                  />
                </div>
              </div>

              <div className="p-5 border-t border-border-default flex justify-end gap-3">
                <Button variant="secondary" onClick={() => setIsSlideDeckConfigOpen(false)}>
                  Cancel
                </Button>
                <Button variant="primary" onClick={() => void handleSlideDeckGenerate()}>
                  Generate Slide Deck
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Report customization */}
      {isReportConfigOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
            onClick={() => setIsReportConfigOpen(false)}
            aria-hidden="true"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="report-customize-title"
              className="bg-surface border border-border-default rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 px-5 py-4 border-b border-border-default bg-surface-subtle/80">
                <div className="w-10 h-10 rounded-lg bg-accent-blue/15 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5 text-accent-blue" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 id="report-customize-title" className="text-lg font-semibold text-text-primary">
                    Tailored report
                  </h3>
                  <p className="text-xs text-text-secondary mt-0.5">
                    Choose a format. Optional topic steers vector retrieval; leave blank for broad coverage
                    across selected sources.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsReportConfigOpen(false)}
                  className="p-2 rounded-lg hover:bg-surface-hover text-text-secondary hover:text-text-primary shrink-0"
                  aria-label="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-5 overflow-y-auto space-y-5">
                <div className="space-y-2 border-l-2 border-accent-blue/40 pl-4">
                  <label htmlFor="report-format" className="text-sm font-medium text-text-primary">
                    Report format
                  </label>
                  <select
                    id="report-format"
                    value={reportSpec.format}
                    onChange={(e) =>
                      setReportSpec((prev) => ({
                        ...prev,
                        format: e.target.value as ReportSpec['format'],
                      }))
                    }
                    className="w-full px-3 py-2.5 text-sm bg-surface border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue/25 focus:border-accent-blue"
                  >
                    <option value="integrated">Integrated synthesis</option>
                    <option value="briefing">Executive briefing</option>
                    <option value="study_guide">Study guide</option>
                    <option value="newsletter">Newsletter style</option>
                    <option value="thematic_summary">Thematic summary</option>
                  </select>
                </div>

                <div className="space-y-2 rounded-lg bg-surface-subtle border border-border-default p-4">
                  <label htmlFor="report-retrieval-focus" className="text-sm font-medium text-text-primary">
                    Topic for retrieval <span className="text-text-tertiary font-normal">(optional)</span>
                  </label>
                  <textarea
                    id="report-retrieval-focus"
                    value={reportSpec.retrievalFocus}
                    onChange={(e) =>
                      setReportSpec((prev) => ({ ...prev, retrievalFocus: e.target.value }))
                    }
                    placeholder="e.g. environmental policy section, or key formulas. Empty = broad queries across all selected sources."
                    rows={3}
                    className="w-full px-3 py-2 text-sm bg-surface border border-border-default rounded-lg text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-blue/20 focus:border-accent-blue resize-none"
                  />
                </div>
              </div>

              <div className="px-5 py-4 border-t border-border-default flex flex-col-reverse sm:flex-row sm:justify-end gap-2 bg-surface-subtle/50">
                <Button
                  variant="secondary"
                  onClick={() => setIsReportConfigOpen(false)}
                  className="w-full sm:w-auto"
                >
                  Cancel
                </Button>
                <Button variant="primary" onClick={() => void handleReportGenerate()} className="w-full sm:w-auto">
                  Generate report
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Quiz customization — vertical form (distinct from slide-deck card picker) */}
      {isQuizConfigOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
            onClick={() => setIsQuizConfigOpen(false)}
            aria-hidden="true"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="quiz-customize-title"
              className="bg-surface border border-border-default rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 px-5 py-4 border-b border-border-default bg-surface-subtle/80">
                <div className="w-10 h-10 rounded-lg bg-accent-purple/15 flex items-center justify-center shrink-0">
                  <FileQuestion className="w-5 h-5 text-accent-purple" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 id="quiz-customize-title" className="text-lg font-semibold text-text-primary">
                    Customize Quiz
                  </h3>
                  <p className="text-xs text-text-secondary mt-0.5">
                    Tune length and difficulty. Optional focus narrows topics; leave blank to use all selected sources.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsQuizConfigOpen(false)}
                  className="p-2 rounded-lg hover:bg-surface-hover text-text-secondary hover:text-text-primary shrink-0"
                  aria-label="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-5 overflow-y-auto space-y-5">
                <div className="space-y-2 border-l-2 border-accent-purple/40 pl-4">
                  <label htmlFor="quiz-volume" className="text-sm font-medium text-text-primary">
                    How many questions?
                  </label>
                  <select
                    id="quiz-volume"
                    value={quizSpec.volume}
                    onChange={(e) =>
                      setQuizSpec((prev) => ({
                        ...prev,
                        volume: e.target.value as QuizSpec['volume'],
                      }))
                    }
                    className="w-full px-3 py-2.5 text-sm bg-surface border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-purple/25 focus:border-accent-purple"
                  >
                    <option value="fewer">Fewer (3–4)</option>
                    <option value="standard">Standard (5–7)</option>
                    <option value="more">More (8–10)</option>
                  </select>
                </div>

                <div className="space-y-2 border-l-2 border-accent-blue/40 pl-4">
                  <label htmlFor="quiz-difficulty" className="text-sm font-medium text-text-primary">
                    Difficulty
                  </label>
                  <select
                    id="quiz-difficulty"
                    value={quizSpec.difficulty}
                    onChange={(e) =>
                      setQuizSpec((prev) => ({
                        ...prev,
                        difficulty: e.target.value as QuizSpec['difficulty'],
                      }))
                    }
                    className="w-full px-3 py-2.5 text-sm bg-surface border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue/25 focus:border-accent-blue"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>

                <div className="space-y-2 rounded-lg bg-surface-subtle border border-border-default p-4">
                  <label htmlFor="quiz-topic" className="text-sm font-medium text-text-primary">
                    What should the topic be? <span className="text-text-tertiary font-normal">(optional)</span>
                  </label>
                  <textarea
                    id="quiz-topic"
                    value={quizSpec.topicFocus}
                    onChange={(e) => setQuizSpec((prev) => ({ ...prev, topicFocus: e.target.value }))}
                    placeholder="e.g. key ideas from chapter 2, or vocabulary for your exam. Leave empty to quiz across everything in your selected sources."
                    rows={4}
                    className="w-full px-3 py-2 text-sm bg-surface border border-border-default rounded-lg text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-blue/20 focus:border-accent-blue resize-none"
                  />
                  <p className="text-xs text-text-tertiary leading-relaxed">
                    Empty field = questions span the full retrieved content from your selected documents.
                  </p>
                </div>
              </div>

              <div className="px-5 py-4 border-t border-border-default flex flex-col-reverse sm:flex-row sm:justify-end gap-2 bg-surface-subtle/50">
                <Button variant="secondary" onClick={() => setIsQuizConfigOpen(false)} className="w-full sm:w-auto">
                  Cancel
                </Button>
                <Button variant="primary" onClick={() => void handleQuizGenerate()} className="w-full sm:w-auto">
                  Generate quiz
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

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
        customInstructions={
          lastGenerationType === 'quiz' ||
          lastGenerationType === 'mind_map' ||
          lastGenerationType === 'report' ||
          lastGenerationType === 'flashcards'
            ? undefined
            : lastCustomInstructions
        }
        error={modalError}
      />
    </div>
  );
}
