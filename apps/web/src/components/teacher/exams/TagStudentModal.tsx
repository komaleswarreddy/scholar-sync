'use client';

import { useState } from 'react';
import { X } from 'lucide-react';

interface TagStudentModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (rollNumber: number) => void;
}

export function TagStudentModal({ open, onClose, onSave }: TagStudentModalProps) {
  const [roll, setRoll] = useState('');

  if (!open) return null;

  const handleSave = () => {
    const num = parseInt(roll, 10);
    if (!Number.isNaN(num) && num > 0) {
      onSave(num);
      setRoll('');
      onClose();
    }
  };

  return (
    <div className="teacher-exam-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="tag-student-title">
      <div className="teacher-exam-modal">
        <div className="teacher-exam-modal__header">
          <h3 id="tag-student-title" className="teacher-exam-modal__title">
            Tag student manually
          </h3>
          <button type="button" className="teacher-exam-modal__close" onClick={onClose} aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="teacher-exam-modal__body">
          <label className="teacher-exam-field__label" htmlFor="tag-roll">
            Roll number
          </label>
          <input
            id="tag-roll"
            type="number"
            min={1}
            className="teacher-exam-field__input"
            placeholder="Enter roll number"
            value={roll}
            onChange={(e) => setRoll(e.target.value)}
            autoFocus
          />
        </div>
        <div className="teacher-exam-modal__footer">
          <button type="button" className="teacher-exam-modal__cancel" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="teacher-exam-modal__save"
            onClick={handleSave}
            disabled={!roll.trim()}
          >
            Save tag
          </button>
        </div>
      </div>
    </div>
  );
}
