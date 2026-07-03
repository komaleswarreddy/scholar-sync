'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  MoreHorizontal,
  X,
  Target,
  Award,
  Tag,
  StickyNote,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { useUserContext } from '@/contexts/UserContext';

export type FeedbackSignal =
  | 'helpful'
  | 'not_helpful'
  | 'confusing'
  | 'incomplete'
  | 'inaccurate'
  | 'off_syllabus'
  | 'expert_validated'
  | 'missing_dimension'
  | 'expert_note';

const TIER1: FeedbackSignal[] = ['helpful', 'not_helpful', 'confusing', 'incomplete'];
const DIMENSIONS = [
  'definition',
  'intuition',
  'misconceptions',
  'applications',
  'cross_concept',
  'mathematical',
  'historical',
  'exam_traps',
  'visual',
  'problem_solving',
] as const;

type MessageFeedbackBarProps = {
  messageId: string;
  compact?: boolean;
};

export function MessageFeedbackBar({ messageId, compact = false }: MessageFeedbackBarProps) {
  const { user } = useUserContext();
  const tier = user?.expertise_tier ?? 'student';
  const [signals, setSignals] = useState<FeedbackSignal[]>([]);
  const [loading, setLoading] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [expertOpen, setExpertOpen] = useState(false);
  const [textModal, setTextModal] = useState<{
    signal: FeedbackSignal;
    title: string;
    required?: boolean;
  } | null>(null);
  const [textValue, setTextValue] = useState('');
  const [selectedDimension, setSelectedDimension] = useState<string>('misconceptions');

  const refresh = useCallback(async () => {
    try {
      const rows = await apiClient.listMessageFeedback(messageId);
      setSignals(rows.map((r) => r.signal_type as FeedbackSignal));
    } catch {
      setSignals([]);
    }
  }, [messageId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const submit = async (
    signal: FeedbackSignal,
    opts?: { free_text?: string; dimension_tag?: string }
  ) => {
    setLoading(true);
    try {
      await apiClient.submitMessageFeedback(messageId, {
        signal_type: signal,
        free_text: opts?.free_text,
        dimension_tag: opts?.dimension_tag,
      });
      await refresh();
    } finally {
      setLoading(false);
      setTextModal(null);
      setTextValue('');
    }
  };

  const tier1Active = TIER1.find((s) => signals.includes(s));
  const canTier2 = ['teacher', 'tutor', 'sme'].includes(tier);
  const canTier3 = ['tutor', 'sme'].includes(tier);

  const iconBtn = (
    signal: FeedbackSignal,
    Icon: typeof ThumbsUp,
    label: string,
    active: boolean
  ) => (
    <button
      key={signal}
      type="button"
      disabled={loading}
      title={label}
      aria-label={label}
      onClick={() => {
        if (signal === 'not_helpful') {
          setTextModal({ signal, title: 'What went wrong?', required: false });
          return;
        }
        if (signal === 'inaccurate') {
          setTextModal({ signal, title: 'What was incorrect?', required: true });
          return;
        }
        if (signal === 'expert_note') {
          setTextModal({ signal, title: 'Add your correction or addition', required: true });
          return;
        }
        if (signal === 'missing_dimension') {
          void submit(signal, { dimension_tag: selectedDimension });
          return;
        }
        void submit(signal);
      }}
      className={`p-1.5 rounded-md transition-colors ${
        active
          ? 'bg-[var(--color-brand-primary)]/15 text-[var(--color-brand-text)]'
          : 'text-[var(--color-home-text-muted)] hover:bg-black/5'
      }`}
    >
      <Icon className={compact ? 'w-3.5 h-3.5' : 'w-4 h-4'} strokeWidth={1.75} />
    </button>
  );

  return (
    <div className="mt-2 flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-0.5">
        {iconBtn('helpful', ThumbsUp, 'Helpful', tier1Active === 'helpful')}
        {iconBtn('not_helpful', ThumbsDown, 'Not helpful', tier1Active === 'not_helpful')}
        {iconBtn('confusing', HelpCircle, 'Confusing', tier1Active === 'confusing')}
        {iconBtn('incomplete', MoreHorizontal, 'Incomplete', tier1Active === 'incomplete')}
        {canTier2 && (
          <button
            type="button"
            className="ml-1 text-[11px] font-medium text-[var(--color-brand-text)] hover:underline"
            onClick={() => setMoreOpen(!moreOpen)}
          >
            More feedback {moreOpen ? <ChevronUp className="inline w-3 h-3" /> : <ChevronDown className="inline w-3 h-3" />}
          </button>
        )}
        {canTier3 && (
          <button
            type="button"
            className="ml-1 text-[11px] font-medium text-purple-700 hover:underline"
            onClick={() => setExpertOpen(!expertOpen)}
          >
            Expert feedback
          </button>
        )}
      </div>

      {moreOpen && canTier2 && (
        <div className="flex items-center gap-0.5 pl-1">
          {iconBtn('inaccurate', X, 'Inaccurate', signals.includes('inaccurate'))}
          {iconBtn('off_syllabus', Target, 'Off syllabus', signals.includes('off_syllabus'))}
        </div>
      )}

      {expertOpen && canTier3 && (
        <div className="rounded-lg border border-purple-200 bg-purple-50/50 p-2 flex flex-col gap-2">
          <div className="flex items-center gap-0.5">
            {iconBtn('expert_validated', Award, 'Expert validated', signals.includes('expert_validated'))}
            {iconBtn('expert_note', StickyNote, 'Expert note', signals.includes('expert_note'))}
          </div>
          <div className="flex flex-wrap items-center gap-1">
            <Tag className="w-3.5 h-3.5 text-purple-700" />
            <select
              value={selectedDimension}
              onChange={(e) => setSelectedDimension(e.target.value)}
              className="text-xs border rounded px-1 py-0.5"
            >
              {DIMENSIONS.map((d) => (
                <option key={d} value={d}>
                  {d.replace('_', ' ')}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="text-xs font-medium text-purple-700 hover:underline"
              onClick={() => void submit('missing_dimension', { dimension_tag: selectedDimension })}
            >
              Tag missing dimension
            </button>
          </div>
        </div>
      )}

      {textModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-4">
            <h3 className="font-semibold text-sm mb-2">{textModal.title}</h3>
            <textarea
              className="w-full border rounded-lg p-2 text-sm min-h-[80px]"
              value={textValue}
              onChange={(e) => setTextValue(e.target.value)}
              placeholder="Optional details…"
            />
            <div className="flex justify-end gap-2 mt-3">
              <button type="button" className="text-sm px-3 py-1.5" onClick={() => setTextModal(null)}>
                Cancel
              </button>
              <button
                type="button"
                className="text-sm px-3 py-1.5 rounded-lg bg-[var(--color-brand-primary)] text-white"
                disabled={textModal.required && !textValue.trim()}
                onClick={() => void submit(textModal.signal, { free_text: textValue || undefined })}
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
