/**
 * Mock data for ScholarSync Library page (UI-first until APIs exist).
 */

export type LibrarySubject = 'Physics' | 'Chemistry' | 'Maths' | 'Biology';
export type LibraryClass = 'Class 11' | 'Class 12';

export type LibraryNotebook = {
  id: string;
  slug?: string;
  notebookId?: string;
  mode?: string;
  subject: LibrarySubject | string;
  classLevel: LibraryClass | string;
  lastStudiedAt?: string | null;
  title: string;
  subtitle: string;
  focus: string;
  masteryPercent: number;
  sources: number;
  studyAssets: number;
  quizzes: number;
  lastStudied: string;
};

export const LIBRARY_STATS = {
  totalNotebooks: 6,
  activeThisWeek: 4,
} as const;

export const LIBRARY_SUBJECT_FILTERS = ['All', 'Physics', 'Chemistry', 'Maths', 'Biology'] as const;
export const LIBRARY_CLASS_FILTERS = ['All', 'Class 11', 'Class 12'] as const;
export const LIBRARY_SORT_OPTIONS = ['Recently used', 'Name A–Z', 'Mastery %', 'Last studied'] as const;

export const LIBRARY_NOTEBOOKS: LibraryNotebook[] = [
  {
    id: 'rotational-motion',
    subject: 'Physics',
    classLevel: 'Class 11',
    title: 'Rotational Motion',
    subtitle: 'NCERT Ch. 7 — System of Particles',
    focus: 'Torque on a rigid body',
    masteryPercent: 72,
    sources: 4,
    studyAssets: 6,
    quizzes: 2,
    lastStudied: '2 hours ago',
  },
  {
    id: 'chemical-bonding',
    subject: 'Chemistry',
    classLevel: 'Class 11',
    title: 'Chemical Bonding & Molecular Structure',
    subtitle: 'NCERT Ch. 4 — Chemical Bonding',
    focus: 'VSEPR theory & hybridization',
    masteryPercent: 81,
    sources: 3,
    studyAssets: 4,
    quizzes: 1,
    lastStudied: 'Yesterday',
  },
  {
    id: 'limits-derivatives',
    subject: 'Maths',
    classLevel: 'Class 11',
    title: 'Limits, Continuity & Derivatives',
    subtitle: 'NCERT Ch. 5 — Continuity and Differentiability',
    focus: 'Chain rule & implicit differentiation',
    masteryPercent: 64,
    sources: 5,
    studyAssets: 9,
    quizzes: 3,
    lastStudied: '3 days ago',
  },
  {
    id: 'hydrocarbons',
    subject: 'Chemistry',
    classLevel: 'Class 11',
    title: 'Hydrocarbons — Reactions',
    subtitle: 'NCERT Ch. 13 — Hydrocarbons',
    focus: 'Electrophilic substitution in benzene',
    masteryPercent: 58,
    sources: 2,
    studyAssets: 3,
    quizzes: 1,
    lastStudied: '5 days ago',
  },
  {
    id: 'current-electricity',
    subject: 'Physics',
    classLevel: 'Class 11',
    title: 'Current Electricity',
    subtitle: 'NCERT Ch. 3 — Current Electricity',
    focus: "Kirchhoff's laws & Wheatstone bridge",
    masteryPercent: 88,
    sources: 4,
    studyAssets: 5,
    quizzes: 2,
    lastStudied: 'Last week',
  },
  {
    id: 'trigonometric-functions',
    subject: 'Maths',
    classLevel: 'Class 11',
    title: 'Trigonometric Functions',
    subtitle: 'NCERT Ch. 3 — Trigonometric Functions',
    focus: 'Identities & inverse trig functions',
    masteryPercent: 76,
    sources: 3,
    studyAssets: 7,
    quizzes: 2,
    lastStudied: 'Last week',
  },
];

export const SUBJECT_THEME: Record<
  LibrarySubject,
  { label: string; ring: string; muted: string }
> = {
  Physics: { label: '#0F7A52', ring: '#0D3D2E', muted: '#E8F2EE' },
  Chemistry: { label: '#EA580C', ring: '#EA580C', muted: '#FFF4EC' },
  Maths: { label: '#0D9488', ring: '#0D9488', muted: '#ECFDF5' },
  Biology: { label: '#16A34A', ring: '#16A34A', muted: '#F0FDF4' },
};

export const DEFAULT_SUBJECT_THEME = {
  label: '#6B7280',
  ring: '#9CA3AF',
  muted: '#F3F4F3',
};

export function getSubjectTheme(subject: string) {
  if (subject in SUBJECT_THEME) {
    return SUBJECT_THEME[subject as LibrarySubject];
  }
  return DEFAULT_SUBJECT_THEME;
}
