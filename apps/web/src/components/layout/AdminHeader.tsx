'use client';

import { AppBrandLogo } from './AppBrandLogo';
import { SettingsDropdown } from './SettingsDropdown';
import { AdminUserMenu } from './AdminUserMenu';

export function AdminHeader() {
  return (
    <header className="home-top-nav home-top-nav--compact">
      <div className="home-top-nav__start">
        <AppBrandLogo showDivider={false} />
        <p className="text-[14px] font-semibold text-[var(--color-home-text)] truncate">
          Analytics admin
        </p>
      </div>

      <div className="home-top-nav__end">
        <SettingsDropdown />
        <AdminUserMenu />
      </div>
    </header>
  );
}
