import { NotesListSkeleton } from '@/components/skeleton';

export default function Loading() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <NotesListSkeleton />
    </div>
  );
}
