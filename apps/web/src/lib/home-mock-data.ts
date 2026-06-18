/**

 * Mock data for ScholarSync home dashboard (UI-first until APIs exist).

 */



export const HOME_CLASS_CONTEXT = 'Class 12';



export const HOME_FOCUS_CONCEPT = {

  slug: 'rotational-motion-torque',

  subject: 'Physics',

  topic: 'Rotational Motion • Torque',

  severity: 'critical' as const,

  decayPercent: 62,

  message: 'Concept decay high (62%). Revise before your test on Sat.',

  nextTest: 'Physics • 18 May',

  progress: {

    conceptDecay: 62,

    syllabusProgress: 48,

    weeklyGoal: 72,

  },

};



export const HOME_PERFORMANCE_LINE =

  "Your last Physics test scored 17/25. We've analyzed your performance and mapped a focused plan to help you improve.";



export const HOME_OVERVIEW_METRICS = [

  {

    id: 'syllabus',

    type: 'ring' as const,

    label: 'Syllabus completion',

    value: 48,

    subtitle: 'Physics - Chemistry - Maths',

    footer: '48% of total syllabus completed',

    footerTone: 'green' as const,

  },

  {

    id: 'tests',

    type: 'stat' as const,

    label: 'Tests analyzed',

    value: '28',

    detail: 'Across all subjects',

    icon: 'document' as const,

    footerTone: 'muted' as const,

  },

  {

    id: 'strong',

    type: 'stat' as const,

    label: 'Strong concepts',

    value: '23',

    detail: 'Keep building!',

    icon: 'shield' as const,

    footerTone: 'green' as const,

  },

  {

    id: 'attention',

    type: 'stat' as const,

    label: 'Need attention',

    value: '7',

    detail: 'Focus and improve',

    icon: 'warning' as const,

    footerTone: 'orange' as const,

  },

];



export const HOME_CONTINUE_SUBJECTS = [

  {

    id: 'physics-rotational',

    subject: 'Physics',

    topic: 'Rotational Motion',

    progress: 40,

    topicsCompleted: 2,

    topicsTotal: 5,

    lastStudied: '2 hours ago',

    icon: 'physics' as const,

  },

  {

    id: 'chem-bonding',

    subject: 'Chemistry',

    topic: 'Chemical Bonding…',

    progress: 25,

    topicsCompleted: 1,

    topicsTotal: 4,

    lastStudied: '4 days ago',

    icon: 'chemistry' as const,

  },

  {

    id: 'math-limits',

    subject: 'Mathematics',

    topic: 'Limits & Derivatives',

    progress: 60,

    topicsCompleted: 3,

    topicsTotal: 5,

    lastStudied: '1 day ago',

    icon: 'math' as const,

  },

  {

    id: 'bio-physiology',

    subject: 'Biology',

    topic: 'Human Physiology',

    progress: 20,

    topicsCompleted: 1,

    topicsTotal: 5,

    lastStudied: '5 days ago',

    icon: 'biology' as const,

  },

];



export const FOCUS_SESSION_URL = `/dashboard?focusConcept=${HOME_FOCUS_CONCEPT.slug}`;


