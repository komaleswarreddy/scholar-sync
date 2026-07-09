'use client';

import { FormEvent, useEffect, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { BookOpen, GraduationCap, Loader2, Lock, Sparkles, User } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { prefetchStudentPortalData } from '@/hooks/usePrefetchStudentData';
import { prefetchAdminPortalData } from '@/hooks/usePrefetchAdminData';
import { hasPlatformSession, getStoredPlatformUser, getPlatformToken, isSchoolAdmin, SIGN_OUT_QUERY } from '@/lib/platform-auth';
import { AppBrandLogo } from '@/components/layout/AppBrandLogo';

const FEATURES = [
  {
    icon: BookOpen,
    title: 'AI notebooks',
    description: 'Upload sources, chat with your materials, and build understanding.',
  },
  {
    icon: GraduationCap,
    title: 'NCERT tutor mode',
    description: 'Structured study paths aligned to your class and syllabus.',
  },
  {
    icon: Sparkles,
    title: 'Study studio',
    description: 'Generate quizzes, flashcards, and mind maps from your notes.',
  },
] as const;

export default function SignInPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get(SIGN_OUT_QUERY) === '1') {
      return;
    }
    if (!hasPlatformSession()) return;
    const user = getStoredPlatformUser();
    const token = getPlatformToken();
    if (isSchoolAdmin(user, token)) {
      router.replace('/admin/users');
    } else {
      router.replace('/home');
    }
  }, [router]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await apiClient.login(username.trim(), password);
      if (user.role === 'schooladmin' || user.is_bootstrap_admin) {
        prefetchAdminPortalData(queryClient);
        router.replace('/admin/users');
      } else {
        prefetchStudentPortalData(queryClient);
        router.replace('/home');
      }
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Invalid username or password';
      setError(typeof message === 'string' ? message : 'Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-sign-in-page">
      <aside className="auth-sign-in-hero" aria-hidden={false}>
        <div className="auth-sign-in-hero__content">
          <AppBrandLogo showDivider={false} />
          <p className="home-section-label mt-10">ScholarSync</p>
          <h1 className="auth-sign-in-hero__title">
            Sign in to
            <span className="auth-sign-in-hero__title-accent">your AI study workspace.</span>
          </h1>
          <p className="auth-sign-in-hero__subtitle">
            Students, teachers, and school admins use one login. Accounts are created by your school administrator.
          </p>
          <ul className="auth-sign-in-features">
            {FEATURES.map(({ icon: Icon, title, description }) => (
              <li key={title} className="auth-sign-in-feature">
                <span className="auth-sign-in-feature__icon" aria-hidden>
                  <Icon className="w-[18px] h-[18px]" strokeWidth={1.75} />
                </span>
                <span>
                  <strong className="font-semibold text-[var(--color-home-text)]">{title}</strong>
                  <span className="block text-[13px] text-[var(--color-home-text-muted)] mt-0.5">
                    {description}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="auth-sign-in-hero__landscape" aria-hidden>
          <Image
            src="/images/home/hero-landscape-right.png"
            alt=""
            width={560}
            height={320}
            className="hero-landscape-img w-full h-auto"
            priority
          />
        </div>
      </aside>

      <main className="auth-sign-in-panel">
        <div className="auth-sign-in-card">
          <div className="auth-sign-in-card__mobile-logo">
            <AppBrandLogo showDivider={false} />
          </div>

          <p className="home-section-label hidden lg:block">Welcome back</p>
          <h2 className="auth-sign-in-card__title mt-2 lg:mt-3">Sign in</h2>
          <p className="auth-sign-in-card__subtitle">
            Enter your username and password to access ScholarSync.
          </p>

          {error && (
            <div className="auth-sign-in-error mt-6" role="alert">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className={`space-y-4 ${error ? 'mt-4' : 'mt-8'}`}>
            <div>
              <label htmlFor="username" className="auth-sign-in-field">
                Username
              </label>
              <div className="auth-sign-in-input-wrap">
                <User className="auth-sign-in-input-icon" aria-hidden />
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="auth-sign-in-input"
                  placeholder="Your username"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="auth-sign-in-field">
                Password
              </label>
              <div className="auth-sign-in-input-wrap">
                <Lock className="auth-sign-in-input-icon" aria-hidden />
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="auth-sign-in-input"
                  placeholder="Your password"
                  required
                />
              </div>
            </div>

            <button type="submit" disabled={loading} className="auth-sign-in-submit">
              {loading ? (
                <span className="inline-flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
                  Signing in…
                </span>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          <p className="auth-sign-in-footer">
            Accounts are created by your school admin.
            <br />
            Contact your administrator if you need access.
          </p>
      </div>
      </main>
    </div>
  );
}
