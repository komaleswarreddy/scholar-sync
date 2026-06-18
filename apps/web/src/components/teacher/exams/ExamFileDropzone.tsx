'use client';

import { useCallback, useRef, useState } from 'react';
import { FileUp, Upload } from 'lucide-react';

interface ExamFileDropzoneProps {
  accept?: string;
  hint: string;
  subhint?: string;
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

export function ExamFileDropzone({
  accept,
  hint,
  subhint,
  onFileSelect,
  disabled = false,
}: ExamFileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files?.length || disabled) return;
      onFileSelect(files[0]);
    },
    [disabled, onFileSelect],
  );

  return (
    <div
      className={`teacher-exam-dropzone${dragOver ? ' teacher-exam-dropzone--active' : ''}${
        disabled ? ' teacher-exam-dropzone--disabled' : ''
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(e) => handleFiles(e.target.files)}
        disabled={disabled}
      />
      <div className="teacher-exam-dropzone__icon">
        {dragOver ? <FileUp className="h-8 w-8" /> : <Upload className="h-8 w-8" />}
      </div>
      <p className="teacher-exam-dropzone__hint">{hint}</p>
      {subhint && <p className="teacher-exam-dropzone__subhint">{subhint}</p>}
    </div>
  );
}
