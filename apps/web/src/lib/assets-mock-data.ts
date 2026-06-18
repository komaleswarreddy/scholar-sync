/**
 * Mock data for ScholarSync Assets page (UI-first).
 */

export type AssetType = 'Quiz' | 'Flashcards' | 'Mind Map' | 'Summary' | 'Audio';
export type AssetSubject = 'Physics' | 'Chemistry' | 'Maths' | 'Biology';
export type AssetClass = 'Class 11' | 'Class 12';

export type StudyAsset = {
  id: string;
  type: AssetType;
  studioType?: string;
  title: string;
  notebook: string;
  subject: AssetSubject | string;
  classLevel: AssetClass | string;
  meta: string;
  timestamp: string;
  content?: unknown;
};

export type StudyNote = {
  id: string;
  title: string;
  notebook: string;
  subject: AssetSubject | string;
  classLevel: AssetClass | string;
  snippet: string;
  timestamp: string;
};

export const ASSET_TYPE_FILTERS = [
  'All',
  'Quiz',
  'Flashcards',
  'Mind Map',
  'Summary',
] as const;

export const ASSET_SUBJECT_FILTERS = [
  'All Subjects',
  'Physics',
  'Chemistry',
  'Maths',
  'Biology',
] as const;

export const ASSET_CLASS_FILTERS = ['All Classes', 'Class 11', 'Class 12'] as const;

export const NOTE_SORT_OPTIONS = ['Most recent', 'Oldest first', 'Title A–Z'] as const;

export const STUDY_ASSETS: StudyAsset[] = [
  {
    id: 'quiz-rotational-l2',
    type: 'Quiz',
    title: 'Rotational Mechanics — Level 2',
    notebook: 'Rotational Motion',
    subject: 'Physics',
    classLevel: 'Class 11',
    meta: '15 questions',
    timestamp: '2 hours ago',
  },
  {
    id: 'flash-torque',
    type: 'Flashcards',
    title: 'Torque & Moment of Inertia',
    notebook: 'Rotational Motion',
    subject: 'Physics',
    classLevel: 'Class 11',
    meta: '24 cards',
    timestamp: 'Yesterday',
  },
  {
    id: 'mind-kinematics',
    type: 'Mind Map',
    title: 'Kinematics Concept Web',
    notebook: 'Rotational Motion',
    subject: 'Physics',
    classLevel: 'Class 11',
    meta: 'Interactive',
    timestamp: 'Yesterday',
  },
  {
    id: 'audio-bonding',
    type: 'Audio',
    title: 'Chemical Bonding Overview',
    notebook: 'Chemical Bonding',
    subject: 'Chemistry',
    classLevel: 'Class 11',
    meta: '5 min summary',
    timestamp: '2 days ago',
  },
  {
    id: 'summary-limits',
    type: 'Summary',
    title: 'Limits — One-page recap',
    notebook: 'Calculus: Limits',
    subject: 'Maths',
    classLevel: 'Class 12',
    meta: '1 page',
    timestamp: '3 days ago',
  },
  {
    id: 'quiz-hydrocarbons',
    type: 'Quiz',
    title: 'Hydrocarbons Reaction Drill',
    notebook: 'Hydrocarbons',
    subject: 'Chemistry',
    classLevel: 'Class 11',
    meta: '12 questions',
    timestamp: '5 days ago',
  },
];

export const STUDY_NOTES: StudyNote[] = [
  {
    id: 'note-torque',
    title: 'Torque derivation',
    notebook: 'Rotational Motion',
    subject: 'Physics',
    classLevel: 'Class 11',
    snippet: 'τ = r × F sin θ — only perpendicular component contributes...',
    timestamp: 'Today',
  },
  {
    id: 'note-inertia',
    title: 'Moment of Inertia table',
    notebook: 'Rotational Motion',
    subject: 'Physics',
    classLevel: 'Class 11',
    snippet: 'Solid sphere: (2/5)MR². Hollow sphere: (2/3)MR². Disc: (1/2)MR²...',
    timestamp: 'Yesterday',
  },
  {
    id: 'note-vsepr',
    title: 'VSEPR geometry shortcuts',
    notebook: 'Chemical Bonding',
    subject: 'Chemistry',
    classLevel: 'Class 11',
    snippet: 'Steric number = bond pairs + lone pairs. SN=4 → tetrahedral...',
    timestamp: '2 days ago',
  },
  {
    id: 'note-chain',
    title: 'Chain rule cheat-sheet',
    notebook: 'Calculus: Limits',
    subject: 'Maths',
    classLevel: 'Class 12',
    snippet: "If y = f(g(x)), then dy/dx = f'(g(x)) · g'(x). Practice with sin(x²)...",
    timestamp: '3 days ago',
  },
];

export const ASSET_TYPE_THEME: Record<
  AssetType,
  { iconBg: string; iconColor: string }
> = {
  Quiz: { iconBg: '#E8F2EE', iconColor: '#0F7A52' },
  Flashcards: { iconBg: '#E8F2EE', iconColor: '#0F7A52' },
  'Mind Map': { iconBg: '#FFF4EC', iconColor: '#EA580C' },
  Audio: { iconBg: '#E8F0FE', iconColor: '#1A73E8' },
  Summary: { iconBg: '#FCE7F3', iconColor: '#DB2777' },
};
