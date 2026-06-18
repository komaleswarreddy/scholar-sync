'use client';

import { useMemo, useState } from 'react';
import { AlertCircle, Check, Pencil } from 'lucide-react';
import { CONCEPT_CATALOG, getConceptById } from '@/lib/teacher-exam-mock-data';
import type { ConceptMappingStatus, ExamQuestion, ExamWizardDraft } from '@/lib/teacher-exam-types';
import { ConceptSelect } from './ConceptSelect';

type FilterOption = 'all' | 'needs_review' | 'edited' | 'auto_mapped';

interface ConceptMappingStepProps {
  draft: ExamWizardDraft;
  onChange: (patch: Partial<ExamWizardDraft>) => void;
}

function StatusPill({ status }: { status: ConceptMappingStatus }) {
  if (status === 'needs_review') {
    return (
      <span className="teacher-exam-status-pill teacher-exam-status-pill--review">
        <AlertCircle className="h-3.5 w-3.5" />
        Needs review
      </span>
    );
  }
  if (status === 'edited') {
    return (
      <span className="teacher-exam-status-pill teacher-exam-status-pill--edited">
        <Pencil className="h-3.5 w-3.5" />
        Edited
      </span>
    );
  }
  return (
    <span className="teacher-exam-status-pill teacher-exam-status-pill--auto">
      <Check className="h-3.5 w-3.5" />
      Auto-mapped
    </span>
  );
}

export function ConceptMappingStep({ draft, onChange }: ConceptMappingStepProps) {
  const [filter, setFilter] = useState<FilterOption>('all');
  const [search, setSearch] = useState('');

  const counts = useMemo(() => {
    const questions = draft.questions;
    return {
      total: questions.length,
      auto: questions.filter((q) => q.mappingStatus === 'auto_mapped').length,
      review: questions.filter((q) => q.mappingStatus === 'needs_review').length,
      edited: questions.filter((q) => q.mappingStatus === 'edited').length,
    };
  }, [draft.questions]);

  const filtered = useMemo(() => {
    let rows = draft.questions;
    if (filter === 'needs_review') rows = rows.filter((q) => q.mappingStatus === 'needs_review');
    if (filter === 'edited') rows = rows.filter((q) => q.mappingStatus === 'edited');
    if (filter === 'auto_mapped') rows = rows.filter((q) => q.mappingStatus === 'auto_mapped');
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(
        (row) =>
          row.preview.toLowerCase().includes(q) ||
          row.autoDetectedPath.toLowerCase().includes(q) ||
          getConceptById(row.approvedConceptId)?.title.toLowerCase().includes(q),
      );
    }
    return rows;
  }, [draft.questions, filter, search]);

  const updateQuestion = (id: string, patch: Partial<ExamQuestion>) => {
    onChange({
      questions: draft.questions.map((q) => (q.id === id ? { ...q, ...patch } : q)),
    });
  };

  const handleConceptChange = (question: ExamQuestion, conceptId: string | null) => {
    if (!conceptId) {
      updateQuestion(question.id, {
        approvedConceptId: null,
        mappingStatus: 'needs_review',
      });
      return;
    }
    const autoConcept = getConceptById(conceptIdFromPath(question.autoDetectedPath));
    const isEdited = autoConcept?.id !== conceptId;
    updateQuestion(question.id, {
      approvedConceptId: conceptId,
      mappingStatus: isEdited ? 'edited' : 'auto_mapped',
    });
  };

  return (
    <div className="teacher-exam-step teacher-exam-step--wide">
      <h2 className="teacher-exam-step__title">Concept mapping</h2>
      <p className="teacher-exam-step__summary">
        {counts.total} questions · {counts.auto} auto-mapped · {counts.review} needs review ·{' '}
        {counts.edited} edited
      </p>

      <div className="teacher-exam-concept-toolbar">
        <select
          className="teacher-exam-concept-toolbar__filter"
          value={filter}
          onChange={(e) => setFilter(e.target.value as FilterOption)}
        >
          <option value="all">All questions</option>
          <option value="needs_review">Needs review</option>
          <option value="edited">Edited</option>
          <option value="auto_mapped">Auto-mapped</option>
        </select>
        <input
          type="search"
          className="teacher-exam-concept-toolbar__search"
          placeholder="Search questions or concepts…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="teacher-exam-concept-table-wrap">
        <table className="teacher-exam-concept-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Question preview</th>
              <th>Auto-detected concept</th>
              <th>Approved concept</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((q) => (
              <tr key={q.id}>
                <td className="teacher-exam-concept-table__num">{q.number}</td>
                <td className="teacher-exam-concept-table__preview">{q.preview}</td>
                <td className="teacher-exam-concept-table__path">{q.autoDetectedPath}</td>
                <td className="teacher-exam-concept-table__select">
                  <ConceptSelect
                    value={q.approvedConceptId}
                    onChange={(id) => handleConceptChange(q, id)}
                  />
                </td>
                <td>
                  <StatusPill status={q.mappingStatus} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
}

function conceptIdFromPath(path: string): string | null {
  return CONCEPT_CATALOG.find((c) => c.path === path)?.id ?? null;
}
