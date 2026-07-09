import { AdminTableSkeleton } from '@/components/skeleton';

/** Content-area fallback only — AdminSidebar/AdminHeader persist from the layout. */
export default function Loading() {
  return <AdminTableSkeleton />;
}
