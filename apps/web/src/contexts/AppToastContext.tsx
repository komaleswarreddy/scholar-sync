'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';

const DEFAULT_TOAST_MS = 2800;
export const TOAST_MIN_VISIBLE_MS = 700;

type ShowToastOptions = {
  /** Keep toast on screen at least this long (returns a promise you can await before navigating). */
  minVisibleMs?: number;
  /** Total time before auto-dismiss (defaults to max(DEFAULT_TOAST_MS, minVisibleMs)). */
  durationMs?: number;
};

type AppToastContextValue = {
  showToast: (message: string, options?: ShowToastOptions) => void | Promise<void>;
};

const AppToastContext = createContext<AppToastContextValue | null>(null);

export function AppToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const hideTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    setMounted(true);
    return () => {
      if (hideTimeoutRef.current) {
        window.clearTimeout(hideTimeoutRef.current);
      }
    };
  }, []);

  const showToast = useCallback((text: string, options?: ShowToastOptions) => {
    if (hideTimeoutRef.current) {
      window.clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }

    setMessage(text);

    const minVisibleMs = options?.minVisibleMs;
    const durationMs = options?.durationMs ?? Math.max(DEFAULT_TOAST_MS, minVisibleMs ?? 0);

    hideTimeoutRef.current = window.setTimeout(() => {
      setMessage(null);
      hideTimeoutRef.current = null;
    }, durationMs);

    if (minVisibleMs != null && minVisibleMs > 0) {
      return new Promise<void>((resolve) => {
        window.setTimeout(resolve, minVisibleMs);
      });
    }
  }, []);

  const value = useMemo(() => ({ showToast }), [showToast]);

  const toastNode =
    message && mounted
      ? createPortal(
          <div className="assets-toast" role="status" aria-live="polite" aria-atomic="true">
            {message}
          </div>,
          document.body,
        )
      : null;

  return (
    <AppToastContext.Provider value={value}>
      {children}
      {toastNode}
    </AppToastContext.Provider>
  );
}

export function useAppToast() {
  const ctx = useContext(AppToastContext);
  if (!ctx) {
    throw new Error('useAppToast must be used within AppToastProvider');
  }
  return ctx;
}

export function useAppToastOptional() {
  return useContext(AppToastContext);
}
