import { redirect } from 'next/navigation';
import { DEFAULT_PROFILE_SECTION } from '@/lib/profile-sections';

export default function ProfileIndexPage() {
  redirect(`/profile/${DEFAULT_PROFILE_SECTION}`);
}
