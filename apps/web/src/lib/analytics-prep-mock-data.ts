/**
 * Mock data for student prep analytics dashboard (Syllabus.ai mocks).
 */

export const ANALYTICS_FILTERS = {
  subjects: ['All Subjects', 'Physics', 'Chemistry', 'Maths', 'Biology'],
  periods: ['Last 7 days', 'Last 30 days', 'Last 90 days'],
} as const;

export const ANALYTICS_KPIS = [
  {
    id: 'mastery',
    label: 'Average Mastery',
    value: '68%',
    delta: '+4% vs last 7 days',
    deltaPositive: true,
    sparkline: [52, 58, 61, 63, 66, 68],
  },
  {
    id: 'syllabus',
    label: 'Syllabus Covered',
    value: '49%',
    sub: '22 / 45 chapters',
    progress: 49,
  },
  {
    id: 'weak',
    label: 'Weak Concepts',
    value: '5',
    sub: 'below 60% mastery',
    tone: 'warning' as const,
  },
  {
    id: 'decay',
    label: 'Decay Risk',
    value: '5',
    sub: 'chapters 14d+ stale',
    tone: 'warning' as const,
  },
];

export const SCORE_TREND = {
  dates: ['Sep 2', 'Sep 9', 'Sep 16', 'Sep 23', 'Sep 30', 'Oct 7', 'Oct 14', 'Oct 21'],
  summaries: [
    { id: 'physics' as const, label: 'PHYSICS', avg: 77, tests: 4, color: '#2D4A3E' },
    { id: 'chemistry' as const, label: 'CHEMISTRY', avg: 75, tests: 3, color: '#E68A00' },
    { id: 'maths' as const, label: 'MATHEMATICS', avg: 66, tests: 4, color: '#28A745' },
  ],
  physics: [68, 72, 75, 78, 88, 82, 78, 72],
  chemistry: [null, 64, 68, 72, 76, 78, 84, 82] as (number | null)[],
  maths: [null, 76, 74, 70, 68, 56, 60, 64] as (number | null)[],
};

export type RecommendedSession = {
  id: string;
  topic: string;
  subject: string;
  staleDays: number;
  testInDays: number;
  score: number;
  focusHref: string;
};

export const RECOMMENDED_SESSIONS: RecommendedSession[] = [
  {
    id: 'thermo',
    topic: 'Thermodynamics',
    subject: 'Physics',
    staleDays: 24,
    testInDays: 18,
    score: 58,
    focusHref: '/notebook/rotational-motion?focusTopic=thermodynamics',
  },
  {
    id: 'equilibrium',
    topic: 'Equilibrium',
    subject: 'Chemistry',
    staleDays: 21,
    testInDays: 12,
    score: 49,
    focusHref: '/notebook/rotational-motion?focusTopic=chemical-equilibrium',
  },
  {
    id: 'rotation',
    topic: 'Rotational Motion',
    subject: 'Physics',
    staleDays: 10,
    testInDays: 10,
    score: 41,
    focusHref: '/notebook/rotational-motion?focusTopic=rotational-motion',
  },
  {
    id: 'limits',
    topic: 'Limits & Derivatives',
    subject: 'Mathematics',
    staleDays: 16,
    testInDays: 9,
    score: 38,
    focusHref: '/notebook/rotational-motion?focusTopic=limits-derivatives',
  },
  {
    id: 'hydrocarbons',
    topic: 'Hydrocarbons',
    subject: 'Chemistry',
    staleDays: 14,
    testInDays: 7,
    score: 60,
    focusHref: '/notebook/rotational-motion?focusTopic=hydrocarbons',
  },
];

export type TopicBarItem = {
  name: string;
  meta: string;
  pct: number;
};

export const STRONG_TOPICS: TopicBarItem[] = [
  { name: 'Sets & Functions', meta: 'Mathematics · Ch. 1–2', pct: 95 },
  { name: 'Kinematics 1D', meta: 'Physics · Ch. 3', pct: 92 },
  { name: 'Atomic Structure', meta: 'Chemistry · Ch. 2', pct: 88 },
  { name: "Newton's Laws", meta: 'Physics · Ch. 4', pct: 84 },
  { name: 'Chemical Bonding', meta: 'Chemistry · Ch. 4', pct: 81 },
];

export const WEAK_TOPICS: TopicBarItem[] = [
  { name: 'Limits & Derivatives', meta: 'Mathematics · Ch. 13', pct: 38 },
  { name: 'Rotational Motion', meta: 'Physics · Ch. 7', pct: 41 },
  { name: 'Equilibrium', meta: 'Chemistry · Ch. 7', pct: 49 },
  { name: 'Thermodynamics', meta: 'Chemistry · Ch. 6', pct: 52 },
  { name: 'Thermodynamics', meta: 'Physics · Ch. 12', pct: 58 },
];

export type ConceptTier = 'mastered' | 'in_progress' | 'weak' | 'untouched';

export type SyllabusConcept = {
  name: string;
  pct: number | null;
  tier: ConceptTier;
};

export const SYLLABUS_SUBJECTS = [
  {
    subject: 'PHYSICS',
    summary: '7 mastered · 4 in progress · 2 weak · 2 untouched',
    segments: { mastered: 47, inProgress: 27, weak: 8, untouched: 18 },
    moreCount: 8,
    concepts: [
      { name: 'Kinematics 1D', pct: 92, tier: 'mastered' as const },
      { name: "Newton's Laws", pct: 88, tier: 'mastered' as const },
      { name: 'Work, Energy, Power', pct: 78, tier: 'in_progress' as const },
      { name: 'Rotational Motion', pct: 41, tier: 'weak' as const },
      { name: 'Gravitation', pct: 65, tier: 'in_progress' as const },
      { name: 'Thermodynamics', pct: 58, tier: 'weak' as const },
      { name: 'Oscillations', pct: null, tier: 'untouched' as const },
    ],
  },
  {
    subject: 'CHEMISTRY',
    summary: '5 mastered · 2 in progress · 1 weak · 3 untouched',
    segments: { mastered: 42, inProgress: 17, weak: 8, untouched: 33 },
    moreCount: 4,
    concepts: [
      { name: 'Atomic Structure', pct: 92, tier: 'mastered' as const },
      { name: 'Chemical Bonding', pct: 88, tier: 'mastered' as const },
      { name: 'Thermodynamics (Chem)', pct: 65, tier: 'in_progress' as const },
      { name: 'Equilibrium', pct: 49, tier: 'weak' as const },
      { name: 'Hydrocarbons', pct: 43, tier: 'in_progress' as const },
      { name: 'Solutions', pct: null, tier: 'untouched' as const },
    ],
  },
  {
    subject: 'MATHEMATICS',
    summary: '4 mastered · 3 in progress · 1 weak · 2 untouched',
    segments: { mastered: 40, inProgress: 30, weak: 7, untouched: 23 },
    moreCount: 11,
    concepts: [
      { name: 'Sets & Functions', pct: 95, tier: 'mastered' as const },
      { name: 'Trigonometry', pct: 88, tier: 'mastered' as const },
      { name: 'Sequences & Series', pct: 72, tier: 'in_progress' as const },
      { name: 'Limits & Derivatives', pct: 38, tier: 'weak' as const },
      { name: 'Probability', pct: 55, tier: 'in_progress' as const },
      { name: 'Binomial Theorem', pct: null, tier: 'untouched' as const },
    ],
  },
];

export type ActionGapItem = {
  id: string;
  topic: string;
  subject: string;
  queries: number;
  score: number;
  focusHref: string;
};

export const ACTION_REQUIRED_GAPS: ActionGapItem[] = [
  {
    id: 'ar1',
    topic: 'Limits & Derivatives',
    subject: 'Mathematics',
    queries: 32,
    score: 38,
    focusHref: '/notebook/rotational-motion?focusTopic=limits-derivatives',
  },
  {
    id: 'ar2',
    topic: 'Rotational Motion',
    subject: 'Physics',
    queries: 47,
    score: 41,
    focusHref: '/notebook/rotational-motion?focusTopic=rotational-motion',
  },
  {
    id: 'ar3',
    topic: 'Equilibrium',
    subject: 'Chemistry',
    queries: 38,
    score: 45,
    focusHref: '/notebook/rotational-motion?focusTopic=chemical-equilibrium',
  },
  {
    id: 'ar4',
    topic: 'Thermodynamics',
    subject: 'Physics',
    queries: 31,
    score: 58,
    focusHref: '/notebook/rotational-motion?focusTopic=thermodynamics',
  },
];

export type ScatterPoint = {
  id: string;
  topic: string;
  /** 0–100, left = fewer queries */
  x: number;
  /** 0–100, top = higher quiz score */
  y: number;
  tone: 'orange' | 'green';
  focusHref?: string;
};

/** Pre-spaced layout — upper-left #1F5B50 cluster, lower-right #D97706 cluster */
export const GAP_SCATTER_POINTS: ScatterPoint[] = [
  { id: 's1', topic: 'Limits', x: 16, y: 14, tone: 'green', focusHref: '/notebook/rotational-motion?focusTopic=limits-derivatives' },
  { id: 's2', topic: 'Rotation', x: 24, y: 22, tone: 'green', focusHref: '/notebook/rotational-motion?focusTopic=rotational-motion' },
  { id: 's3', topic: 'Equilibrium', x: 20, y: 32, tone: 'green', focusHref: '/notebook/rotational-motion?focusTopic=chemical-equilibrium' },
  { id: 's4', topic: 'Thermo', x: 30, y: 18, tone: 'green', focusHref: '/notebook/rotational-motion?focusTopic=thermodynamics' },
  { id: 's5', topic: 'Waves', x: 26, y: 28, tone: 'green' },
  { id: 's6', topic: 'Optics', x: 34, y: 24, tone: 'green' },
  { id: 's7', topic: 'Sets', x: 74, y: 74, tone: 'orange' },
  { id: 's8', topic: 'Bonding', x: 80, y: 80, tone: 'orange' },
  { id: 's9', topic: 'Trig', x: 68, y: 78, tone: 'orange' },
];

export type DecayCardItem = {
  id: string;
  topic: string;
  mastery: number;
  days: number;
  status: 'at-risk' | 'fading' | 'fresh';
  focusHref: string;
};

export const DECAY_BY_SUBJECT: Record<string, DecayCardItem[]> = {
  PHYSICS: [
    { id: 'dp1', topic: 'Thermodynamics', mastery: 58, days: 24, status: 'at-risk', focusHref: '/notebook/rotational-motion?focusTopic=thermodynamics' },
    { id: 'dp2', topic: 'Rotational Motion', mastery: 41, days: 21, status: 'at-risk', focusHref: '/notebook/rotational-motion?focusTopic=rotational-motion' },
    { id: 'dp3', topic: "Newton's Laws", mastery: 72, days: 9, status: 'fading', focusHref: '/notebook/rotational-motion?focusTopic=newtons-laws' },
    { id: 'dp4', topic: 'Kinematics 1D', mastery: 92, days: 2, status: 'fresh', focusHref: '/notebook/rotational-motion?focusTopic=kinematics' },
  ],
  CHEMISTRY: [
    { id: 'dc1', topic: 'Equilibrium', mastery: 49, days: 22, status: 'at-risk', focusHref: '/notebook/rotational-motion?focusTopic=chemical-equilibrium' },
    { id: 'dc2', topic: 'Hydrocarbons', mastery: 43, days: 18, status: 'at-risk', focusHref: '/notebook/rotational-motion?focusTopic=hydrocarbons' },
    { id: 'dc3', topic: 'Chemical Bonding', mastery: 88, days: 2, status: 'fresh', focusHref: '/notebook/rotational-motion?focusTopic=chemical-bonding' },
  ],
  MATHEMATICS: [
    { id: 'dm1', topic: 'Limits & Derivatives', mastery: 38, days: 26, status: 'at-risk', focusHref: '/notebook/rotational-motion?focusTopic=limits-derivatives' },
    { id: 'dm2', topic: 'Probability', mastery: 49, days: 11, status: 'fading', focusHref: '/notebook/rotational-motion?focusTopic=probability' },
    { id: 'dm3', topic: 'Trigonometry', mastery: 78, days: 2, status: 'fresh', focusHref: '/notebook/rotational-motion?focusTopic=trigonometry' },
  ],
};

export const CITATION_LOYALTY = {
  overall: 61,
  headline: 'You verify 61% of cited answers against the textbook',
  subtext: 'Healthy verification habit. Keep cross-checking AI answers against NCERT.',
  bySubject: [
    { label: 'PHYS', pct: 65, tone: 'neutral' as const },
    { label: 'CHEM', pct: 43, tone: 'warning' as const },
    { label: 'MATH', pct: 69, tone: 'good' as const },
  ],
};

export const RAG_INTERACTION = {
  queriesThisWeek: 132,
  questionsByDay: [
    { day: 'Mon', count: 16 },
    { day: 'Tue', count: 20 },
    { day: 'Wed', count: 10 },
    { day: 'Thu', count: 22 },
    { day: 'Fri', count: 30 },
    { day: 'Sat', count: 24 },
    { day: 'Sun', count: 10 },
  ],
  topChapters: [
    { name: 'Limits & Derivatives', count: 52 },
    { name: 'Rotational Motion', count: 47 },
    { name: 'Equilibrium', count: 38 },
    { name: 'Thermodynamics', count: 33 },
  ],
} as const;

export type StudioToolUsage = {
  name: string;
  uses: number;
  segments: { physics: number; chemistry: number; maths: number };
};

export const STUDIO_ENGAGEMENT = {
  maxUses: 47,
  subjectColors: {
    physics: '#1E4D40',
    chemistry: '#F59E0B',
    maths: '#10B981',
  },
  tools: [
    { name: 'Quiz', uses: 34, segments: { physics: 14, chemistry: 12, maths: 8 } },
    { name: 'Flashcards', uses: 47, segments: { physics: 18, chemistry: 16, maths: 13 } },
    { name: 'Mind Map', uses: 13, segments: { physics: 5, chemistry: 4, maths: 4 } },
    { name: 'Audio', uses: 9, segments: { physics: 3, chemistry: 3, maths: 3 } },
    { name: 'Summary', uses: 17, segments: { physics: 7, chemistry: 5, maths: 5 } },
  ] satisfies StudioToolUsage[],
  legend: [
    { label: 'Physics', key: 'physics' as const },
    { label: 'Chemistry', key: 'chemistry' as const },
    { label: 'Math', key: 'maths' as const },
  ],
} as const;

export const VERIFICATION_DISCLAIMER = {
  title: 'Why source verification matters',
  body: `When you verify AI answers against your textbook or class notes, you build stronger recall and catch mistakes early.

Students who verify at least 60% of cited answers show higher mastery scores within 2 weeks — especially in Physics and Chemistry where small errors compound quickly.

Tip: After each tutor reply, open the cited source and confirm one key line before moving on.`,
};
