'use client';

import type { ReactElement } from 'react';
import type { ProfileSectionId } from '@/lib/profile-sections';
import { StudentInfoSection } from './sections/StudentInfoSection';
import { AcademicProfileSection } from './sections/AcademicProfileSection';
import { ExamGoalsSection } from './sections/ExamGoalsSection';
import { InstituteInfoSection } from './sections/InstituteInfoSection';
import { CurrentPlanSection } from './sections/CurrentPlanSection';
import { LearningPreferencesSection } from './sections/LearningPreferencesSection';
import { NotificationsSection } from './sections/NotificationsSection';
import { AccountSecuritySection } from './sections/AccountSecuritySection';

const sectionComponents: Record<ProfileSectionId, () => ReactElement> = {
  'student-info': StudentInfoSection,
  'academic-profile': AcademicProfileSection,
  'exam-goals': ExamGoalsSection,
  'institute-info': InstituteInfoSection,
  'current-plan': CurrentPlanSection,
  'learning-preferences': LearningPreferencesSection,
  notifications: NotificationsSection,
  'account-security': AccountSecuritySection,
};

export function ProfileSectionContent({ sectionId }: { sectionId: ProfileSectionId }) {
  const Section = sectionComponents[sectionId];
  return <Section />;
}
