import { CONCEPT_CATALOG, getConceptById } from './teacher-exam-mock-data';
import { getExamById } from './teacher-exam-storage';
import type {
  AnswerChoice,
  ClassExamAnalytics,
  QuestionAnalyticsRow,
  TeacherExam,
  WeakConceptAnalytics,
} from './teacher-exam-types';

const WEAK_CONCEPT_IDS = new Set(['c-n2', 'c-mom', 'c-trig']);

export const CONCEPT_REMEDIATION_SUGGESTIONS: Record<string, string[]> = {
  'c-n1': [
    "Re-teach inertia with everyday examples (seatbelt, sudden brake).",
    'Assign 8 MCQs from NCERT Ch.9 on Newton\'s First Law.',
    'Review Q1–Q3 common errors in the next class.',
  ],
  'c-n2': [
    'Re-teach F=ma with worked examples and free-body diagrams.',
    'Assign 10 MCQs from NCERT Ch.9 on Newton\'s Second Law.',
    'Review Q6–Q8 common errors where students confused mass and weight.',
  ],
  'c-n3': [
    'Pair-action/reaction demos (balloon rocket, skaters).',
    'Assign 6 MCQs on action-reaction pairs.',
    'Clarify that action-reaction forces act on different bodies.',
  ],
  'c-kin': [
    'Practice SUVAT problems with timed drills.',
    'Assign 10 kinematics MCQs from previous year papers.',
    'Review sign conventions for acceleration in 1D motion.',
  ],
  'c-mom': [
    'Re-teach conservation of momentum with collision demos.',
    'Assign 8 problems on elastic and inelastic collisions.',
    'Review Q12–Q15 where students missed system boundary.',
  ],
  'c-pe': [
    'Revisit PE = mgh with height reference level examples.',
    'Assign 6 MCQs on gravitational potential energy.',
    'Connect PE graphs to motion in vertical direction.',
  ],
  'c-ke': [
    'Practice KE = ½mv² with unit conversions.',
    'Assign 8 energy transformation problems.',
    'Review when KE is conserved vs when work is done.',
  ],
  'c-ph': [
    'Re-teach pH scale with indicator colour chart activity.',
    'Assign 10 MCQs on acids, bases, and pH calculations.',
    'Review logarithmic nature of pH in a short recap.',
  ],
  'c-acid': [
    'Compare strong vs weak acids with conductivity demo.',
    'Assign 8 MCQs on neutralization reactions.',
    'Review common errors in balancing acid-base equations.',
  ],
  'c-trig': [
    'Re-teach sin²θ + cos²θ = 1 with unit circle proofs.',
    'Assign 12 identity-based problems from NCERT Ch.8.',
    'Review Q18–Q20 where students mixed up complementary angles.',
  ],
};

const DEFAULT_SUGGESTIONS = [
  'Schedule a 15-minute recap in the next class period.',
  'Assign targeted practice MCQs from the textbook chapter.',
  'Review the most-missed questions with worked solutions.',
];

function hashSeed(input: string): number {
  let h = 0;
  for (let i = 0; i < input.length; i++) {
    h = (h << 5) - h + input.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

function seededPct(examId: string, questionId: string, slot: 0 | 1 | 2): number {
  const base = hashSeed(`${examId}:${questionId}:${slot}`) % 100;
  return base;
}

function resolveConceptForQuestion(
  question: TeacherExam['questions'][number],
): { id: string | null; title: string; path: string } {
  const mapped = getConceptById(question.approvedConceptId);
  if (mapped) {
    return { id: mapped.id, title: mapped.title, path: mapped.path };
  }
  const pathParts = question.autoDetectedPath.split(' > ');
  const title = pathParts[pathParts.length - 1] ?? question.autoDetectedPath;
  return { id: question.approvedConceptId, title, path: question.autoDetectedPath };
}

function buildQuestionStats(
  exam: TeacherExam,
  question: TeacherExam['questions'][number],
): QuestionAnalyticsRow {
  const concept = resolveConceptForQuestion(question);
  const correctAnswer = (exam.answers[question.id] ?? 'A') as AnswerChoice;
  const isWeakConcept = concept.id ? WEAK_CONCEPT_IDS.has(concept.id) : question.number % 7 === 0;

  let pctCorrect: number;
  let pctWrong: number;
  let pctUnanswered: number;

  if (isWeakConcept) {
    const raw = 28 + (seededPct(exam.id, question.id, 0) % 25);
    pctCorrect = Math.min(raw, 55);
    pctUnanswered = 5 + (seededPct(exam.id, question.id, 1) % 12);
    pctWrong = 100 - pctCorrect - pctUnanswered;
  } else {
    pctCorrect = 55 + (seededPct(exam.id, question.id, 0) % 31);
    pctUnanswered = 2 + (seededPct(exam.id, question.id, 1) % 8);
    pctWrong = 100 - pctCorrect - pctUnanswered;
  }

  return {
    questionId: question.id,
    number: question.number,
    conceptId: concept.id,
    conceptTitle: concept.title,
    conceptPath: concept.path,
    correctAnswer,
    pctCorrect,
    pctWrong,
    pctUnanswered,
  };
}

function aggregateWeakConcepts(
  questions: QuestionAnalyticsRow[],
): WeakConceptAnalytics[] {
  const byConcept = new Map<
    string,
    {
      conceptId: string;
      title: string;
      path: string;
      correctSum: number;
      count: number;
      questionNumbers: number[];
    }
  >();

  for (const q of questions) {
    const key = q.conceptId ?? q.conceptPath;
    const existing = byConcept.get(key);
    if (existing) {
      existing.correctSum += q.pctCorrect;
      existing.count += 1;
      existing.questionNumbers.push(q.number);
    } else {
      byConcept.set(key, {
        conceptId: q.conceptId ?? key,
        title: q.conceptTitle,
        path: q.conceptPath,
        correctSum: q.pctCorrect,
        count: 1,
        questionNumbers: [q.number],
      });
    }
  }

  const weak: WeakConceptAnalytics[] = [];

  for (const entry of byConcept.values()) {
    const classCorrectPct = Math.round(entry.correctSum / entry.count);
    if (classCorrectPct >= 60) continue;

    const catalogMatch = CONCEPT_CATALOG.find(
      (c) => c.id === entry.conceptId || c.title === entry.title,
    );
    const suggestionKey = catalogMatch?.id ?? entry.conceptId;

    weak.push({
      conceptId: entry.conceptId,
      title: entry.title,
      path: entry.path,
      classCorrectPct,
      affectedQuestionNumbers: [...entry.questionNumbers].sort((a, b) => a - b),
      suggestions:
        CONCEPT_REMEDIATION_SUGGESTIONS[suggestionKey] ?? DEFAULT_SUGGESTIONS,
    });
  }

  return weak.sort((a, b) => a.classCorrectPct - b.classCorrectPct);
}

export function buildClassExamAnalytics(exam: TeacherExam): ClassExamAnalytics {
  const questions = exam.questions.map((q) => buildQuestionStats(exam, q));
  const sortedQuestions = [...questions].sort((a, b) => a.pctCorrect - b.pctCorrect);

  const classCorrectPct =
    questions.length > 0
      ? Math.round(
          questions.reduce((sum, q) => sum + q.pctCorrect, 0) / questions.length,
        )
      : 0;

  const highestMissRatePct =
    questions.length > 0
      ? Math.max(...questions.map((q) => q.pctWrong))
      : 0;

  const weakConcepts = aggregateWeakConcepts(questions);

  const summary = exam.gradingSummary ?? {
    studentsGraded: exam.omrRows.length || 28,
    averageScore: 14.2,
    maxScore: 20,
    weakConcepts: weakConcepts.length,
  };

  return {
    examId: exam.id,
    examName: exam.examName,
    subject: exam.subject,
    classNum: exam.classNum,
    section: exam.section,
    examDate: exam.examDate,
    board: exam.board,
    summary: {
      ...summary,
      weakConcepts: weakConcepts.length,
    },
    totalQuestions: questions.length,
    classCorrectPct,
    highestMissRatePct,
    questions: sortedQuestions,
    weakConcepts,
  };
}

export function getClassExamAnalytics(examId: string): ClassExamAnalytics | null {
  const exam = getExamById(examId);
  if (!exam) return null;
  if (exam.status !== 'graded' && exam.status !== 'archived') return null;
  if (!exam.gradingSummary && exam.status !== 'archived') return null;
  return buildClassExamAnalytics(exam);
}
