'use client';

import { useEffect, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { CONCEPT_CATALOG, getConceptById } from '@/lib/teacher-exam-mock-data';

interface ConceptSelectProps {
  value: string | null;
  onChange: (conceptId: string | null) => void;
}

export function ConceptSelect({ value, onChange }: ConceptSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = getConceptById(value);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div className="teacher-exam-concept-select" ref={ref}>
      <button
        type="button"
        className="teacher-exam-concept-select__trigger"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className="teacher-exam-concept-select__display">
          {selected ? (
            <>
              <span className="teacher-exam-concept-select__title">{selected.title}</span>
              <span className="teacher-exam-concept-select__path">{selected.path}</span>
            </>
          ) : (
            <span className="teacher-exam-concept-select__placeholder">Select concept</span>
          )}
        </span>
        <ChevronDown className="h-4 w-4 flex-shrink-0 text-text-tertiary" />
      </button>

      {open && (
        <ul className="teacher-exam-concept-select__menu" role="listbox">
          <li>
            <button
              type="button"
              className="teacher-exam-concept-select__option"
              onClick={() => {
                onChange(null);
                setOpen(false);
              }}
            >
              <span className="teacher-exam-concept-select__placeholder">— None —</span>
            </button>
          </li>
          {CONCEPT_CATALOG.map((concept) => (
            <li key={concept.id}>
              <button
                type="button"
                className={`teacher-exam-concept-select__option${
                  value === concept.id ? ' teacher-exam-concept-select__option--selected' : ''
                }`}
                onClick={() => {
                  onChange(concept.id);
                  setOpen(false);
                }}
                role="option"
                aria-selected={value === concept.id}
              >
                <span className="teacher-exam-concept-select__title">{concept.title}</span>
                <span className="teacher-exam-concept-select__path">{concept.path}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
