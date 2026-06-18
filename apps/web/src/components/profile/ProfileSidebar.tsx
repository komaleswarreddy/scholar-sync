'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { PROFILE_SECTIONS, type ProfileSectionId } from '@/lib/profile-sections';
import { ProfileCompletionSidebar } from './ProfileCompletionSidebar';

type ProfileSidebarProps = {
  activeSection: ProfileSectionId;
};

export function ProfileSidebar({ activeSection }: ProfileSidebarProps) {
  return (
    <aside className="profile-sidebar flex flex-col w-full lg:w-[240px] flex-shrink-0">
      <Link
        href="/home"
        className="flex items-center gap-1.5 text-[14px] font-medium text-[var(--color-home-text-muted)] hover:text-[var(--color-brand-text)] mb-5 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Home
      </Link>

      <p className="text-[11px] font-semibold tracking-[0.14em] uppercase text-[var(--color-home-label)] mb-3">
        STUDENT PROFILE
      </p>

      <nav className="flex flex-col gap-0.5 flex-1">
        {PROFILE_SECTIONS.map(({ id, label, icon: Icon, href }) => {
          const active = activeSection === id;
          return (
            <Link
              key={id}
              href={href}
              className={`profile-sidebar-link ${active ? 'profile-sidebar-link--active profile-sidebar-link--bar' : ''}`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" strokeWidth={1.75} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-6 lg:mt-8 hidden lg:block">
        <ProfileCompletionSidebar />
      </div>
    </aside>
  );
}
