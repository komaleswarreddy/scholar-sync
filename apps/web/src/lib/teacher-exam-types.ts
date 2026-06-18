export type ExamBoard = 'NCERT' | 'Telangana State Board' | 'ICSE' | 'IB';

export type ExamStatus = 'draft' | 'graded' | 'archived';

export type ExamWizardStep = 1 | 2 | 3 | 4 | 5 | 6;

export type ConceptMappingStatus = 'auto_mapped' | 'needs_review' | 'edited';

export type OmrSheetStatus =
  | 'matched'
  | 'unknown_likely'
  | 'multiple_marks'
  | 'unmatched'
  | 'confirmed'
  | 'tagged_manual';

export type AnswerChoice = '-' | 'A' | 'B' | 'C' | 'D';

export interface ConceptOption {
  id: string;
  title: string;
  path: string;
}

export interface ExamQuestion {
  id: string;
  number: number;
  preview: string;
  autoDetectedPath: string;
  approvedConceptId: string | null;
  mappingStatus: ConceptMappingStatus;
}

export interface OmrStudentRow {
  id: string;
  rollNumber: number | null;
  name: string;
  displayLabel: string;
  status: OmrSheetStatus;
  message: string;
  questionsRead?: string;
  likelyRoll?: number;
  likelyName?: string;
}

export interface ExamGradingSummary {
  studentsGraded: number;
  averageScore: number;
  maxScore: number;
  weakConcepts: number;
}

export interface QuestionAnalyticsRow {
  questionId: string;
  number: number;
  conceptId: string | null;
  conceptTitle: string;
  conceptPath: string;
  correctAnswer: AnswerChoice;
  pctCorrect: number;
  pctWrong: number;
  pctUnanswered: number;
}

export interface WeakConceptAnalytics {
  conceptId: string;
  title: string;
  path: string;
  classCorrectPct: number;
  affectedQuestionNumbers: number[];
  suggestions: string[];
}

export interface ClassExamAnalytics {
  examId: string;
  examName: string;
  subject: string;
  classNum: number;
  section: string;
  examDate: string;
  board: ExamBoard;
  summary: ExamGradingSummary;
  totalQuestions: number;
  classCorrectPct: number;
  highestMissRatePct: number;
  questions: QuestionAnalyticsRow[];
  weakConcepts: WeakConceptAnalytics[];
}

export interface TeacherExam {
  id: string;
  status: ExamStatus;
  createdAt: string;
  updatedAt: string;
  archivedAt?: string;

  board: ExamBoard;
  classNum: number;
  subject: string;
  section: string;
  examName: string;
  examDate: string;
  marksCorrect: number;
  marksWrong: number;
  marksUnanswered: number;

  wizardStep: ExamWizardStep;
  questionPaperUploaded: boolean;
  questionPaperFileName?: string;
  questions: ExamQuestion[];
  answerKeyMode: 'upload' | 'manual';
  answerKeyUploaded: boolean;
  answerKeyFileName?: string;
  answers: Record<string, AnswerChoice>;
  omrUploaded: boolean;
  omrFileCount?: number;
  omrRows: OmrStudentRow[];
  gradingSummary?: ExamGradingSummary;
}

export interface ExamWizardDraft {
  examId: string | null;
  step: ExamWizardStep;
  board: ExamBoard;
  classNum: number | null;
  subject: string;
  section: string;
  examName: string;
  examDate: string;
  marksCorrect: number;
  marksWrong: number;
  marksUnanswered: number;
  questionPaperUploaded: boolean;
  questionPaperFileName?: string;
  questions: ExamQuestion[];
  answerKeyMode: 'upload' | 'manual';
  answerKeyUploaded: boolean;
  answerKeyFileName?: string;
  answers: Record<string, AnswerChoice>;
  omrUploaded: boolean;
  omrFileCount?: number;
  omrRows: OmrStudentRow[];
}

export type ExamsListTab = 'upcoming' | 'graded' | 'archived';

export const WIZARD_STEP_LABELS: Record<ExamWizardStep, string> = {
  1: 'Exam details',
  2: 'Question paper',
  3: 'Concept mapping',
  4: 'Answer key',
  5: 'OMR sheets',
  6: 'Complete',
};

export function getRemainingStepLabel(step: ExamWizardStep): string {
  switch (step) {
    case 1:
      return 'Exam details left';
    case 2:
      return 'Question paper left';
    case 3:
      return 'Concept mapping left';
    case 4:
      return 'Answer key left';
    case 5:
      return 'OMR sheets left';
    default:
      return 'Setup complete';
  }
}
