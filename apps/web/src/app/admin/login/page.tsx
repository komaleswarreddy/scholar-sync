import { redirect } from 'next/navigation';

/** Redirect legacy admin login to unified sign-in. */
export default function AdminLoginPage() {
  redirect('/sign-in');
}
