/**
 * Dashboard Layout
 * 
 * Layout with:
 * - Top Header (ribbon with logo, actions, user menu)
 * - 3-Column Grid Layout:
 *   - Column 1: Source Management (Left Sidebar)
 *   - Column 2: Chat Interface (Center)
 *   - Column 3: Studio Suite (Top) + Notes (Bottom) (Right Sidebar)
 * 
 * Note: This is a server component that wraps a client component.
 * Next.js App Router layouts cannot be client components directly.
 */

import { DashboardWrapper } from '@/components/layout/DashboardWrapper';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <DashboardWrapper>{children}</DashboardWrapper>;
}

