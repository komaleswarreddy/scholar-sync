'use client';

import { AppBrandLogo } from './AppBrandLogo';
import { SettingsDropdown } from './SettingsDropdown';
import { TeacherUserMenu } from './TeacherUserMenu';

export function TeacherHeader() {
  return (
    <header className="home-top-nav home-top-nav--compact">
      <div className="home-top-nav__start">
        <AppBrandLogo showDivider={false} />
        <p className="text-[14px] font-semibold text-[var(--color-home-text)] truncate">
          Teacher portal
        </p>
      </div>

      <div className="home-top-nav__end">
        <SettingsDropdown />
        <TeacherUserMenu />
      </div>
    </header>
  );
}
