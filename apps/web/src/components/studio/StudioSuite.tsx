/**
 * Studio Suite Component
 * 
 * Right sidebar top section with Studio generation tools.
 * Uses placeholder functionality until API keys are added.
 */

'use client';

import { useEffect, useState } from 'react';
import { 
  FileQuestion, 
  FileText, 
  AlertCircle,
  Settings,
  X,
  Check
} from 'lucide-react';
import { StudioCard } from './StudioCard';
import { Button } from '../ui/Button';
import { useValidSelectedSourceIds } from '@/hooks/useValidSelectedSourceIds';
import { useStudioChatBridge } from '@/contexts/StudioChatBridgeContext';
import { useStudioGeneration } from '@/contexts/StudioGenerationContext';
import { useNotebookContextOptional } from '@/contexts/NotebookContext';
import {
  NOTEBOOK_STUDIO_TOOL_TONES,
  NOTEBOOK_STUDIO_TOOLS,
  PROBLEM_SOLVER_NOTEBOOK_STUDIO_TOOLS,
  PROBLEM_SOLVER_STUDIO_PRIMARY_TYPES,
  PROBLEM_SOLVER_STUDIO_SECONDARY_TYPES,
  TUTOR_NOTEBOOK_STUDIO_TOOLS,
  TUTOR_STUDIO_PRIMARY_TYPES,
  TUTOR_STUDIO_SECONDARY_TYPES,
} from '@/lib/notebook-studio-tools';
import { NotebookSectionHeader } from '@/components/notebook/NotebookSectionHeader';
import {
  NOTEBOOK_STUDIO_TONE_STYLES,
} from '@/lib/notebook-ui-tokens';

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

export function StudioSuite({ layout = 'default' }: { layout?: 'default' | 'notebook' }) {
  const isNotebookLayout = layout === 'notebook';
  const notebookCtx = useNotebookContextOptional();
  const isTutorNotebook = notebookCtx?.notebook.mode === 'tutor';
  const isProblemSolverNotebook = notebookCtx?.notebook.mode === 'problem_solver';
  const notebookStudioTools =
    isNotebookLayout && isProblemSolverNotebook
      ? PROBLEM_SOLVER_NOTEBOOK_STUDIO_TOOLS
      : isNotebookLayout && isTutorNotebook
        ? TUTOR_NOTEBOOK_STUDIO_TOOLS
        : NOTEBOOK_STUDIO_TOOLS;
  const [studioExpanded, setStudioExpanded] = useState(false);
  const isCollapsibleNotebookStudio =
    isNotebookLayout && (isTutorNotebook || isProblemSolverNotebook);
  const studioPrimaryTypes = isProblemSolverNotebook
    ? PROBLEM_SOLVER_STUDIO_PRIMARY_TYPES
    : TUTOR_STUDIO_PRIMARY_TYPES;
  const studioSecondaryTypes = isProblemSolverNotebook
    ? PROBLEM_SOLVER_STUDIO_SECONDARY_TYPES
    : TUTOR_STUDIO_SECONDARY_TYPES;
  const visibleTutorTools = isCollapsibleNotebookStudio
    ? studioExpanded
      ? notebookStudioTools
      : notebookStudioTools.filter((tool) => studioPrimaryTypes.includes(tool.type))
    : notebookStudioTools;
  const studioGridClass = isCollapsibleNotebookStudio
    ? studioExpanded
      ? isProblemSolverNotebook
        ? 'notebook-studio-grid notebook-studio-grid--count-3'
        : 'notebook-studio-grid notebook-studio-grid--count-4'
      : 'notebook-studio-grid notebook-studio-grid--count-2'
    : 'notebook-studio-grid';
  const { validSelectedIds, validSelectedCount } = useValidSelectedSourceIds();
  const { hasChatContext } = useStudioChatBridge();
  const {
    generate,
    generating,
    loading,
    apiError,
    clearError,
    validationError,
    clearValidationError,
  } = useStudioGeneration();
  const hasSelectedSources =
    validSelectedCount > 0 || (isCollapsibleNotebookStudio && isNotebookLayout);
  
  // Custom instructions state
  const [customInstructions, setCustomInstructions] = useState<string>('');
  const [showCustomInstructions, setShowCustomInstructions] = useState<boolean>(false);
  const [isSlideDeckConfigOpen, setIsSlideDeckConfigOpen] = useState<boolean>(false);
  const [slideDeckSpec, setSlideDeckSpec] = useState<SlideDeckSpec>(DEFAULT_SLIDE_DECK_SPEC);
  const [isQuizConfigOpen, setIsQuizConfigOpen] = useState<boolean>(false);
  const [quizSpec, setQuizSpec] = useState<QuizSpec>(DEFAULT_QUIZ_SPEC);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    let intent: any = null;
    try {
      const raw = window.localStorage.getItem('studioIntentV1');
      if (raw) intent = JSON.parse(raw);
    } catch {
      intent = null;
    }
    if (!intent || typeof intent !== 'object') return;

    // Clear intent immediately to avoid loops.
    try {
      window.localStorage.removeItem('studioIntentV1');
    } catch {
      // ignore
    }

    const type = String(intent.type || '');
    if (!type) return;

    // If no sources are selected, we keep behavior unchanged: Studio will show its normal hint.
    if (!hasSelectedSources) return;

    if (type === 'slide_deck') {
      setIsSlideDeckConfigOpen(true);
      return;
    }
    if (type === 'quiz') {
      setIsQuizConfigOpen(true);
      return;
    }
    if (type === 'mind_map') {
      void handleMindMapGenerate();
      return;
    }
    if (type === 'flashcards') {
      void handleFlashcardGenerate();
      return;
    }
    void generate({ taskType: type });
  }, [generate, hasSelectedSources]); // intentionally not depending on local config state

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
    const n = validSelectedCount;
    const block = buildMindMapInstructions(n);
    const combined = [block, customInstructions.trim()].filter(Boolean).join('\n\n');
    await generate({ taskType: 'mind_map', instructions: combined });
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
    const n = validSelectedCount;
    const block = buildFlashcardInstructions(n);
    const combined = [block, customInstructions.trim()].filter(Boolean).join('\n\n');
    await generate({ taskType: 'flashcards', instructions: combined });
  };

  const handleSlideDeckGenerate = async () => {
    const structuredSlideInstructions = buildSlideDeckInstructions(slideDeckSpec);
    const combinedInstructions = [structuredSlideInstructions, customInstructions.trim()]
      .filter(Boolean)
      .join('\n\n');
    setIsSlideDeckConfigOpen(false);
    await generate({
      taskType: 'slide_deck',
      instructions: combinedInstructions,
      retrievalFocus: slideDeckSpec.objective.trim() || undefined,
    });
  };

  const handleQuizGenerate = async () => {
    const structuredQuizInstructions = buildQuizInstructions(quizSpec);
    const combinedInstructions = [structuredQuizInstructions, customInstructions.trim()]
      .filter(Boolean)
      .join('\n\n');
    setIsQuizConfigOpen(false);
    await generate({
      taskType: 'quiz',
      instructions: combinedInstructions,
      retrievalFocus: quizSpec.topicFocus.trim() || undefined,
    });
  };

  const handleToolClick = (toolType: string) => {
    if (generating === toolType) return;
    if (toolType === 'slide_deck') {
      setIsSlideDeckConfigOpen(true);
      return;
    }
    if (toolType === 'quiz') {
      setIsQuizConfigOpen(true);
      return;
    }
    if (toolType === 'mind_map') {
      void handleMindMapGenerate();
      return;
    }
    if (toolType === 'flashcards') {
      void handleFlashcardGenerate();
      return;
    }
    void generate({ taskType: toolType });
  };

  const renderToolDisabled = (toolType: string) => {
    const disabledNoSources = !hasSelectedSources;
    return {
      disabled: generating === toolType || loading || disabledNoSources,
      disabledNoSources,
    };
  };

  if (isNotebookLayout) {
    return (
      <div className="flex flex-col">
        {isCollapsibleNotebookStudio ? (
          <NotebookSectionHeader
            title="STUDIO"
            subtitle="Create from this notebook"
            actionLabel={studioExpanded ? 'Show less' : 'View all'}
            onAction={() => setStudioExpanded((open) => !open)}
            showAction={studioSecondaryTypes.length > 0}
          />
        ) : (
          <>
            <div className="notebook-col-header px-4 pt-3 pb-1">
              <span>STUDIO</span>
            </div>
            <p className="px-4 text-[12px] text-[var(--color-home-text-muted)] mb-3">
              Create from this notebook
            </p>
          </>
        )}

        {(validationError || apiError) && (
          <div className="mx-4 mb-3 p-2.5 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-red-700 flex-1">
              {validationError ||
                (typeof apiError === 'string' ? apiError : apiError || 'An error occurred')}
            </p>
          </div>
        )}

        {!hasSelectedSources && !isCollapsibleNotebookStudio && (
          <p className="px-4 pb-2 text-[11px] text-[var(--color-home-text-muted)]">
            Select sources to enable Studio tools.
          </p>
        )}

        <div className={`${studioGridClass} px-4 pb-4`}>
          {(isCollapsibleNotebookStudio ? visibleTutorTools : notebookStudioTools).map((tool) => {
            const { disabled } = renderToolDisabled(tool.type);
            const tone = NOTEBOOK_STUDIO_TOOL_TONES[tool.type] || 'green';
            const toneStyle = NOTEBOOK_STUDIO_TONE_STYLES[tone];
            const isGenerating = generating === tool.type;
            const Icon = tool.icon;
            return (
              <button
                key={tool.type}
                type="button"
                disabled={disabled}
                onClick={() => handleToolClick(tool.type)}
                className="notebook-studio-card disabled:opacity-45 disabled:cursor-not-allowed"
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center mb-2"
                  style={{ backgroundColor: toneStyle.bg, color: toneStyle.color }}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <p className="text-[13px] font-semibold text-[var(--color-home-text)]">{tool.title}</p>
                <p className="text-[11px] text-[var(--color-brand-text)] mt-0.5">
                  {isGenerating ? 'Generating…' : 'Tap to generate'}
                </p>
              </button>
            );
          })}
        </div>

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
                      <p className="text-base font-semibold text-text-primary">Detailed Deck</p>
                    </button>
                    <button
                      onClick={() => setSlideDeckSpec((prev) => ({ ...prev, format: 'presenter' }))}
                      className={`rounded-xl border p-4 text-left transition-colors ${slideDeckSpec.format === 'presenter' ? 'border-accent-blue bg-accent-blue/10' : 'border-border-default bg-surface-subtle hover:bg-surface-hover'}`}
                    >
                      <p className="text-base font-semibold text-text-primary">Presenter Deck</p>
                    </button>
                  </div>
                  <textarea
                    value={slideDeckSpec.objective}
                    onChange={(e) => setSlideDeckSpec((prev) => ({ ...prev, objective: e.target.value }))}
                    placeholder="Optional focus for this deck"
                    className="w-full min-h-[90px] px-3 py-2 text-sm bg-surface-subtle border border-border-default rounded-lg resize-none"
                  />
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

        {isQuizConfigOpen && (
          <>
            <div className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm" onClick={() => setIsQuizConfigOpen(false)} aria-hidden="true" />
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
              <div role="dialog" aria-modal="true" className="bg-surface border border-border-default rounded-xl shadow-2xl w-full max-w-md p-5" onClick={(e) => e.stopPropagation()}>
                <h3 className="text-lg font-semibold text-text-primary mb-4">Customize Quiz</h3>
                <select
                  value={quizSpec.volume}
                  onChange={(e) => setQuizSpec((prev) => ({ ...prev, volume: e.target.value as QuizSpec['volume'] }))}
                  className="w-full px-3 py-2 text-sm border border-border-default rounded-lg mb-3"
                >
                  <option value="fewer">Fewer (3–4)</option>
                  <option value="standard">Standard (5–7)</option>
                  <option value="more">More (8–10)</option>
                </select>
                <select
                  value={quizSpec.difficulty}
                  onChange={(e) => setQuizSpec((prev) => ({ ...prev, difficulty: e.target.value as QuizSpec['difficulty'] }))}
                  className="w-full px-3 py-2 text-sm border border-border-default rounded-lg mb-4"
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
                <div className="flex justify-end gap-2">
                  <Button variant="secondary" onClick={() => setIsQuizConfigOpen(false)}>Cancel</Button>
                  <Button variant="primary" onClick={() => void handleQuizGenerate()}>Generate</Button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    );
  }

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
      {(validationError || apiError) && (
        <div className="p-3 mx-4 mt-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-xs text-red-700 dark:text-red-300 font-medium">
              {validationError ||
                (typeof apiError === 'string' ? apiError : apiError || 'An error occurred')}
            </p>
            <button
              onClick={() => {
                clearValidationError();
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
          {hasChatContext ? (
            <>
              With an active chat, Studio uses{' '}
              <strong className="font-medium text-text-secondary">chat + selected sources</strong> (~60/40).
            </>
          ) : (
            <>
              Tools use your <strong className="font-medium text-text-secondary">selected</strong> sources.
            </>
          )}{' '}
          Highlight text in chat for selection-only generation. Flashcards use broad retrieval across
          selected sources.
        </p>
        <div className="grid grid-cols-2 gap-3">
          {NOTEBOOK_STUDIO_TOOLS.map((tool) => {
            const isGenerating = generating === tool.type;
            const disabledNoSources = !hasSelectedSources;
            const Icon = tool.icon;
            return (
              <StudioCard
                key={tool.type}
                icon={<Icon className="w-5 h-5" />}
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
                  void generate({ taskType: tool.type });
                }}
                disabled={isGenerating || loading || disabledNoSources}
                disabledHint={
                  disabledNoSources
                    ? 'Select at least one source to enable Studio generation.'
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

    </div>
  );
}
