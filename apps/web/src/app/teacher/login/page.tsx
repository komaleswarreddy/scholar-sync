'use client';

import { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  hasTeacherSession,
  setTeacherToken,
  TEACHER_PORTAL_EMAIL,
  validateTeacherLogin,
} from '@/lib/teacher-auth';

export default function TeacherLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState(TEACHER_PORTAL_EMAIL);
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (hasTeacherSession()) {
      router.replace('/teacher/exams');
    }
  }, [router]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (!validateTeacherLogin(email, password)) {
        throw new Error('Invalid email or password');
      }
      setTeacherToken('teacher-portal-session');
      router.replace('/teacher/exams');
    } catch (err: unknown) {
      const message = (err as Error)?.message || 'Invalid email or password';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F9FAFB] px-4">
      <div className="w-full max-w-md rounded-2xl border border-border-default bg-white p-8 shadow-sm">
        <div className="mb-8 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">Teacher portal</p>
          <h1 className="mt-2 text-2xl font-semibold text-text-primary">Sign in to teacher</h1>
          <p className="mt-2 text-sm text-text-secondary">
            Manage exams and classroom content for your students.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="teacher-email" className="mb-1.5 block text-sm font-medium text-text-primary">
              Email
            </label>
            <input
              id="teacher-email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-border-default px-3 py-2.5 text-sm text-text-primary outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
              required
            />
          </div>

          <div>
            <label htmlFor="teacher-password" className="mb-1.5 block text-sm font-medium text-text-primary">
              Password
            </label>
            <input
              id="teacher-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-border-default px-3 py-2.5 text-sm text-text-primary outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
              required
            />
          </div>

          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? 'Signing in...' : 'Sign in to teacher'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-secondary">
          Student account?{' '}
          <Link href="/sign-in" className="font-medium text-accent-blue hover:underline">
            Back to student login
          </Link>
        </p>
      </div>
    </div>
  );
}
