import { ProfileFormSkeleton } from '@/components/skeleton';

export default function Loading() {
  return (
    <div className="max-w-[1280px] mx-auto px-4 md:px-8 py-6 md:py-8">
      <ProfileFormSkeleton />
    </div>
  );
}
