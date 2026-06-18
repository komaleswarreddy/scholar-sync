'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Search } from 'lucide-react';
import { ExamCard } from '@/components/teacher/exams/ExamCard';
import { TeacherExamsTabToggle } from '@/components/teacher/exams/TeacherExamsTabToggle';
import { clearDraft } from '@/lib/teacher-exam-storage';
import { useTeacherExams } from '@/lib/teacher-exam-storage';
import type { ExamsListTab } from '@/lib/teacher-exam-types';

export default function TeacherExamsPage() {
  const router = useRouter();
  const { exams, hydrated } = useTeacherExams();
  const [tab, setTab] = useState<ExamsListTab>('upcoming');
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    let list = exams;
    if (tab === 'upcoming') list = exams.filter((e) => e.status === 'draft');
    if (tab === 'graded') list = exams.filter((e) => e.status === 'graded');
    if (tab === 'archived') list = exams.filter((e) => e.status === 'archived');

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (e) =>
          e.examName.toLowerCase().includes(q) ||
          e.subject.toLowerCase().includes(q) ||
          String(e.classNum).includes(q),
      );
    }
    return list;
  }, [exams, tab, search]);

  const counts: Record<ExamsListTab, number> = useMemo(
    () => ({
      upcoming: exams.filter((e) => e.status === 'draft').length,
      graded: exams.filter((e) => e.status === 'graded').length,
      archived: exams.filter((e) => e.status === 'archived').length,
    }),
    [exams],
  );

  const handleCreate = () => {
    clearDraft();
    router.push('/teacher/exams/new');
  };

  if (!hydrated) {
    return (
      <div className="teacher-exam-page">
        <div className="teacher-exam-page__loading">Loading exams…</div>
      </div>
    );
  }

  return (
    <div className="teacher-exam-page">
      <header className="teacher-exam-page__header">
        <h1 className="teacher-exam-page__title">Exams</h1>
        <div className="teacher-exam-page__actions">
          <div className="teacher-exam-page__search-wrap">
            <Search className="teacher-exam-page__search-icon" />
            <input
              type="search"
              className="teacher-exam-page__search"
              placeholder="Search exams…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button type="button" className="teacher-exam-page__create" onClick={handleCreate}>
            <Plus className="h-4 w-4" />
            Create exam
          </button>
        </div>
      </header>

      <TeacherExamsTabToggle active={tab} counts={counts} onChange={setTab} />

      {filtered.length === 0 ? (
        <div className="teacher-exam-empty">
          <p className="teacher-exam-empty__text">
            {search.trim()
              ? 'No exams match your search.'
              : tab === 'upcoming'
                ? 'No upcoming exams. Create one to get started.'
                : tab === 'graded'
                  ? 'No graded exams yet.'
                  : 'No archived exams.'}
          </p>
          {tab === 'upcoming' && !search.trim() && (
            <button type="button" className="teacher-exam-page__create" onClick={handleCreate}>
              <Plus className="h-4 w-4" />
              Create exam
            </button>
          )}
        </div>
      ) : (
        <div className="teacher-exam-card-grid">
          {filtered.map((exam) => (
            <ExamCard key={exam.id} exam={exam} tab={tab} />
          ))}
        </div>
      )}
    </div>
  );
}
