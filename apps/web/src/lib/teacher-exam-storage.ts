'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  buildMockOmrRows,
  buildMockQuestions,
  createEmptyDraft,
  SEED_TEACHER_EXAMS,
} from './teacher-exam-mock-data';
import type { ExamWizardDraft, TeacherExam } from './teacher-exam-types';

const EXAMS_KEY = 'scholarsync:teacher-exams:v1';
const DRAFT_KEY = 'scholarsync:teacher-exam-draft:v1';

function readExams(): TeacherExam[] {
  if (typeof window === 'undefined') return SEED_TEACHER_EXAMS;
  try {
    const raw = localStorage.getItem(EXAMS_KEY);
    if (!raw) {
      writeExams(SEED_TEACHER_EXAMS);
      return SEED_TEACHER_EXAMS;
    }
    const parsed = JSON.parse(raw) as TeacherExam[];
    if (!Array.isArray(parsed) || parsed.length === 0) {
      writeExams(SEED_TEACHER_EXAMS);
      return SEED_TEACHER_EXAMS;
    }
    return parsed;
  } catch {
    return SEED_TEACHER_EXAMS;
  }
}

function writeExams(exams: TeacherExam[]) {
  localStorage.setItem(EXAMS_KEY, JSON.stringify(exams));
}

export function getAllExams(): TeacherExam[] {
  return readExams();
}

export function getExamById(id: string): TeacherExam | undefined {
  return readExams().find((e) => e.id === id);
}

export function saveExam(exam: TeacherExam): void {
  const exams = readExams();
  const idx = exams.findIndex((e) => e.id === exam.id);
  const updated = { ...exam, updatedAt: new Date().toISOString() };
  if (idx >= 0) {
    exams[idx] = updated;
  } else {
    exams.unshift(updated);
  }
  writeExams(exams);
}

export function deleteExam(id: string): void {
  writeExams(readExams().filter((e) => e.id !== id));
}

export function draftToExam(draft: ExamWizardDraft): TeacherExam {
  const now = new Date().toISOString();
  const id = draft.examId ?? `exam-${Date.now()}`;
  const existing = draft.examId ? getExamById(draft.examId) : undefined;

  return {
    id,
    status: existing?.status ?? 'draft',
    createdAt: existing?.createdAt ?? now,
    updatedAt: now,
    archivedAt: existing?.archivedAt,
    board: draft.board,
    classNum: draft.classNum ?? 10,
    subject: draft.subject,
    section: draft.section,
    examName: draft.examName,
    examDate: draft.examDate,
    marksCorrect: draft.marksCorrect,
    marksWrong: draft.marksWrong,
    marksUnanswered: draft.marksUnanswered,
    wizardStep: draft.step,
    questionPaperUploaded: draft.questionPaperUploaded,
    questionPaperFileName: draft.questionPaperFileName,
    questions: draft.questions.length > 0 ? draft.questions : buildMockQuestions(),
    answerKeyMode: draft.answerKeyMode,
    answerKeyUploaded: draft.answerKeyUploaded,
    answerKeyFileName: draft.answerKeyFileName,
    answers: draft.answers,
    omrUploaded: draft.omrUploaded,
    omrFileCount: draft.omrFileCount,
    omrRows: draft.omrRows.length > 0 ? draft.omrRows : buildMockOmrRows(),
    gradingSummary: existing?.gradingSummary,
  };
}

export function saveDraft(draft: ExamWizardDraft): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  if (draft.examId || draft.examName.trim()) {
    saveExam(draftToExam(draft));
  }
}

export function getDraft(): ExamWizardDraft {
  if (typeof window === 'undefined') return createEmptyDraft();
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return createEmptyDraft();
    return { ...createEmptyDraft(), ...JSON.parse(raw) };
  } catch {
    return createEmptyDraft();
  }
}

export function clearDraft(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(DRAFT_KEY);
}

export function loadDraftFromExam(examId: string): ExamWizardDraft | null {
  const exam = getExamById(examId);
  if (!exam) return null;
  return {
    examId: exam.id,
    step: exam.wizardStep < 6 ? exam.wizardStep : 1,
    board: exam.board,
    classNum: exam.classNum,
    subject: exam.subject,
    section: exam.section,
    examName: exam.examName,
    examDate: exam.examDate,
    marksCorrect: exam.marksCorrect,
    marksWrong: exam.marksWrong,
    marksUnanswered: exam.marksUnanswered,
    questionPaperUploaded: exam.questionPaperUploaded,
    questionPaperFileName: exam.questionPaperFileName,
    questions: exam.questions,
    answerKeyMode: exam.answerKeyMode,
    answerKeyUploaded: exam.answerKeyUploaded,
    answerKeyFileName: exam.answerKeyFileName,
    answers: exam.answers,
    omrUploaded: exam.omrUploaded,
    omrFileCount: exam.omrFileCount,
    omrRows: exam.omrRows,
  };
}

export function finishExamAsGraded(draft: ExamWizardDraft): TeacherExam {
  const exam = draftToExam({ ...draft, step: 6 });
  const graded: TeacherExam = {
    ...exam,
    status: 'graded',
    wizardStep: 6,
    omrUploaded: true,
    omrFileCount: draft.omrFileCount ?? 28,
    omrRows: draft.omrRows.length > 0 ? draft.omrRows : buildMockOmrRows(),
    gradingSummary: {
      studentsGraded: 28,
      averageScore: 14.2,
      maxScore: 20,
      weakConcepts: 3,
    },
  };
  saveExam(graded);
  clearDraft();
  return graded;
}

export function useTeacherExams() {
  const [exams, setExams] = useState<TeacherExam[]>(SEED_TEACHER_EXAMS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setExams(readExams());
    setHydrated(true);
  }, []);

  const refresh = useCallback(() => {
    setExams(readExams());
  }, []);

  return { exams, hydrated, refresh };
}
