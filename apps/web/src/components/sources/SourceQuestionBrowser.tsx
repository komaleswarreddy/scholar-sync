'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { RichMarkdown } from '@/components/common/RichMarkdown';
import { useProblemSolverContext } from '@/contexts/ProblemSolverContext';
import {
  useExtractSourceQuestions,
  useSourceQuestionDetail,
  useSourceQuestions,
} from '@/hooks/useSourceQuestions';
import type { SourceQuestionSummary } from '@/types/source-question';
import { getUserFriendlyMessage, handleApiError } from '@/lib/error-handler';

type View = 'grid' | 'detail';

type Props = {
  sourceId: string;
  sourceTitle: string;
  onBack: () => void;
};

const EXTRACT_SLOW_MS = 25_000;

export function SourceQuestionBrowser({ sourceId, sourceTitle, onBack }: Props) {
  const { submitProblem } = useProblemSolverContext();
  const [view, setView] = useState<View>('grid');
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);
  const [proceeding, setProceeding] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [slowExtract, setSlowExtract] = useState(false);
  const extractStarted = useRef(false);

  const { data, isLoading, isError, refetch, isFetching } = useSourceQuestions(sourceId);
  const { mutate: runExtract, isPending: extractPending } = useExtractSourceQuestions(sourceId);
  const { data: detail, isLoading: detailLoading } = useSourceQuestionDetail(
    sourceId,
    selectedQuestionId,
    view === 'detail',
  );

  useEffect(() => {
    extractStarted.current = false;
    setExtractError(null);
    setView('grid');
    setSelectedQuestionId(null);
  }, [sourceId]);

  const triggerExtract = useCallback(
    (force = false) => {
      setExtractError(null);
      setSlowExtract(false);
      runExtract(force, {
        onError: (err) => {
          const apiError = handleApiError(err);
          setExtractError(getUserFriendlyMessage(apiError));
          extractStarted.current = false;
        },
      });
    },
    [runExtract],
  );

  // Auto-extract once per source visit when no questions exist yet.
  useEffect(() => {
    if (!data || extractPending || extractStarted.current || isFetching) return;
    const hasQuestions = (data.questions?.length ?? 0) > 0;
    if (hasQuestions) return;
    if ((data.question_count ?? 0) > 0) {
      void refetch();
      return;
    }
    if (data.status === 'failed') return;
    if (data.status === 'processing') return;
    if (data.status === 'ready') return;

    extractStarted.current = true;
    triggerExtract(false);
  }, [data, extractPending, isFetching, refetch, triggerExtract]);

  const questions = data?.questions ?? [];
  const hasQuestions = questions.length > 0;
  const status = data?.status ?? (isLoading ? 'idle' : 'failed');
  const extracting =
    !hasQuestions &&
    (extractPending || status === 'processing' || (isLoading && !data));

  useEffect(() => {
    if (!extracting) {
      setSlowExtract(false);
      return;
    }
    const timer = window.setTimeout(() => setSlowExtract(true), EXTRACT_SLOW_MS);
    return () => window.clearTimeout(timer);
  }, [extracting]);

  const handleProceed = async () => {
    if (!detail?.full_text) return;
    setProceeding(true);
    try {
      await submitProblem(detail.full_text, 'text', [
        { source_id: sourceId, question_id: detail.id, file_name: sourceTitle },
      ]);
      window.dispatchEvent(new CustomEvent('problemSolverFocusChat'));
    } finally {
      setProceeding(false);
    }
  };

  const openQuestion = (question: SourceQuestionSummary) => {
    setSelectedQuestionId(question.id);
    setView('detail');
  };

  return (
    <div className="flex flex-col min-h-0 h-full bg-white">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border-default flex-shrink-0">
        <button
          type="button"
          className="p-1 rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-muted"
          onClick={view === 'detail' ? () => setView('grid') : onBack}
          aria-label={view === 'detail' ? 'Back to questions' : 'Back to sources'}
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="min-w-0 flex-1">
          <p className="text-xs text-text-secondary truncate">Questions</p>
          <p className="text-sm font-medium truncate text-text-primary">{sourceTitle}</p>
        </div>
        {view === 'grid' ? (
          <button
            type="button"
            className="p-1.5 rounded-md text-text-secondary hover:text-text-primary"
            onClick={() => {
              extractStarted.current = true;
              triggerExtract(true);
            }}
            disabled={extractPending || extracting}
            aria-label="Re-extract questions"
          >
            <RefreshCw className={`w-4 h-4 ${extractPending || extracting ? 'animate-spin' : ''}`} />
          </button>
        ) : null}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-3">
        {view === 'grid' ? (
          <>
            {extracting ? (
              <div className="flex flex-col items-center justify-center gap-2 py-12 text-text-secondary text-sm">
                <Loader2 className="w-5 h-5 animate-spin text-[var(--color-brand-text,#0f7a52)]" />
                <p>Extracting questions…</p>
                {slowExtract ? (
                  <p className="text-xs text-center max-w-[240px]">
                    Still working — large papers can take up to a minute.
                  </p>
                ) : null}
              </div>
            ) : null}

            {!extracting && (extractError || isError || status === 'failed') ? (
              <div className="text-sm text-red-600 space-y-3 py-4">
                <p>{extractError || data?.error || 'Could not extract questions from this file.'}</p>
                <Button size="sm" variant="secondary" onClick={() => triggerExtract(true)}>
                  Try again
                </Button>
              </div>
            ) : null}

            {hasQuestions ? (
              <div className="source-question-list">
                {questions.map((q) => (
                  <button
                    key={q.id}
                    type="button"
                    className="source-question-card"
                    onClick={() => openQuestion(q)}
                  >
                    <span className="source-question-card__number">Q{q.question_number}</span>
                  </button>
                ))}
              </div>
            ) : null}

            {!extracting && !hasQuestions && status === 'ready' ? (
              <div className="text-sm text-text-secondary space-y-3 py-4">
                <p>No questions found in this document.</p>
                <Button size="sm" variant="secondary" onClick={() => triggerExtract(true)}>
                  Re-extract
                </Button>
              </div>
            ) : null}

            {!extracting && !hasQuestions && status === 'idle' && !extractError && !isError ? (
              <div className="flex flex-col items-center justify-center gap-3 py-12 text-sm text-text-secondary">
                <Loader2 className="w-5 h-5 animate-spin text-[var(--color-brand-text,#0f7a52)]" />
                <p>Preparing questions…</p>
              </div>
            ) : null}
          </>
        ) : (
          <div className="flex flex-col gap-4">
            {detailLoading || !detail ? (
              <div className="flex items-center gap-2 text-sm text-text-secondary py-8">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading question…
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-text-primary">
                    Q{detail.question_number}
                  </span>
                  {detail.section_label ? (
                    <span className="source-question-card__badge">{detail.section_label}</span>
                  ) : null}
                  {detail.confidence === 'low' ? (
                    <span className="text-xs text-amber-600">Low confidence</span>
                  ) : null}
                </div>
                <RichMarkdown
                  content={detail.full_text}
                  variant="source-question"
                  className="text-sm"
                />
                <div className="flex gap-2 pt-2">
                  <Button variant="secondary" size="sm" onClick={() => setView('grid')}>
                    Back
                  </Button>
                  <Button size="sm" onClick={() => void handleProceed()} disabled={proceeding}>
                    {proceeding ? 'Starting…' : 'Proceed to solve'}
                  </Button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
