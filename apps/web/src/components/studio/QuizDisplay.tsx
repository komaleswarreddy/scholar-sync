/**
 * Quiz Display Component
 * 
 * Displays quiz questions with multiple choice options.
 * Supports "Take Quiz" mode (hide answers) and "Review Answers" mode (show all).
 * Styled to match NotebookLM design system.
 */

'use client';

import { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, ChevronDown, ChevronUp, BookOpen, Trophy } from 'lucide-react';
import { Button } from '../ui/Button';

export interface QuizQuestion {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

export interface QuizData {
  title?: string;
  questions: QuizQuestion[];
}

interface QuizDisplayProps {
  quizData: QuizData | string | object;
}

export function QuizDisplay({ quizData }: QuizDisplayProps) {
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({});
  const [expandedQuestions, setExpandedQuestions] = useState<Set<number>>(new Set());
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [score, setScore] = useState<number | null>(null);

  // Parse quiz data
  const parseQuizData = (): QuizData | null => {
    try {
      let parsed: any;
      
      if (typeof quizData === 'string') {
        parsed = JSON.parse(quizData);
      } else if (typeof quizData === 'object' && quizData !== null) {
        parsed = quizData;
      } else {
        return null;
      }

      // Handle different response structures
      if (parsed.data) {
        // Response structure: { task_type: "quiz", data: { title, questions } }
        return parsed.data;
      } else if (parsed.questions) {
        // Direct structure: { title, questions }
        return parsed;
      } else if (Array.isArray(parsed)) {
        // Array of questions
        return { questions: parsed };
      }

      return null;
    } catch (error) {
      console.error('Failed to parse quiz data:', error);
      return null;
    }
  };

  const quiz = parseQuizData();

  if (!quiz || !quiz.questions || quiz.questions.length === 0) {
    return (
      <div className="p-6">
        <div className="text-center py-8">
          <p className="text-sm text-text-secondary">
            Invalid quiz data. Please ensure the quiz is properly formatted.
          </p>
        </div>
      </div>
    );
  }

  const { title, questions } = quiz;

  // Expand all questions when submitted
  useEffect(() => {
    if (isSubmitted) {
      setExpandedQuestions(new Set(questions.map((_, i) => i)));
    }
  }, [isSubmitted, questions.length]);

  // Calculate score
  const calculateScore = (): number => {
    let correct = 0;
    questions.forEach((question, index) => {
      if (selectedAnswers[index] === question.correct_answer) {
        correct++;
      }
    });
    return correct;
  };

  // Toggle question expansion
  const toggleQuestion = (index: number) => {
    if (isSubmitted) return; // Don't allow collapsing after submission
    const newExpanded = new Set(expandedQuestions);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedQuestions(newExpanded);
  };

  // Handle answer selection
  const handleSelectAnswer = (questionIndex: number, option: string) => {
    if (!isSubmitted) {
      setSelectedAnswers((prev) => ({
        ...prev,
        [questionIndex]: option,
      }));
    }
  };

  // Handle quiz submission
  const handleSubmit = () => {
    const calculatedScore = calculateScore();
    setScore(calculatedScore);
    setIsSubmitted(true);
    // Expand all questions to show results
    setExpandedQuestions(new Set(questions.map((_, i) => i)));
  };

  // Reset quiz
  const handleReset = () => {
    setSelectedAnswers({});
    setIsSubmitted(false);
    setScore(null);
    setExpandedQuestions(new Set());
  };

  // Check if answer is correct
  const isCorrect = (questionIndex: number, option: string): boolean => {
    return questions[questionIndex].correct_answer === option;
  };

  // Check if answer is selected
  const isSelected = (questionIndex: number, option: string): boolean => {
    return selectedAnswers[questionIndex] === option;
  };

  // Check if user's answer is correct
  const isUserAnswerCorrect = (questionIndex: number): boolean => {
    return selectedAnswers[questionIndex] === questions[questionIndex].correct_answer;
  };

  // Get answer status for display
  const getAnswerStatus = (questionIndex: number, option: string) => {
    if (!isSubmitted) {
      // Before submission, only show selected state
      if (isSelected(questionIndex, option)) {
        return 'selected';
      }
      return 'default';
    }

    // After submission - show correct/incorrect
    const correct = isCorrect(questionIndex, option);
    const selected = isSelected(questionIndex, option);

    if (correct) {
      return 'correct';
    }
    if (selected && !correct) {
      return 'incorrect';
    }

    return 'default';
  };

  // Get score percentage
  const scorePercentage = score !== null ? Math.round((score / questions.length) * 100) : 0;

  // Calculate progress
  const answeredCount = Object.keys(selectedAnswers).length;
  const progressPercentage = (answeredCount / questions.length) * 100;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          {title && (
            <h3 className="text-xl font-bold text-text-primary mb-1">{title}</h3>
          )}
          <p className="text-sm text-text-secondary">
            {questions.length} {questions.length === 1 ? 'question' : 'questions'}
          </p>
        </div>
      </div>

      {/* Progress Bar - Only show before submission */}
      {!isSubmitted && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-text-secondary font-medium">
              Progress: {answeredCount} / {questions.length} questions answered
            </span>
            <span className="text-text-tertiary">
              {Math.round(progressPercentage)}%
            </span>
          </div>
          <div className="w-full h-2.5 bg-surface-subtle rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-blue rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Score Display - After Submission */}
      {isSubmitted && score !== null && (
        <div className="bg-surface-subtle border border-border-default rounded-xl p-6">
          <div className="flex items-center justify-center gap-4 mb-4">
            <Trophy className="w-8 h-8 text-accent-blue" />
            <div className="text-center">
              <p className="text-3xl font-bold text-text-primary">
                {score} / {questions.length}
              </p>
              <p className="text-lg font-semibold text-text-secondary mt-1">
                {scorePercentage}% Correct
              </p>
            </div>
          </div>
          <div className="flex justify-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleReset}
            >
              Retake Quiz
            </Button>
          </div>
        </div>
      )}

      {/* Questions */}
      <div className="space-y-4">
        {questions.map((question, questionIndex) => {
          const isExpanded = expandedQuestions.has(questionIndex) || isSubmitted;
          const selectedAnswer = selectedAnswers[questionIndex];
          const userCorrect = isUserAnswerCorrect(questionIndex);

          return (
            <div
              key={questionIndex}
              className="bg-surface border border-border-default rounded-xl overflow-hidden transition-all"
            >
              {/* Question Header */}
              <div
                className={`p-4 ${!isSubmitted ? 'cursor-pointer hover:bg-surface-hover transition-colors' : ''}`}
                onClick={() => !isSubmitted && toggleQuestion(questionIndex)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-accent-blue/10 text-accent-blue text-xs font-semibold flex items-center justify-center mt-0.5">
                        {questionIndex + 1}
                      </span>
                      <div className="flex-1">
                        <p className="text-base font-semibold text-text-primary leading-relaxed">
                          {question.question}
                        </p>
                        {/* Show result indicator after submission */}
                        {isSubmitted && (
                          <div className="flex items-center gap-2 mt-2">
                            {userCorrect ? (
                              <span className="text-xs font-semibold text-accent-green flex items-center gap-1">
                                <CheckCircle2 className="w-4 h-4" />
                                Correct
                              </span>
                            ) : (
                              <span className="text-xs font-semibold text-red-500 flex items-center gap-1">
                                <XCircle className="w-4 h-4" />
                                Incorrect
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  {!isSubmitted && (
                    <button className="flex-shrink-0 text-text-secondary hover:text-text-primary transition-colors">
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5" />
                      ) : (
                        <ChevronDown className="w-5 h-5" />
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Question Content */}
              {isExpanded && (
                <div className="px-4 pb-4 space-y-4 border-t border-border-default pt-4">
                  {/* Options */}
                  <div className="space-y-2">
                    {question.options.map((option, optionIndex) => {
                      const status = getAnswerStatus(questionIndex, option);
                      const isOptionSelected = isSelected(questionIndex, option);
                      const isOptionCorrect = isCorrect(questionIndex, option);

                      return (
                        <button
                          key={optionIndex}
                          onClick={() => handleSelectAnswer(questionIndex, option)}
                          disabled={isSubmitted}
                          className={`
                            w-full text-left p-3 rounded-lg border-2 transition-all
                            ${
                              status === 'correct'
                                ? 'bg-accent-green/10 border-accent-green text-text-primary'
                                : status === 'incorrect'
                                ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700 text-text-primary'
                                : status === 'selected'
                                ? 'bg-accent-blue/10 border-accent-blue text-text-primary'
                                : 'bg-surface-subtle border-border-default text-text-primary hover:bg-surface-hover hover:border-border-active'
                            }
                            ${isSubmitted ? 'cursor-default' : 'cursor-pointer'}
                            ${!isSubmitted ? 'hover:scale-[1.01]' : ''}
                          `}
                        >
                          <div className="flex items-start gap-3">
                            {/* Option Indicator */}
                            <div
                              className={`
                                flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-semibold mt-0.5
                                ${
                                  status === 'correct'
                                    ? 'bg-accent-green border-accent-green text-background'
                                    : status === 'incorrect'
                                    ? 'bg-red-500 border-red-500 text-background'
                                    : status === 'selected'
                                    ? 'bg-accent-blue border-accent-blue text-background'
                                    : 'bg-surface border-border-default text-text-secondary'
                                }
                              `}
                            >
                              {String.fromCharCode(65 + optionIndex)}
                            </div>

                            {/* Option Text */}
                            <div className="flex-1">
                              <p className="text-sm leading-relaxed">{option}</p>
                            </div>

                            {/* Status Icons - Show after submission */}
                            {isSubmitted && (
                              <div className="flex-shrink-0">
                                {isOptionCorrect ? (
                                  <CheckCircle2 className="w-5 h-5 text-accent-green" />
                                ) : isOptionSelected && !isOptionCorrect ? (
                                  <XCircle className="w-5 h-5 text-red-500" />
                                ) : null}
                              </div>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {/* Explanation - Show after submission */}
                  {isSubmitted && question.explanation && (
                    <div className="pt-3 border-t border-border-default">
                      <div className="flex items-start gap-2">
                        <BookOpen className="w-4 h-4 text-accent-blue mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                          <p className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-1">
                            Explanation
                          </p>
                          <p className="text-sm text-text-primary leading-relaxed">
                            {question.explanation}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Submit Button - Only show before submission */}
      {!isSubmitted && (
        <div className="pt-4 border-t border-border-default">
          <div className="flex flex-col items-center gap-4">
            <Button
              variant="primary"
              size="lg"
              onClick={handleSubmit}
              disabled={Object.keys(selectedAnswers).length === 0}
              className="w-full max-w-md"
            >
              Submit Quiz
            </Button>
            {Object.keys(selectedAnswers).length > 0 && (
              <p className="text-sm text-text-secondary text-center">
                {Object.keys(selectedAnswers).length} of {questions.length} questions answered
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
