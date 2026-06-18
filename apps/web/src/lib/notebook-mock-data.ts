/**
 * Mock data for notebook workspace (Rotational Motion UI-first).
 */

export const NOTEBOOK_ROTATIONAL = {
  slug: 'rotational-motion',
  breadcrumbs: [
    { label: 'Library', href: '/library' },
    { label: 'Physics', href: '/library' },
    { label: 'Class 11', href: '/library' },
  ],
  title: 'Rotational Motion',
  subtitle: 'NCERT Ch. 7 — System of Particles',
  focusLabel: 'FOCUS: TORQUE ON A RIGID BODY',
  masteryPercent: 72,
} as const;

export type NotebookSource = {
  id: string;
  title: string;
  subtitle: string;
  meta: string;
  iconTone: 'green' | 'purple' | 'orange' | 'blue';
};

export const NOTEBOOK_SOURCES: NotebookSource[] = [
  {
    id: 'ncert-ch7',
    title: 'NCERT Physics Ch 7',
    subtitle: 'System of Particles & Rotational Motion',
    meta: 'PDF • 18 pages',
    iconTone: 'green',
  },
  {
    id: 'class-notes-oct12',
    title: 'Class Notes — Oct 12',
    subtitle: 'Torque & angular momentum',
    meta: 'Notes • 6 pages',
    iconTone: 'purple',
  },
  {
    id: 'week14-test',
    title: 'Week 14 Test',
    subtitle: 'Practice paper',
    meta: 'PDF • 4 pages',
    iconTone: 'orange',
  },
  {
    id: 'hc-verma',
    title: 'HC Verma Vol I',
    subtitle: 'Ch 10 — Rotational mechanics',
    meta: 'Book • Selected sections',
    iconTone: 'blue',
  },
];

export type NotebookNotePreview = {
  id: string;
  title: string;
  timestamp: string;
};

export type NotebookNoteFull = NotebookNotePreview & {
  notebook: string;
  subject: string;
  classLevel: string;
  snippet: string;
  body: string;
};

export const NOTEBOOK_NOTES_SIDEBAR: NotebookNotePreview[] = [
  { id: 'torque-derivation', title: 'Torque derivation', timestamp: '2 days ago' },
  { id: 'inertia-table', title: 'Moment of Inertia table', timestamp: '3 days ago' },
  { id: 'door-analogy', title: 'Door-handle analogy', timestamp: '4 days ago' },
];

export const NOTEBOOK_NOTES_FULL: NotebookNoteFull[] = [
  {
    id: 'torque-derivation',
    title: 'Torque derivation',
    timestamp: 'Today',
    notebook: 'Rotational Motion',
    subject: 'Physics',
    classLevel: 'Class 11',
    snippet: 'τ = r × F sin θ — only perpendicular component contributes...',
    body: `τ = r × F sin θ

Only the force component perpendicular to the position vector contributes to torque.

For a door: τ = r × F. Pushing at the hinge gives r ≈ 0 → small torque. Pushing at the handle maximizes r.

Key takeaway: τ = Iα connects net torque to angular acceleration.`,
  },
  {
    id: 'inertia-table',
    title: 'Moment of Inertia table',
    timestamp: 'Yesterday',
    notebook: 'Rotational Motion',
    subject: 'Physics',
    classLevel: 'Class 11',
    snippet: 'Solid sphere: (2/5)MR². Hollow sphere: (2/3)MR². Disc: (1/2)MR²...',
    body: `Common moments of inertia (about central axis):

• Solid sphere: I = (2/5)MR²
• Hollow sphere: I = (2/3)MR²
• Disc: I = (1/2)MR²
• Rod (center): I = (1/12)ML²
• Rod (end): I = (1/3)ML²

Use parallel axis theorem: I = I_cm + Md²`,
  },
  {
    id: 'door-analogy',
    title: 'Door-handle analogy',
    timestamp: '2 days ago',
    notebook: 'Rotational Motion',
    subject: 'Physics',
    classLevel: 'Class 11',
    snippet: 'Why handles are far from hinges — maximize r for same F...',
    body: `Door-handle analogy for torque:

Same force F produces larger torque when applied farther from the pivot (larger r).

W = τθ — work done by torque through an angular displacement.

Real-world: wrenches, steering wheels, see-saws.`,
  },
];

export const NOTEBOOK_CHAT = {
  status: 'Analysing weakness: Torque on a rigid body',
  messages: [
    {
      id: 'ai-1',
      role: 'assistant' as const,
      content:
        'Torque is the rotational analogue of force. For a rigid body, τ = r × F. Only the perpendicular component of force matters.',
      actions: ['Explain torque with the door analogy', 'Show a quick practice question'],
    },
    {
      id: 'user-1',
      role: 'user' as const,
      content: 'Why is torque zero when force passes through the axis?',
      time: '10:32 AM',
    },
    {
      id: 'ai-2',
      role: 'assistant' as const,
      content:
        'When the line of action passes through the pivot, r is parallel to F, so sin θ = 0 and τ = 0.',
      actions: [],
    },
  ],
  suggestions: [
    'Practice level-2 torque problems',
    'Visualise this as a mind map',
    'Compare torque vs moment of force',
    'Revise angular momentum',
  ],
};

export const NOTEBOOK_STUDIO = [
  { type: 'Quiz', desc: '15 questions', tone: 'green' },
  { type: 'Flashcards', desc: '24 cards', tone: 'green' },
  { type: 'Mind Map', desc: 'Interactive', tone: 'orange' },
  { type: 'Slide Deck', desc: 'Presentation', tone: 'blue' },
] as const;

export const NOTEBOOK_RECENT_ASSETS = [
  {
    id: 'ra-1',
    title: 'Kinematics summary mind map',
    meta: 'Mind Map • Physics • Class 11',
    tone: 'orange' as const,
  },
  {
    id: 'ra-2',
    title: 'Torque flashcards',
    meta: 'Flashcards • 24 cards',
    tone: 'green' as const,
  },
];

export const NOTEBOOK_HEATMAP: (
  | 'strong'
  | 'good'
  | 'average'
  | 'weak'
  | 'empty'
)[] = [
  'strong', 'strong', 'good', 'good', 'average', 'weak', 'empty', 'empty',
  'strong', 'good', 'good', 'average', 'average', 'weak', 'empty', 'empty',
  'good', 'good', 'average', 'average', 'weak', 'empty', 'empty', 'empty',
  'good', 'average', 'average', 'weak', 'weak', 'empty', 'empty', 'empty',
  'average', 'average', 'weak', 'weak', 'empty', 'empty', 'empty', 'empty',
];
