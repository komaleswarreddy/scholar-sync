'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import {
  readStoredTutorClass,
  TUTOR_CLASS_OPTIONS,
  writeStoredTutorClass,
  type TutorClassNum,
} from '@/hooks/useTutorCatalog';

interface TutorClassContextType {
  classNum: TutorClassNum;
  setClassNum: (classNum: TutorClassNum) => void;
}

const TutorClassContext = createContext<TutorClassContextType | undefined>(undefined);

export function TutorClassProvider({ children }: { children: ReactNode }) {
  const [classNum, setClassNumState] = useState<TutorClassNum>(() => readStoredTutorClass());

  useEffect(() => {
    setClassNumState(readStoredTutorClass());
  }, []);

  const setClassNum = useCallback((next: TutorClassNum) => {
    if (!TUTOR_CLASS_OPTIONS.includes(next)) return;
    setClassNumState(next);
    writeStoredTutorClass(next);
  }, []);

  return (
    <TutorClassContext.Provider value={{ classNum, setClassNum }}>
      {children}
    </TutorClassContext.Provider>
  );
}

export function useTutorClass() {
  const ctx = useContext(TutorClassContext);
  if (!ctx) {
    throw new Error('useTutorClass must be used within TutorClassProvider');
  }
  return ctx;
}

export function useTutorClassOptional() {
  return useContext(TutorClassContext);
}
