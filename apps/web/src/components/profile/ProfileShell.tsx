'use client';

import { ReactNode } from 'react';
import { HomeTopNav } from '@/components/home/HomeTopNav';
import { ProfileCompletionSidebar } from './ProfileCompletionSidebar';
import { ProfileSidebar } from './ProfileSidebar';
import { getProfileSection, type ProfileSectionId } from '@/lib/profile-sections';

type ProfileShellProps = {
  sectionId: ProfileSectionId;
  children: ReactNode;
};

export function ProfileShell({ sectionId, children }: ProfileShellProps) {
  const section = getProfileSection(sectionId);

  return (
    <div className="min-h-screen flex flex-col home-page profile-page">
      <HomeTopNav activeStyle="pill" />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[1280px] mx-auto px-4 md:px-8 py-6 md:py-8">
          <div className="flex flex-col lg:flex-row gap-8 lg:gap-10">
            <ProfileSidebar activeSection={sectionId} />

            <div className="flex-1 min-w-0">
              <div className="mb-6">
                <h1 className="text-[26px] sm:text-[28px] font-bold text-[var(--color-home-text)] tracking-tight">
                  {section.title}
                </h1>
                <p className="text-[15px] text-[var(--color-home-text-muted)] mt-1.5">
                  {section.subtitle}
                </p>
              </div>

              {children}

              <div className="mt-6 lg:hidden">
                <ProfileCompletionSidebar />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
