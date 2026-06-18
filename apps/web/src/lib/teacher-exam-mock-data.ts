import type {
  ConceptOption,
  ExamQuestion,
  OmrStudentRow,
  TeacherExam,
} from './teacher-exam-types';

export const EXAM_BOARDS = ['NCERT', 'Telangana State Board', 'ICSE', 'IB'] as const;

export const EXAM_CLASSES = [9, 10, 11, 12] as const;

export const EXAM_SUBJECTS_BY_CLASS: Record<number, string[]> = {
  9: ['Physics', 'Chemistry', 'Mathematics', 'Biology'],
  10: ['Physics', 'Chemistry', 'Mathematics', 'Biology'],
  11: ['Physics', 'Chemistry', 'Mathematics', 'Biology'],
  12: ['Physics', 'Chemistry', 'Mathematics', 'Biology'],
};

export const CONCEPT_CATALOG: ConceptOption[] = [
  { id: 'c-n1', title: "Newton's First Law", path: "Physics > Motion > Newton's Laws" },
  { id: 'c-n2', title: "Newton's Second Law", path: "Physics > Motion > Newton's Laws" },
  { id: 'c-n3', title: "Newton's Third Law", path: "Physics > Motion > Newton's Laws" },
  { id: 'c-kin', title: 'Kinematics Equations', path: 'Physics > Motion > Kinematics' },
  { id: 'c-mom', title: 'Momentum Conservation', path: 'Physics > Motion > Momentum' },
  { id: 'c-pe', title: 'Potential Energy', path: 'Physics > Work & Energy > Energy' },
  { id: 'c-ke', title: 'Kinetic Energy', path: 'Physics > Work & Energy > Energy' },
  { id: 'c-ph', title: 'pH Scale', path: 'Chemistry > Acids & Bases > pH' },
  { id: 'c-acid', title: 'Acids & Bases', path: 'Chemistry > Acids & Bases' },
  { id: 'c-trig', title: 'Trigonometric Identities', path: 'Mathematics > Trigonometry' },
];

const QUESTION_PREVIEWS = [
  'A hypothetical object moves with constant velocity. Which of the following statements must be true according to classical mechanics?',
  'A block slides down a frictionless incline. What is the acceleration of the block in terms of g and θ?',
  'Two forces act on a body. If the net force is zero, which law of motion applies?',
  'A car accelerates uniformly from rest. After 5 seconds its velocity is 20 m/s. Find the acceleration.',
  'An object in circular motion at constant speed still has acceleration because…',
  'A 2 kg mass experiences a net force of 10 N. What is its acceleration?',
  'Action and reaction forces always occur in pairs according to which principle?',
  'A ball thrown upward reaches maximum height when its velocity becomes zero. At that instant…',
  'Work done by a constant force depends on which of the following quantities?',
  'Gravitational potential energy near Earth\'s surface is given by which expression?',
  'A spring stores elastic potential energy when compressed. This energy is converted to…',
  'Conservation of mechanical energy applies when which condition is satisfied?',
  'Power is defined as the rate of doing work. Its SI unit is…',
  'Impulse is equal to the change in which quantity?',
  'A collision in which kinetic energy is conserved is called…',
  'The center of mass of a system moves as if all external forces act on it. This describes…',
  'Torque depends on force, lever arm, and the angle between them. Maximum torque occurs when…',
  'Angular momentum is conserved when net external torque on a system is…',
  'Simple harmonic motion is characterized by acceleration proportional to…',
  'The period of a simple pendulum depends on length and gravitational acceleration. It does not depend on…',
];

export function buildMockQuestions(): ExamQuestion[] {
  return QUESTION_PREVIEWS.map((preview, index) => {
    const concept = CONCEPT_CATALOG[index % CONCEPT_CATALOG.length];
    const autoPath = concept.path;
    const approvedId = index === 3 ? null : concept.id;
    let mappingStatus: ExamQuestion['mappingStatus'] = 'auto_mapped';
    if (index === 0) mappingStatus = 'edited';
    if (index === 3) mappingStatus = 'needs_review';

    return {
      id: `q-${index + 1}`,
      number: index + 1,
      preview,
      autoDetectedPath: autoPath,
      approvedConceptId: approvedId,
      mappingStatus,
    };
  });
}

const STUDENT_NAMES = [
  'Aarav Mehta', 'Priya Sharma', 'Rohan Gupta', 'Ananya Iyer', 'Kabir Singh',
  'Sara N.', 'Karthik R.', 'Neha Patel', 'Arjun Desai', 'Isha Verma',
  'Vikram Joshi', 'Meera Krishnan', 'Aditya Rao', 'Diya Menon', 'Rahul Nair',
  'Sneha Reddy', 'Aman Kapoor', 'Pooja Bhat', 'Harsh Malhotra', 'Kavya Pillai',
  'Nikhil Shah', 'Riya Choudhury', 'Dev Agarwal', 'Tara Bose', 'Yash Khanna',
  'Lakshmi S.', 'Manual Tagged Student', 'Extra Student',
];

export function buildMockOmrRows(): OmrStudentRow[] {
  const rows: OmrStudentRow[] = [];

  for (let i = 0; i < 28; i++) {
    const roll = i + 1;
    const name = STUDENT_NAMES[i] ?? `Student ${roll}`;

    if (i === 24) {
      rows.push({
        id: `omr-${roll}`,
        rollNumber: null,
        name: 'Unknown student',
        displayLabel: 'Unknown student',
        status: 'unknown_likely',
        message: 'Roll number unclear. Likely Roll 35 (Karthik R.)',
        likelyRoll: 35,
        likelyName: 'Karthik R.',
      });
      continue;
    }

    if (i === 25) {
      rows.push({
        id: `omr-${roll}`,
        rollNumber: 22,
        name: 'Sara N.',
        displayLabel: 'Roll 22 - Sara N.',
        status: 'multiple_marks',
        message: '2 questions had multiple marks (Q7, Q14). Defaulting to unanswered.',
        questionsRead: '20 of 20 questions read',
      });
      continue;
    }

    if (i === 26) {
      rows.push({
        id: `omr-${roll}`,
        rollNumber: null,
        name: 'Unknown student',
        displayLabel: 'Unknown student',
        status: 'unmatched',
        message: 'Could not read roll number.',
      });
      continue;
    }

    if (i === 27) {
      rows.push({
        id: `omr-${roll}`,
        rollNumber: 12,
        name: 'Manual Tagged Student',
        displayLabel: 'Roll 12 - Manual Tagged Student',
        status: 'tagged_manual',
        message: 'Tagged manually',
        questionsRead: '20 of 20 questions read',
      });
      continue;
    }

    rows.push({
      id: `omr-${roll}`,
      rollNumber: roll,
      name,
      displayLabel: `Roll ${roll} - ${name}`,
      status: 'matched',
      message: '20 of 20 questions read',
      questionsRead: '20 of 20 questions read',
    });
  }

  return rows;
}

export const SEED_TEACHER_EXAMS: TeacherExam[] = [
  {
    id: 'exam-draft-1',
    status: 'draft',
    createdAt: '2026-06-01T10:00:00.000Z',
    updatedAt: '2026-06-03T14:00:00.000Z',
    board: 'NCERT',
    classNum: 10,
    subject: 'Chemistry',
    section: 'A',
    examName: 'sdf',
    examDate: '2026-07-08',
    marksCorrect: 1,
    marksWrong: 0,
    marksUnanswered: 0,
    wizardStep: 3,
    questionPaperUploaded: true,
    questionPaperFileName: 'chemistry-midterm.pdf',
    questions: buildMockQuestions(),
    answerKeyMode: 'manual',
    answerKeyUploaded: false,
    answers: {},
    omrUploaded: false,
    omrRows: [],
  },
  {
    id: 'exam-graded-1',
    status: 'graded',
    createdAt: '2026-05-15T09:00:00.000Z',
    updatedAt: '2026-05-20T16:00:00.000Z',
    board: 'NCERT',
    classNum: 10,
    subject: 'Physics',
    section: 'B',
    examName: 'Term 2 Unit Test',
    examDate: '2026-05-18',
    marksCorrect: 1,
    marksWrong: 0,
    marksUnanswered: 0,
    wizardStep: 6,
    questionPaperUploaded: true,
    questionPaperFileName: 'physics-unit-test.pdf',
    questions: buildMockQuestions(),
    answerKeyMode: 'manual',
    answerKeyUploaded: true,
    answers: Object.fromEntries(
      buildMockQuestions().map((q, i) => [q.id, ['A', 'B', 'C', 'D'][i % 4] as 'A' | 'B' | 'C' | 'D']),
    ),
    omrUploaded: true,
    omrFileCount: 28,
    omrRows: buildMockOmrRows(),
    gradingSummary: {
      studentsGraded: 28,
      averageScore: 14.2,
      maxScore: 20,
      weakConcepts: 3,
    },
  },
  {
    id: 'exam-archived-1',
    status: 'archived',
    createdAt: '2026-03-01T09:00:00.000Z',
    updatedAt: '2026-03-10T12:00:00.000Z',
    archivedAt: '2026-04-01T10:00:00.000Z',
    board: 'NCERT',
    classNum: 9,
    subject: 'Mathematics',
    section: 'A',
    examName: 'Annual Exam 2025',
    examDate: '2026-03-05',
    marksCorrect: 1,
    marksWrong: 0.25,
    marksUnanswered: 0,
    wizardStep: 6,
    questionPaperUploaded: true,
    questions: buildMockQuestions(),
    answerKeyMode: 'upload',
    answerKeyUploaded: true,
    answers: {},
    omrUploaded: true,
    omrFileCount: 32,
    omrRows: buildMockOmrRows(),
    gradingSummary: {
      studentsGraded: 32,
      averageScore: 12.8,
      maxScore: 20,
      weakConcepts: 5,
    },
  },
];

export function createEmptyDraft(): import('./teacher-exam-types').ExamWizardDraft {
  return {
    examId: null,
    step: 1,
    board: 'NCERT',
    classNum: null,
    subject: '',
    section: '',
    examName: '',
    examDate: '',
    marksCorrect: 1,
    marksWrong: 0,
    marksUnanswered: 0,
    questionPaperUploaded: false,
    questions: [],
    answerKeyMode: 'upload',
    answerKeyUploaded: false,
    answers: {},
    omrUploaded: false,
    omrRows: [],
  };
}

export function getConceptById(id: string | null): ConceptOption | undefined {
  if (!id) return undefined;
  return CONCEPT_CATALOG.find((c) => c.id === id);
}
