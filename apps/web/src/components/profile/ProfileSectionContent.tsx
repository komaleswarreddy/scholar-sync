'use client';

import dynamic from 'next/dynamic';
import type { ProfileSectionId } from '@/lib/profile-sections';
import { ProfileFormSkeleton } from '@/components/skeleton';

const loading = () => <ProfileFormSkeleton />;

const DynamicSections: Record<ProfileSectionId, React.ComponentType> = {
  'student-info': dynamic(
    () => import('./sections/StudentInfoSection').then((m) => m.StudentInfoSection),
    { loading },
  ),
  'academic-profile': dynamic(
    () => import('./sections/AcademicProfileSection').then((m) => m.AcademicProfileSection),
    { loading },
  ),
  'exam-goals': dynamic(
    () => import('./sections/ExamGoalsSection').then((m) => m.ExamGoalsSection),
    { loading },
  ),
  'institute-info': dynamic(
    () => import('./sections/InstituteInfoSection').then((m) => m.InstituteInfoSection),
    { loading },
  ),
  'current-plan': dynamic(
    () => import('./sections/CurrentPlanSection').then((m) => m.CurrentPlanSection),
    { loading },
  ),
  'learning-preferences': dynamic(
    () => import('./sections/LearningPreferencesSection').then((m) => m.LearningPreferencesSection),
    { loading },
  ),
  notifications: dynamic(
    () => import('./sections/NotificationsSection').then((m) => m.NotificationsSection),
    { loading },
  ),
  'account-security': dynamic(
    () => import('./sections/AccountSecuritySection').then((m) => m.AccountSecuritySection),
    { loading },
  ),
};

export function ProfileSectionContent({ sectionId }: { sectionId: ProfileSectionId }) {
  const Section = DynamicSections[sectionId];
  return <Section />;
}
