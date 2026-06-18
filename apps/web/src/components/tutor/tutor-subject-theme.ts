import type { LucideIcon } from 'lucide-react';
import {
  Atom,
  BookOpen,
  Coins,
  FlaskConical,
  Globe,
  Landmark,
  Scale,
  Sigma,
} from 'lucide-react';

export type SubjectTheme = {
  Icon: LucideIcon;
  iconBg: string;
  iconColor: string;
};

export const SUBJECT_THEME_MAP: Record<string, SubjectTheme> = {
  physics: { Icon: Atom, iconBg: '#EAF2FF', iconColor: '#2875DD' },
  chemistry: { Icon: FlaskConical, iconBg: '#FDF2E2', iconColor: '#E58B1A' },
  mathematics: { Icon: Sigma, iconBg: '#EEF7F0', iconColor: '#1C8C5C' },
  biology: { Icon: BookOpen, iconBg: '#EEF7F0', iconColor: '#1C8C5C' },
  science: { Icon: FlaskConical, iconBg: '#FDF2E2', iconColor: '#E58B1A' },
  history: { Icon: Landmark, iconBg: '#F4F4F5', iconColor: '#71717A' },
  geography: { Icon: Globe, iconBg: '#EAF2FF', iconColor: '#2875DD' },
  'civics-polity': { Icon: Scale, iconBg: '#EDF7F2', iconColor: '#21594F' },
  economics: { Icon: Coins, iconBg: '#FDF2E2', iconColor: '#E58B1A' },
};

export function getSubjectTheme(subjectId: string): SubjectTheme {
  return SUBJECT_THEME_MAP[subjectId] ?? { Icon: BookOpen, iconBg: '#F4F4F5', iconColor: '#71717A' };
}
