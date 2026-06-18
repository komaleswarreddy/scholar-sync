/** Client-side feature flags (mirror server env where applicable). */
export const isProblemSolverEnabled =
  process.env.NEXT_PUBLIC_ENABLE_PROBLEM_SOLVER === 'true';
