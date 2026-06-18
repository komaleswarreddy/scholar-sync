'use client';

import {
  Award,
  BookOpen,
  Brain,
  Calendar,
  CalendarCheck,
  Clock,
  LineChart,
  PieChart,
  Sparkles,
  Star,
  Target,
  Trophy,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { PROFILE_EXAM_GOALS } from '@/lib/profile-mock-data';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

const goalIcons: Record<(typeof PROFILE_EXAM_GOALS)[number]['icon'], LucideIcon> = {
  target: Target,
  star: Star,
  calendar: Calendar,
  medal: Award,
  pie: PieChart,
  book: BookOpen,
  clock: Clock,
  brain: Brain,
  calendarCheck: CalendarCheck,
};

export function ExamGoalsSection() {
  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader hideAvatar />

      <div className="profile-exam-goals-panel">
        <h3 className="profile-exam-panel-title">Your Exam Goals</h3>

        <div className="profile-exam-goals-grid">
          {PROFILE_EXAM_GOALS.map((goal) => {
            const Icon = goalIcons[goal.icon];
            return (
              <div
                key={goal.number}
                className={`profile-exam-goal-card profile-exam-goal-card--${goal.number}`}
              >
                <div className="profile-exam-goal-body">
                  <div className="profile-exam-goal-icon">
                    <Icon className="w-4 h-4" strokeWidth={1.75} aria-hidden />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="profile-exam-goal-label">
                      {goal.number}. {goal.label}
                    </p>
                    {'tags' in goal && goal.tags ? (
                      <div className="profile-exam-goal-tags">
                        {goal.tags.map((tag) => (
                          <span key={tag} className="profile-exam-subject-pill">
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="profile-exam-goal-value">{goal.value}</p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="profile-exam-help-box">
          <div className="profile-exam-help-art" aria-hidden>
            <div className="profile-exam-podium">
              <div className="profile-exam-podium-tier profile-exam-podium-tier--2" />
              <div className="profile-exam-podium-tier profile-exam-podium-tier--1" />
              <div className="profile-exam-podium-tier profile-exam-podium-tier--3" />
            </div>
            <Trophy className="profile-exam-trophy-icon w-10 h-10" strokeWidth={1.5} />
            <Sparkles className="w-4 h-4 text-[var(--color-brand-text)] opacity-30 absolute top-2 right-8" />
            <Sparkles className="w-3 h-3 text-[var(--color-brand-text)] opacity-25 absolute bottom-6 right-2" />
          </div>

          <div className="profile-exam-help-content">
            <div className="profile-exam-help-icon-circle">
              <LineChart className="w-5 h-5 text-[var(--color-brand-text)]" strokeWidth={1.75} />
            </div>
            <p className="profile-exam-help-text">
              <span className="profile-exam-help-title">How this helps: </span>
              Your goals help us personalize your tutor guidance, create smarter study plans, and
              send focus alerts that keep you aligned with your targets.
            </p>
          </div>
        </div>
      </div>

      <ProfileFormFooter />
    </div>
  );
}
