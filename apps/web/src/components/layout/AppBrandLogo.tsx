'use client';

import Link from 'next/link';
import { BookOpen } from 'lucide-react';

type AppBrandLogoProps = {
  showDivider?: boolean;
  className?: string;
};

export function AppBrandLogo({ showDivider = true, className = '' }: AppBrandLogoProps) {
  return (
    <div className={`app-brand-logo-wrap ${className}`.trim()}>
      <Link href="/home" className="app-brand-logo" aria-label="ScholarSync home">
        <span className="app-brand-logo__mark" aria-hidden="true">
          <BookOpen className="w-[18px] h-[18px]" strokeWidth={1.75} />
        </span>
        <span className="app-brand-logo__text">ScholarSync</span>
      </Link>
      {showDivider ? <span className="app-brand-logo__divider" aria-hidden="true" /> : null}
    </div>
  );
}
