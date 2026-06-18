/**
 * Mock data for ScholarSync student profile (UI-first).
 */

export const PROFILE_COMPLETION_PERCENT = 82;

export const PROFILE_DISPLAY = {
  fullName: 'Rahul Kumar',
  initials: 'RK',
  classBoard: 'Class 11 • CBSE',
  track: 'JEE Main + Advanced Track',
} as const;

export const PROFILE_STUDENT_INFO = {
  fullName: 'Rahul Kumar',
  dateOfBirth: '12 Feb 2008',
  gender: 'Male',
  email: 'rahul.kumar@email.com',
  phone: '98765 43210',
  parentContact: '+91 91234 56789',
  city: 'Hyderabad',
  state: 'Telangana',
} as const;

export const PROFILE_ACADEMIC = {
  classLevel: 'Class 11',
  board: 'CBSE',
  stream: 'Science (PCM)',
  subjects: ['Physics', 'Chemistry', 'Mathematics', 'English'],
  academicYear: '2025–26',
} as const;

/** Exam Goals — field labels and values fixed per mock (do not rename) */
export const PROFILE_EXAM_GOALS = [
  {
    number: 1,
    label: 'Primary goal',
    value: 'JEE Main + Advanced',
    icon: 'target' as const,
  },
  {
    number: 2,
    label: 'Secondary goal',
    value: 'Boards',
    icon: 'star' as const,
  },
  {
    number: 3,
    label: 'Target exam year',
    value: '2027',
    icon: 'calendar' as const,
  },
  {
    number: 4,
    label: 'Target percentile / rank',
    value: '98 percentile / Under 10,000 rank',
    icon: 'medal' as const,
  },
  {
    number: 5,
    label: 'Target board percentage',
    value: '90%+',
    icon: 'pie' as const,
  },
  {
    number: 6,
    label: 'Priority subjects',
    value: 'Physics, Maths, Chemistry',
    tags: ['Physics', 'Maths', 'Chemistry'] as const,
    icon: 'book' as const,
  },
  {
    number: 7,
    label: 'Weekly study target',
    value: '12 hours / week',
    icon: 'clock' as const,
  },
  {
    number: 8,
    label: 'Current focus',
    value: 'Improve weak concepts before weekly test',
    icon: 'brain' as const,
  },
  {
    number: 9,
    label: 'Preferred attempt plan or test milestone',
    value: 'Weekly mock every Sunday',
    icon: 'calendarCheck' as const,
  },
] as const;

export const PROFILE_INSTITUTE = {
  schoolCoaching: 'Narayana Coaching Institute — Hyderabad',
  batch: 'JEE Advanced Batch A2',
  mentor: 'Mr. Srinivas Reddy',
  instituteCode: 'NAR-HYD-11-A2',
} as const;

export const PROFILE_CURRENT_PLAN = {
  planName: 'ScholarSync Pro',
  limits: '50 sources / notebook • 200 AI messages / month',
  access: 'Library, Tutor, Analytics, Study Planner',
  renewal: 'Renews on 15 Aug 2026',
} as const;

export const PROFILE_LEARNING_PREFS = {
  teachingStyle: 'Step-by-step with examples',
  language: 'English',
  difficulty: 'Adaptive (based on mastery)',
  sessionLength: '45 minutes',
} as const;

export const PROFILE_NOTIFICATIONS = {
  studyReminders: true,
  testAlerts: true,
  masteryAlerts: true,
  weeklyReportSharing: 'Parent email',
} as const;

export const PROFILE_ACCOUNT = {
  loginEmail: 'rahul.kumar@email.com',
  lastPasswordChange: '3 months ago',
  devices: '2 active devices',
  dataControls: 'Export data • Delete account',
} as const;
