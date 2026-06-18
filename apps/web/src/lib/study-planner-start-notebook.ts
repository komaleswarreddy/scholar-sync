import type { StudyModule } from './study-planner-types';
import type { TutorPrepareScope } from './tutor-notebook-prepare';

export function studyModuleToPrepareScope(
  module: StudyModule,
  classNum: number,
): TutorPrepareScope {
  const title = `Ch. ${module.chapterNo} · ${module.chapterTitle}`;
  return {
    title,
    classNum,
    subjectKey: module.subjectKey,
    subjectLabel: module.subject,
    subjectSlug: module.subjectKey,
    subsubject: null,
    chapterNo: module.chapterNo,
    chapterTitle: module.chapterTitle,
    filterChapterName: module.chapterTitle.trim().toLowerCase(),
    ncertDocumentId: null,
    conceptId: 'all',
    conceptLabel: 'All concepts',
  };
}
