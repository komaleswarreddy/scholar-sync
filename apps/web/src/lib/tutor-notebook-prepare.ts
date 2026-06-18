import { apiClient } from '@/lib/api-client';
import { ErrorType, handleApiError } from '@/lib/error-handler';

import type { TutorBootstrapPayload } from '@/contexts/TutorBootstrapContext';



export type TutorPrepareScope = {

  title: string;

  classNum: number;

  subjectKey: string;

  subjectLabel: string;

  subjectSlug: string;

  subsubject: string | null;

  chapterNo: number;

  chapterTitle: string;

  filterChapterName?: string;

  ncertDocumentId?: string | null;

  chunksCount?: number;

  conceptId: string;

  conceptLabel: string;

};



export type PrepareStepId =

  | 'creating_notebook'

  | 'building_summary'

  | 'generating_assets'

  | 'finalizing';



export type PrepareProgress = {

  step: PrepareStepId;

  stepIndex: number;

  totalSteps: number;

  progress: number;

  elapsedMs: number;

  estimatedRemainingMs: number;

  assetTypes?: string[];

  contextLabel: string;

};



export type PrepareResult = {

  slug: string;

  notebookId: string;

  assetsCreated: number;

  bootstrapPayload: TutorBootstrapPayload;

  timedOut: boolean;

  partialFailure: boolean;

};



export class TutorPrepareFailedError extends Error {

  constructor(

    message = 'Could not prepare your notebook. Please try again.',

    public readonly phase: 'create' | 'bootstrap' | 'prepare' | 'unknown' = 'unknown',

  ) {

    super(message);

    this.name = 'TutorPrepareFailedError';

  }

}



/** @deprecated Use TutorPrepareFailedError */

export class TutorBootstrapFailedError extends TutorPrepareFailedError {

  constructor(message = 'Could not prepare your notebook. Please try again.') {

    super(message, 'bootstrap');

    this.name = 'TutorBootstrapFailedError';

  }

}



/** Total prep budget for unified server-side prepare (must exceed slow cold NCERT fetch). */

export const MAX_WAIT_MS = 180_000;



const STEP_ESTIMATES_MS: Record<PrepareStepId, number> = {

  creating_notebook: 3_000,

  building_summary: 18_000,

  generating_assets: 30_000,

  finalizing: 2_000,

};



const STEP_ORDER: PrepareStepId[] = [

  'creating_notebook',

  'building_summary',

  'generating_assets',

  'finalizing',

];



function buildScopeSettings(scope: TutorPrepareScope) {

  return {

    class_num: scope.classNum,

    subject_key: scope.subjectKey,

    subject_slug: scope.subjectSlug,

    subsubject: scope.subsubject,

    chapter_no: scope.chapterNo,

    chapter_title: scope.chapterTitle,

    chapter_name: scope.chapterTitle,

    filter_chapter_name: scope.filterChapterName ?? scope.chapterTitle.trim().toLowerCase(),

    ncert_document_id: scope.ncertDocumentId ?? null,

    chunks_count: scope.chunksCount,

    concept: scope.conceptId === 'all' ? null : scope.conceptLabel,

  };

}



function buildContextLabel(scope: TutorPrepareScope): string {

  const parts = [

    scope.classNum != null ? `Class ${scope.classNum}` : null,

    scope.subjectLabel,

    scope.chapterNo != null ? `Ch. ${scope.chapterNo} ${scope.chapterTitle}` : null,

    scope.conceptId !== 'all' ? scope.conceptLabel : null,

  ].filter(Boolean);

  return parts.join(' · ');

}



function estimateRemainingMs(currentStep: PrepareStepId, stepStartedMs: number): number {

  const idx = STEP_ORDER.indexOf(currentStep);

  let remaining = Math.max(0, STEP_ESTIMATES_MS[currentStep] - stepStartedMs);

  for (let i = idx + 1; i < STEP_ORDER.length; i += 1) {

    remaining += STEP_ESTIMATES_MS[STEP_ORDER[i]];

  }

  return remaining;

}



function reportProgress(

  onProgress: (progress: PrepareProgress) => void,

  step: PrepareStepId,

  contextLabel: string,

  startedAt: number,

  stepStartedAt: number,

  extras?: Pick<PrepareProgress, 'assetTypes'>,

) {

  const stepIndex = STEP_ORDER.indexOf(step);

  const elapsedMs = Date.now() - startedAt;

  const progress = Math.min(99, Math.round(((stepIndex + 0.35) / STEP_ORDER.length) * 100));

  onProgress({

    step,

    stepIndex,

    totalSteps: STEP_ORDER.length,

    progress,

    elapsedMs,

    estimatedRemainingMs: estimateRemainingMs(step, Date.now() - stepStartedAt),

    contextLabel,

    ...extras,

  });

}



function stepForElapsedMs(elapsedMs: number): PrepareStepId {

  if (elapsedMs < STEP_ESTIMATES_MS.creating_notebook) {

    return 'creating_notebook';

  }

  if (elapsedMs < STEP_ESTIMATES_MS.creating_notebook + STEP_ESTIMATES_MS.building_summary) {

    return 'building_summary';

  }

  if (

    elapsedMs <

    STEP_ESTIMATES_MS.creating_notebook +

      STEP_ESTIMATES_MS.building_summary +

      STEP_ESTIMATES_MS.generating_assets

  ) {

    return 'generating_assets';

  }

  return 'finalizing';

}



function isAbortError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false;
  const code = (error as { code?: string }).code;
  const name = (error as { name?: string }).name;
  return code === 'ERR_CANCELED' || name === 'AbortError' || name === 'CanceledError';
}

function mapPrepareError(error: unknown): TutorPrepareFailedError {
  if (isAbortError(error)) {
    throw error;
  }
  const apiError = handleApiError(error);
  if (apiError.type === ErrorType.UNAUTHORIZED || apiError.type === ErrorType.FORBIDDEN) {
    return new TutorPrepareFailedError(
      'Your session expired. Please sign in again and retry.',
      'prepare',
    );
  }
  if (apiError.type === ErrorType.TIMEOUT) {
    return new TutorPrepareFailedError(
      'Preparation is taking longer than expected. Please try again.',
      'prepare',
    );
  }
  if (apiError.type === ErrorType.NETWORK) {
    return new TutorPrepareFailedError(
      'Network connection was interrupted. Please check your connection and try again.',
      'prepare',
    );
  }
  if (apiError.statusCode && apiError.statusCode >= 500) {
    return new TutorPrepareFailedError(
      'Our servers had trouble preparing this notebook. Please try again in a moment.',
      'prepare',
    );
  }
  return new TutorPrepareFailedError(
    apiError.message || 'Could not prepare your notebook. Please try again.',
    'prepare',
  );
}

export async function prepareTutorNotebook(

  scope: TutorPrepareScope,

  onProgress: (progress: PrepareProgress) => void,

  options?: { signal?: AbortSignal },

): Promise<PrepareResult> {

  const startedAt = Date.now();

  const contextLabel = buildContextLabel(scope);

  let stepStartedAt = startedAt;

  let timedOut = false;



  reportProgress(onProgress, 'creating_notebook', contextLabel, startedAt, stepStartedAt);



  const progressTicker = window.setInterval(() => {

    const elapsedMs = Date.now() - startedAt;

    const step = stepForElapsedMs(elapsedMs);

    if (step !== 'creating_notebook') {

      stepStartedAt = startedAt + STEP_ESTIMATES_MS.creating_notebook;

    }

    reportProgress(onProgress, step, contextLabel, startedAt, stepStartedAt);

  }, 900);



  let response: Awaited<ReturnType<typeof apiClient.prepareTutorNotebook>>;

  try {

    response = await apiClient.prepareTutorNotebook(

      {

        title: scope.title,

        class_level: `Class ${scope.classNum}`,

        subject: scope.subjectLabel,

        focus: scope.title,

        tutor_scope: buildScopeSettings(scope),

      },

      { timeoutMs: MAX_WAIT_MS, signal: options?.signal },

    );

  } catch (error) {

    window.clearInterval(progressTicker);

    if (isAbortError(error)) {
      throw error;
    }

    console.warn('[TutorPrepare] unified prepare failed:', error);

    throw mapPrepareError(error);

  } finally {

    window.clearInterval(progressTicker);

  }



  const elapsedMs = Date.now() - startedAt;

  if (elapsedMs >= MAX_WAIT_MS) {

    timedOut = true;

  }



  const bootstrapPayload: TutorBootstrapPayload = {

    opening_summary: response.opening_summary,

    suggestions: response.suggestions,

    studio_recommendations: response.studio_recommendations,

    chat_id: response.chat_id ?? undefined,

  };



  stepStartedAt = Date.now();

  reportProgress(onProgress, 'finalizing', contextLabel, startedAt, stepStartedAt, {

    assetTypes: response.auto_types,

  });



  onProgress({

    step: 'finalizing',

    stepIndex: STEP_ORDER.length - 1,

    totalSteps: STEP_ORDER.length,

    progress: 100,

    elapsedMs: Date.now() - startedAt,

    estimatedRemainingMs: 0,

    contextLabel,

    assetTypes: response.auto_types,

  });



  return {

    slug: response.slug,

    notebookId: response.notebook_id,

    assetsCreated: response.assets_created,

    bootstrapPayload,

    timedOut,

    partialFailure: response.partial_failure || response.assets_created < 2,

  };

}



export function shouldEnterNotebookAfterPrepare(result: PrepareResult, elapsedMs: number): boolean {

  return result.assetsCreated >= 1 || elapsedMs >= MAX_WAIT_MS;

}



export const PREPARE_STEP_LABELS: Record<

  PrepareStepId,

  { label: string; estimate?: string }

> = {

  creating_notebook: { label: 'Creating notebook', estimate: '~3s' },

  building_summary: { label: 'Building chapter summary & suggestions', estimate: '~18s' },

  generating_assets: { label: 'Generating 2 study assets in parallel', estimate: '~30s' },

  finalizing: { label: 'Finalizing', estimate: '~2s' },

};



export function formatAssetStepLabel(step: PrepareStepId, assetTypes?: string[]): string {

  if (step === 'generating_assets' && assetTypes?.length) {

    const pretty = assetTypes

      .map((t) => t.replace(/_/g, ' '))

      .join(' & ');

    return `${PREPARE_STEP_LABELS[step].label} (${pretty})`;

  }

  return PREPARE_STEP_LABELS[step].label;

}



/** Fire-and-forget NCERT context warm when user selects a chapter. */

export function warmTutorNcertContext(scope: TutorPrepareScope): void {

  void apiClient.warmTutorNcertContext(buildScopeSettings(scope)).catch((error) => {

    console.debug('[TutorPrepare] NCERT warm skipped:', error);

  });

}



/** @deprecated Unified prepare handles studio assets server-side. */

export async function generateAndPersistStudioAsset(): Promise<boolean> {

  return false;

}

