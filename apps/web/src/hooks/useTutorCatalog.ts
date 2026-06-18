import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';

export const tutorCatalogKeys = {
  all: ['tutor-catalog'] as const,
  subjects: (classNum: number) => [...tutorCatalogKeys.all, 'subjects', classNum] as const,
  chapters: (classNum: number, subject: string) =>
    [...tutorCatalogKeys.all, 'chapters', classNum, subject] as const,
  concepts: (classNum: number, subject: string, chapterNo: number) =>
    [...tutorCatalogKeys.all, 'concepts', classNum, subject, chapterNo] as const,
  featured: (classNum: number, subject: string, chapterNo: number) =>
    [...tutorCatalogKeys.all, 'featured', classNum, subject, chapterNo] as const,
};

export function useTutorSubjects(classNum: number) {
  return useQuery({
    queryKey: tutorCatalogKeys.subjects(classNum),
    queryFn: async () => {
      try {
        const data = await apiClient.getTutorCatalog({ class_num: classNum });
        return data.subjects ?? [];
      } catch (error: unknown) {
        const apiError =
          (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
          handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    staleTime: 60_000,
  });
}

export function useTutorChapters(classNum: number, subjectKey: string | null) {
  return useQuery({
    queryKey: tutorCatalogKeys.chapters(classNum, subjectKey || ''),
    queryFn: async () => {
      if (!subjectKey) return [];
      try {
        const data = await apiClient.getTutorCatalog({
          class_num: classNum,
          subject: subjectKey,
        });
        return data.chapters ?? [];
      } catch (error: unknown) {
        const apiError =
          (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
          handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: Boolean(subjectKey),
    staleTime: 60_000,
  });
}

export function useTutorConcepts(
  classNum: number,
  subjectKey: string | null,
  chapterNo: number | null,
) {
  return useQuery({
    queryKey: tutorCatalogKeys.concepts(classNum, subjectKey || '', chapterNo ?? 0),
    queryFn: async () => {
      if (!subjectKey || chapterNo == null) return [];
      try {
        const data = await apiClient.getTutorCatalog({
          class_num: classNum,
          subject: subjectKey,
          chapter_no: chapterNo,
        });
        return data.concepts ?? [];
      } catch (error: unknown) {
        const apiError =
          (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
          handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: Boolean(subjectKey) && chapterNo != null,
    staleTime: 60_000,
  });
}

export function useTutorFeaturedNotebooks(
  classNum: number,
  subjectKey: string | null,
  chapterNo: number | null,
) {
  return useQuery({
    queryKey: tutorCatalogKeys.featured(classNum, subjectKey || '', chapterNo ?? 0),
    queryFn: async () => {
      if (!subjectKey || chapterNo == null) return [];
      try {
        const data = await apiClient.getTutorFeaturedNotebooks({
          class_num: classNum,
          subject: subjectKey,
          chapter_no: chapterNo,
        });
        return data.notebooks ?? [];
      } catch (error: unknown) {
        const apiError =
          (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
          handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: Boolean(subjectKey) && chapterNo != null,
    staleTime: 30_000,
  });
}

export const TUTOR_CLASS_STORAGE_KEY = 'tutorClassNum';

export const TUTOR_CLASS_OPTIONS = [12] as const;
export type TutorClassNum = (typeof TUTOR_CLASS_OPTIONS)[number];

/** Default class level for Tutor Mode and navbar context. */
export const TUTOR_DEFAULT_CLASS: TutorClassNum = 12;

export function readStoredTutorClass(): TutorClassNum {
  if (typeof window === 'undefined') return TUTOR_DEFAULT_CLASS;
  try {
    const raw = window.localStorage.getItem(TUTOR_CLASS_STORAGE_KEY);
    const n = raw ? parseInt(raw, 10) : TUTOR_DEFAULT_CLASS;
    return n === 12 ? n : TUTOR_DEFAULT_CLASS;
  } catch {
    return TUTOR_DEFAULT_CLASS;
  }
}

export function writeStoredTutorClass(classNum: TutorClassNum) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(TUTOR_CLASS_STORAGE_KEY, String(classNum));
  } catch {
    // ignore
  }
}
