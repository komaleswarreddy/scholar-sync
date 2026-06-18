export type SourceQuestionSummary = {
  id: string;
  source_id: string;
  question_number: number;
  section_label?: string | null;
  preview: string;
  page_hint?: number | null;
  sort_order: number;
  confidence?: string | null;
};

export type SourceQuestionDetail = SourceQuestionSummary & {
  full_text: string;
  source_title?: string | null;
};

export type SourceQuestionListResponse = {
  status: 'idle' | 'processing' | 'ready' | 'failed' | string;
  question_count: number;
  extraction_version: number;
  error?: string | null;
  source_id?: string | null;
  questions: SourceQuestionSummary[];
};
