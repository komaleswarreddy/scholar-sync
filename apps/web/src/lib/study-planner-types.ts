export type PlanType = 'custom' | 'institute';

export type ModuleStatus =
  | 'completed'
  | 'in_progress'
  | 'overdue'
  | 'skipped'
  | 'upcoming';

export type StudyPlanTask = {
  label: string;
  subject: string;
  chapterNo?: number;
  subjectKey?: string;
};

export type PreparedAssets = {
  summary: boolean;
  prompts: number;
  flashcards: number;
  quizQuestions: number;
};

export type StudyModule = {
  id: string;
  title: string;
  subject: string;
  subjectKey: string;
  chapterNo: number;
  chapterTitle: string;
  scheduledDate: string;
  durationMin: number;
  status: ModuleStatus;
  description?: string;
  preparedAssets?: PreparedAssets;
};

export type StudyPlan = {
  id: string;
  name: string;
  type: PlanType;
  currentDay: number;
  totalDays: number;
  progressPercent: number;
  todayTasks: StudyPlanTask[];
  createdAt: string;
  dateRange?: { start: string; end: string };
  subjects?: string[];
  modules?: StudyModule[];
  modulesComplete?: number;
  modulesTotal?: number;
  behindDays?: number;
  currentWeekIndex?: number;
  /** ISO date used as "today" for demo consistency */
  planToday?: string;
};

export type StudyPlanSubjectId = 'physics' | 'chemistry' | 'mathematics' | 'biology';

export type StudyPlanSubject = {
  id: StudyPlanSubjectId;
  label: string;
  apiKey: string;
};

export type ChapterOption = {
  chapterNo: number;
  label: string;
};

export type TimelineMode = 'end_date' | 'duration';
export type DurationUnit = 'Days' | 'Weeks' | 'Months';
export type StudyTimeMode = 'per_day' | 'per_week';

export type CustomPlanFormState = {
  selectedSubjects: StudyPlanSubjectId[];
  selectedChapters: Record<StudyPlanSubjectId, number[]>;
  timelineMode: TimelineMode;
  endDate: string;
  durationValue: number;
  durationUnit: DurationUnit;
  studyTimeMode: StudyTimeMode;
  hoursPerDay: number;
  daysPerWeek: number;
};

export type InstituteScheduleRow = {
  subject: string;
  topic: string;
  chapterLabel: string;
  subjectKey: string;
  chapterNo: number;
};

export type PlanViewMode = 'week' | 'list';
