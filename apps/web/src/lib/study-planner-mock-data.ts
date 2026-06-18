import type {
  ChapterOption,
  InstituteScheduleRow,
  ModuleStatus,
  StudyModule,
  StudyPlan,
  StudyPlanSubject,
  StudyPlanSubjectId,
} from './study-planner-types';
import { PLAN_DEMO_TODAY } from './study-planner-utils';

export const STUDY_PLAN_SUBJECTS: StudyPlanSubject[] = [
  { id: 'physics', label: 'Physics', apiKey: 'science' },
  { id: 'chemistry', label: 'Chemistry', apiKey: 'science' },
  { id: 'mathematics', label: 'Mathematics', apiKey: 'mathematics' },
  { id: 'biology', label: 'Biology', apiKey: 'science' },
];

export const INSTITUTE_WEEK_SCHEDULE: InstituteScheduleRow[] = [
  {
    subject: 'Physics',
    topic: 'Motion',
    chapterLabel: 'Ch. 3',
    subjectKey: 'science',
    chapterNo: 3,
  },
  {
    subject: 'Chemistry',
    topic: 'Acids & Bases',
    chapterLabel: 'Ch. 5',
    subjectKey: 'science',
    chapterNo: 5,
  },
  {
    subject: 'Mathematics',
    topic: 'Trigonometry',
    chapterLabel: 'Ch. 8',
    subjectKey: 'mathematics',
    chapterNo: 8,
  },
  {
    subject: 'Biology',
    topic: 'Life Processes',
    chapterLabel: 'Ch. 6',
    subjectKey: 'science',
    chapterNo: 6,
  },
];

export const CHAPTER_FALLBACK: Record<StudyPlanSubjectId, ChapterOption[]> = {
  physics: [
    { chapterNo: 1, label: 'Ch. 1 · Light — Reflection' },
    { chapterNo: 2, label: 'Ch. 2 · Light — Refraction' },
    { chapterNo: 3, label: 'Ch. 3 · Human Eye' },
    { chapterNo: 4, label: 'Ch. 4 · Electricity' },
    { chapterNo: 5, label: 'Ch. 5 · Magnetic Effects' },
    { chapterNo: 6, label: 'Ch. 6 · Energy Sources' },
  ],
  chemistry: [
    { chapterNo: 1, label: 'Ch. 1 · Chemical Reactions' },
    { chapterNo: 2, label: 'Ch. 2 · Acids, Bases & Salts' },
    { chapterNo: 3, label: 'Ch. 3 · Metals & Non-metals' },
    { chapterNo: 4, label: 'Ch. 4 · Carbon Compounds' },
    { chapterNo: 5, label: 'Ch. 5 · Periodic Classification' },
  ],
  mathematics: [
    { chapterNo: 1, label: 'Ch. 1 · Real Numbers' },
    { chapterNo: 2, label: 'Ch. 2 · Polynomials' },
    { chapterNo: 3, label: 'Ch. 3 · Linear Equations' },
    { chapterNo: 4, label: 'Ch. 4 · Quadratic Equations' },
    { chapterNo: 5, label: 'Ch. 5 · Arithmetic Progressions' },
    { chapterNo: 6, label: 'Ch. 6 · Triangles' },
    { chapterNo: 7, label: 'Ch. 7 · Coordinate Geometry' },
    { chapterNo: 8, label: 'Ch. 8 · Trigonometry' },
  ],
  biology: [
    { chapterNo: 1, label: 'Ch. 1 · Life Processes' },
    { chapterNo: 2, label: 'Ch. 2 · Control & Coordination' },
    { chapterNo: 3, label: 'Ch. 3 · How Organisms Reproduce' },
    { chapterNo: 4, label: 'Ch. 4 · Heredity & Evolution' },
    { chapterNo: 5, label: 'Ch. 5 · Our Environment' },
    { chapterNo: 6, label: 'Ch. 6 · Management of Resources' },
  ],
};

function mod(
  id: string,
  title: string,
  subject: string,
  subjectKey: string,
  chapterNo: number,
  chapterTitle: string,
  scheduledDate: string,
  durationMin: number,
  status: ModuleStatus,
  description?: string,
): StudyModule {
  return {
    id,
    title,
    subject,
    subjectKey,
    chapterNo,
    chapterTitle,
    scheduledDate,
    durationMin,
    status,
    description:
      description ??
      `Guided notebook for ${subject} — ${chapterTitle}. Work through summaries, prompts, and practice questions at your pace.`,
    preparedAssets: {
      summary: true,
      prompts: 6,
      flashcards: 12,
      quizQuestions: 8,
    },
  };
}

/** Screenshot-aligned Institute Pace · Term 2 module schedule (32 modules, 8 complete). */
export const INSTITUTE_PACE_MODULES: StudyModule[] = [
  // Week 1 — completed
  mod('ip-m01', 'Light — Reflection', 'Physics', 'science', 1, 'Light — Reflection', '2026-05-28', 45, 'completed'),
  mod('ip-m02', 'Chemical Reactions', 'Chemistry', 'science', 1, 'Chemical Reactions', '2026-05-28', 40, 'completed'),
  mod('ip-m03', 'Real Numbers', 'Mathematics', 'mathematics', 1, 'Real Numbers', '2026-05-29', 50, 'completed'),
  mod('ip-m04', 'Life Processes Intro', 'Biology', 'science', 1, 'Life Processes', '2026-05-29', 45, 'completed'),
  mod('ip-m05', 'Trigonometric Ratios', 'Mathematics', 'mathematics', 8, 'Trigonometry', '2026-05-30', 45, 'overdue'),
  mod('ip-m06', 'Acids & Bases', 'Chemistry', 'science', 2, 'Acids, Bases & Salts', '2026-05-30', 30, 'completed'),
  mod('ip-m07', 'Polynomials', 'Mathematics', 'mathematics', 2, 'Polynomials', '2026-05-31', 50, 'completed'),
  mod('ip-m08', 'Control & Coordination', 'Biology', 'science', 2, 'Control & Coordination', '2026-05-31', 45, 'completed'),
  // Week 2 — screenshot-aligned (today = Jun 4, week grid Wed 3 – Tue 9)
  mod('ip-m09', 'Periodic Table Intro', 'Chemistry', 'science', 5, 'Periodic Classification', '2026-06-06', 30, 'upcoming'),
  mod('ip-m10', 'Kinematics Equations', 'Physics', 'science', 3, 'Motion', '2026-06-05', 40, 'skipped'),
  mod('ip-m11', 'Linear Equations', 'Mathematics', 'mathematics', 3, 'Linear Equations', '2026-05-31', 50, 'completed'),
  mod('ip-m12', 'Human Eye & Vision', 'Physics', 'science', 3, 'Human Eye', '2026-05-31', 45, 'overdue'),
  mod('ip-m13', "Newton's Laws of Motion", 'Physics', 'science', 3, 'Motion', '2026-06-04', 45, 'in_progress'),
  mod('ip-m14', 'pH Scale', 'Chemistry', 'science', 2, 'Acids, Bases & Salts', '2026-06-04', 30, 'upcoming'),
  mod('ip-m15', 'Trigonometric Identities', 'Mathematics', 'mathematics', 8, 'Trigonometry', '2026-06-05', 60, 'upcoming'),
  mod('ip-m16', 'Heredity & Evolution', 'Biology', 'science', 4, 'Heredity & Evolution', '2026-06-08', 45, 'upcoming'),
  // Week 3
  mod('ip-m17', 'Electricity', 'Physics', 'science', 4, 'Electricity', '2026-06-08', 45, 'upcoming'),
  mod('ip-m18', 'Carbon Compounds', 'Chemistry', 'science', 4, 'Carbon Compounds', '2026-06-08', 40, 'upcoming'),
  mod('ip-m19', 'Quadratic Equations', 'Mathematics', 'mathematics', 4, 'Quadratic Equations', '2026-06-09', 50, 'upcoming'),
  mod('ip-m20', 'Our Environment', 'Biology', 'science', 5, 'Our Environment', '2026-06-09', 45, 'upcoming'),
  mod('ip-m21', 'Magnetic Effects', 'Physics', 'science', 5, 'Magnetic Effects', '2026-06-10', 45, 'upcoming'),
  mod('ip-m22', 'Periodic Classification', 'Chemistry', 'science', 5, 'Periodic Classification', '2026-06-11', 40, 'upcoming'),
  mod('ip-m23', 'Arithmetic Progressions', 'Mathematics', 'mathematics', 5, 'Arithmetic Progressions', '2026-06-11', 50, 'upcoming'),
  mod('ip-m24', 'Management of Resources', 'Biology', 'science', 6, 'Management of Resources', '2026-06-12', 45, 'upcoming'),
  // Week 4
  mod('ip-m25', 'Energy Sources', 'Physics', 'science', 6, 'Energy Sources', '2026-06-15', 45, 'upcoming'),
  mod('ip-m26', 'Chemical Reactions Review', 'Chemistry', 'science', 1, 'Chemical Reactions', '2026-06-15', 40, 'upcoming'),
  mod('ip-m27', 'Triangles', 'Mathematics', 'mathematics', 6, 'Triangles', '2026-06-16', 50, 'upcoming'),
  mod('ip-m28', 'Life Processes Review', 'Biology', 'science', 1, 'Life Processes', '2026-06-16', 45, 'upcoming'),
  mod('ip-m29', 'Motion Review', 'Physics', 'science', 3, 'Motion', '2026-06-17', 45, 'upcoming'),
  mod('ip-m30', 'Acids Review', 'Chemistry', 'science', 2, 'Acids, Bases & Salts', '2026-06-17', 40, 'upcoming'),
  mod('ip-m31', 'Coordinate Geometry', 'Mathematics', 'mathematics', 7, 'Coordinate Geometry', '2026-06-18', 50, 'upcoming'),
  mod('ip-m32', 'Term 2 Mock Test', 'Mathematics', 'mathematics', 8, 'Trigonometry', '2026-06-21', 60, 'upcoming'),
];

const CUSTOM_PLAN_MODULES: StudyModule[] = [
  mod('cp-m01', 'Trigonometry — Identities', 'Mathematics', 'mathematics', 8, 'Trigonometry', '2026-06-04', 50, 'in_progress'),
  mod('cp-m02', 'Trigonometry — Applications', 'Mathematics', 'mathematics', 8, 'Trigonometry', '2026-06-05', 45, 'upcoming'),
  mod('cp-m03', 'Triangles Review', 'Mathematics', 'mathematics', 6, 'Triangles', '2026-06-06', 40, 'upcoming'),
];

export const SEED_STUDY_PLANS: StudyPlan[] = [
  {
    id: 'seed-custom-1',
    name: 'Pre-Exam Crunch',
    type: 'custom',
    currentDay: 9,
    totalDays: 14,
    progressPercent: 64,
    todayTasks: [
      {
        label: 'Trigonometry — Identities',
        subject: 'Mathematics',
        chapterNo: 8,
        subjectKey: 'mathematics',
      },
    ],
    createdAt: new Date().toISOString(),
    dateRange: { start: '2026-05-27', end: '2026-06-09' },
    subjects: ['Mathematics'],
    modules: CUSTOM_PLAN_MODULES,
    modulesComplete: 5,
    modulesTotal: 8,
    behindDays: 0,
    currentWeekIndex: 2,
    planToday: PLAN_DEMO_TODAY,
  },
  {
    id: 'seed-institute-1',
    name: 'Institute Pace · Term 2',
    type: 'institute',
    currentDay: 5,
    totalDays: 21,
    progressPercent: 25,
    todayTasks: [
      {
        label: "Newton's Laws of Motion",
        subject: 'Physics',
        chapterNo: 3,
        subjectKey: 'science',
      },
      {
        label: 'pH Scale',
        subject: 'Chemistry',
        chapterNo: 2,
        subjectKey: 'science',
      },
    ],
    createdAt: new Date().toISOString(),
    dateRange: { start: '2026-05-28', end: '2026-06-18' },
    subjects: ['Physics', 'Chemistry', 'Mathematics', 'Biology'],
    modules: INSTITUTE_PACE_MODULES,
    modulesComplete: 8,
    modulesTotal: 32,
    behindDays: 1,
    currentWeekIndex: 2,
    planToday: PLAN_DEMO_TODAY,
  },
];

export function getSubjectById(id: StudyPlanSubjectId): StudyPlanSubject {
  const subject = STUDY_PLAN_SUBJECTS.find((s) => s.id === id);
  if (!subject) throw new Error(`Unknown subject: ${id}`);
  return subject;
}

export function mergeChapterOptions(
  subjectId: StudyPlanSubjectId,
  apiChapters:
    | { chapter_no?: number | null; title?: string | null; chapter_name?: string | null; name?: string }[]
    | undefined,
): ChapterOption[] {
  const fallback = CHAPTER_FALLBACK[subjectId];
  if (!apiChapters?.length) return fallback;

  return apiChapters
    .filter((ch) => ch.chapter_no != null)
    .map((ch) => {
      const chapterNo = ch.chapter_no as number;
      const fallbackMatch = fallback.find((f) => f.chapterNo === chapterNo);
      if (fallbackMatch) return fallbackMatch;
      const title = ch.title || ch.chapter_name || ch.name || `Chapter ${chapterNo}`;
      return {
        chapterNo,
        label: `Ch. ${chapterNo} · ${title}`,
      };
    });
}
