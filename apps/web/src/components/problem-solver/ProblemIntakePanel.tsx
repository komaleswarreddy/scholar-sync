'use client';

import { useRef, useState } from 'react';
import { ImagePlus, Loader2, Upload } from 'lucide-react';
import { useNotebookContext } from '@/contexts/NotebookContext';
import { useProblemSolverContext } from '@/contexts/ProblemSolverContext';
import { useUploadSource } from '@/hooks/useSources';
import { useExtractProblemSolverFromSource } from '@/hooks/useProblemSolver';
import { apiClient } from '@/lib/api-client';
import { getUserFriendlyMessage, handleApiError } from '@/lib/error-handler';
import styles from '@/components/tutor/tutor-mode.module.css';

const ACCEPTED_TYPES =
  'image/*,.pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document';

export function ProblemIntakePanel() {
  const { notebook } = useNotebookContext();
  const { submitProblem, setExtracting } = useProblemSolverContext();
  const uploadSource = useUploadSource(notebook.id);
  const extractFromSource = useExtractProblemSolverFromSource();

  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleTextSubmit = async () => {
    const trimmed = text.trim();
    if (trimmed.length < 10) {
      setError('Please enter at least 10 characters describing your problem.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await submitProblem(trimmed, 'text');
      setText('');
    } catch (e: unknown) {
      const apiError = handleApiError(e);
      setError(getUserFriendlyMessage(apiError));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFile = async (file: File) => {
    setError(null);
    setIsSubmitting(true);
    setExtracting(true);
    try {
      const uploaded = await uploadSource.mutateAsync({
        file,
        title: file.name,
      });
      const sourceId = uploaded?.id as string | undefined;
      if (!sourceId) {
        throw new Error('Upload did not return a source id');
      }

      let indexed = false;
      for (let attempt = 0; attempt < 30; attempt++) {
        await new Promise((r) => setTimeout(r, 2000));
        const list = (await apiClient.listSources(notebook.id)) as Array<{
          id: string;
          status: string;
        }>;
        const source = list.find((s) => s.id === sourceId);
        if (source?.status === 'indexed' || source?.status === 'completed') {
          indexed = true;
          break;
        }
        if (source?.status === 'error' || source?.status === 'failed') {
          throw new Error('File processing failed');
        }
      }
      if (!indexed) {
        throw new Error('File is still processing. Try again in a moment.');
      }

      const { normalized_text } = await extractFromSource.mutateAsync(sourceId);
      await submitProblem(normalized_text, 'file', [{ source_id: sourceId, file_name: file.name }]);
    } catch (e: unknown) {
      const apiError = handleApiError(e);
      setError(getUserFriendlyMessage(apiError));
    } finally {
      setExtracting(false);
      setIsSubmitting(false);
    }
  };

  return (
    <section className={styles.psFlowSection}>
      <div className={styles.sectionHeader}>
        <span className={styles.stepBadge}>1</span>
        <h2 className={styles.sectionTitle}>Upload your problem</h2>
      </div>
      <p className={styles.psHint}>
        Paste the question or upload an image / PDF. We will read it and identify the NCERT concepts involved.
      </p>
      <textarea
        className={styles.psTextarea}
        placeholder="Type or paste your problem here…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={6}
        disabled={isSubmitting}
      />
      <div className={styles.psIntakeActions}>
        <button
          type="button"
          className={styles.psSecondaryBtn}
          onClick={() => fileInputRef.current?.click()}
          disabled={isSubmitting}
        >
          <ImagePlus className="w-4 h-4" strokeWidth={1.75} />
          Image / PDF
        </button>
        <button
          type="button"
          className={styles.createBtn}
          onClick={() => void handleTextSubmit()}
          disabled={isSubmitting || text.trim().length < 10}
        >
          {isSubmitting ? (
            <>
              <Loader2 className={`w-4 h-4 ${styles.spinner}`} />
              Analyzing…
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" strokeWidth={1.75} />
              Analyze problem
            </>
          )}
        </button>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
          e.target.value = '';
        }}
      />
      {error ? <p className={styles.psError}>{error}</p> : null}
    </section>
  );
}
