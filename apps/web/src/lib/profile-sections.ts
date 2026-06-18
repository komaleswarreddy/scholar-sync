import type { LucideIcon } from 'lucide-react';
import {
  User,
  GraduationCap,
  Target,
  Building2,
  CreditCard,
  SlidersHorizontal,
  Bell,
  Shield,
} from 'lucide-react';

export type ProfileSectionId =
  | 'student-info'
  | 'academic-profile'
  | 'exam-goals'
  | 'institute-info'
  | 'current-plan'
  | 'learning-preferences'
  | 'notifications'
  | 'account-security';

export type ProfileSectionConfig = {
  id: ProfileSectionId;
  label: string;
  title: string;
  subtitle: string;
  icon: LucideIcon;
  href: string;
};

export const PROFILE_SECTIONS: ProfileSectionConfig[] = [
  {
    id: 'student-info',
    label: 'Student Info',
    title: 'Student Info',
    subtitle: 'Update your personal details and contact information.',
    icon: User,
    href: '/profile/student-info',
  },
  {
    id: 'academic-profile',
    label: 'Academic Profile',
    title: 'Academic Profile',
    subtitle: 'Your class, board, stream, and subjects for this academic year.',
    icon: GraduationCap,
    href: '/profile/academic-profile',
  },
  {
    id: 'exam-goals',
    label: 'Exam Goals',
    title: 'Exam Goals',
    subtitle: 'Define your target exams, outcomes, and preparation priorities.',
    icon: Target,
    href: '/profile/exam-goals',
  },
  {
    id: 'institute-info',
    label: 'Institute Info',
    title: 'Institute Info',
    subtitle: 'School or coaching setup, batch, and mentor details.',
    icon: Building2,
    href: '/profile/institute-info',
  },
  {
    id: 'current-plan',
    label: 'Current Plan',
    title: 'Current Plan',
    subtitle: 'Your product plan, usage limits, and renewal details.',
    icon: CreditCard,
    href: '/profile/current-plan',
  },
  {
    id: 'learning-preferences',
    label: 'Learning Preferences',
    title: 'Learning Preferences',
    subtitle: 'How AI tutoring, language, and sessions should work for you.',
    icon: SlidersHorizontal,
    href: '/profile/learning-preferences',
  },
  {
    id: 'notifications',
    label: 'Notifications',
    title: 'Notifications',
    subtitle: 'Reminders, alerts, and report sharing preferences.',
    icon: Bell,
    href: '/profile/notifications',
  },
  {
    id: 'account-security',
    label: 'Account & Security',
    title: 'Account & Security',
    subtitle: 'Login, password, devices, and data controls.',
    icon: Shield,
    href: '/profile/account-security',
  },
];

export const DEFAULT_PROFILE_SECTION: ProfileSectionId = 'student-info';

export function getProfileSection(id: string | undefined): ProfileSectionConfig {
  const found = PROFILE_SECTIONS.find((s) => s.id === id);
  return found ?? PROFILE_SECTIONS[0];
}

export function isValidProfileSection(id: string): id is ProfileSectionId {
  return PROFILE_SECTIONS.some((s) => s.id === id);
}
