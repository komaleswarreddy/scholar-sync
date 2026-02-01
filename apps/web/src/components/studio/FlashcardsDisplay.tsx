/**
 * Flashcards Display Component
 * 
 * Displays flashcards with flip card UI, navigation, and study mode.
 * Supports randomize and mark as known features.
 * Styled to match NotebookLM design system.
 */

'use client';

import { useState, useEffect, useMemo } from 'react';
import { ChevronLeft, ChevronRight, RotateCcw, Shuffle, CheckCircle2, XCircle, BookOpen, Download } from 'lucide-react';
import { Button } from '../ui/Button';
import { Flashcard } from '@repo/types';
import { exportAsJSON, exportFlashcardsAsCSV } from '@/lib/export-utils';

export interface FlashcardsData {
  task_type?: 'flashcards';
  data?: Flashcard[];
}

interface FlashcardsDisplayProps {
  flashcardsData: FlashcardsData | Flashcard[] | string | object;
}

export function FlashcardsDisplay({ flashcardsData }: FlashcardsDisplayProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [studyMode, setStudyMode] = useState(false);
  const [knownCards, setKnownCards] = useState<Set<number>>(new Set());
  const [shuffledIndices, setShuffledIndices] = useState<number[]>([]);

  // Parse flashcards data
  const parseFlashcardsData = (): Flashcard[] | null => {
    try {
      let parsed: any;
      
      if (typeof flashcardsData === 'string') {
        parsed = JSON.parse(flashcardsData);
      } else if (typeof flashcardsData === 'object' && flashcardsData !== null) {
        parsed = flashcardsData;
      } else {
        return null;
      }

      // Handle different response structures
      if (parsed.data && Array.isArray(parsed.data)) {
        // Response structure: { task_type: "flashcards", data: [{ front, back }, ...] }
        return parsed.data;
      } else if (Array.isArray(parsed)) {
        // Direct array: [{ front, back }, ...]
        return parsed;
      }

      return null;
    } catch (error) {
      console.error('Failed to parse flashcards data:', error);
      return null;
    }
  };

  const flashcards = parseFlashcardsData();

  if (!flashcards || flashcards.length === 0) {
    return (
      <div className="p-6">
        <div className="text-center py-8">
          <p className="text-sm text-text-secondary">
            Invalid flashcards data. Please ensure the flashcards are properly formatted.
          </p>
        </div>
      </div>
    );
  }

  // Initialize shuffled indices when study mode is enabled
  useEffect(() => {
    if (studyMode) {
      const indices = flashcards.map((_, i) => i);
      // Fisher-Yates shuffle
      for (let i = indices.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [indices[i], indices[j]] = [indices[j], indices[i]];
      }
      setShuffledIndices(indices);
      setCurrentIndex(0);
      setIsFlipped(false);
    } else {
      setShuffledIndices([]);
      setCurrentIndex(0);
      setIsFlipped(false);
    }
  }, [studyMode, flashcards.length]);

  // Get current flashcard index (accounting for shuffle)
  const getCurrentCardIndex = (): number => {
    if (studyMode && shuffledIndices.length > 0) {
      return shuffledIndices[currentIndex];
    }
    return currentIndex;
  };

  const currentCardIndex = getCurrentCardIndex();
  const currentCard = flashcards[currentCardIndex];
  const totalCards = flashcards.length;
  const currentPosition = currentIndex + 1;
  const knownCount = knownCards.size;
  const remainingCount = totalCards - knownCount;

  // Navigation handlers
  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setIsFlipped(false);
    }
  };

  const handleNext = () => {
    if (currentIndex < (studyMode ? shuffledIndices.length - 1 : totalCards - 1)) {
      setCurrentIndex(currentIndex + 1);
      setIsFlipped(false);
    }
  };

  const handleFlip = () => {
    setIsFlipped(!isFlipped);
  };

  // Study mode handlers
  const handleToggleStudyMode = () => {
    setStudyMode(!studyMode);
    setKnownCards(new Set()); // Reset known cards when toggling study mode
  };

  const handleMarkAsKnown = () => {
    const newKnownCards = new Set(knownCards);
    newKnownCards.add(currentCardIndex);
    setKnownCards(newKnownCards);
    
    // Auto-advance to next card
    if (currentIndex < (studyMode ? shuffledIndices.length - 1 : totalCards - 1)) {
      handleNext();
    } else {
      // If at the end, go to first unknown card
      const nextUnknownIndex = flashcards.findIndex((_, i) => !newKnownCards.has(i));
      if (nextUnknownIndex !== -1) {
        if (studyMode) {
          const shuffledIndex = shuffledIndices.findIndex(idx => idx === nextUnknownIndex);
          if (shuffledIndex !== -1) {
            setCurrentIndex(shuffledIndex);
          }
        } else {
          setCurrentIndex(nextUnknownIndex);
        }
        setIsFlipped(false);
      }
    }
  };

  const handleShuffle = () => {
    if (studyMode) {
      // Re-shuffle the remaining cards
      const remainingIndices = flashcards
        .map((_, i) => i)
        .filter(i => !knownCards.has(i));
      
      // Fisher-Yates shuffle
      for (let i = remainingIndices.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [remainingIndices[i], remainingIndices[j]] = [remainingIndices[j], remainingIndices[i]];
      }
      
      // Add known cards at the end
      const knownIndices = Array.from(knownCards);
      const newShuffled = [...remainingIndices, ...knownIndices];
      setShuffledIndices(newShuffled);
      setCurrentIndex(0);
      setIsFlipped(false);
    }
  };

  const handleReset = () => {
    setCurrentIndex(0);
    setIsFlipped(false);
    setKnownCards(new Set());
    if (studyMode) {
      handleShuffle();
    }
  };

  // Check if current card is known
  const isCurrentCardKnown = knownCards.has(currentCardIndex);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handlePrevious();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleNext();
      } else if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        handleFlip();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex, isFlipped]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-text-primary mb-1">Flashcards</h3>
          <p className="text-sm text-text-secondary">
            {totalCards} {totalCards === 1 ? 'card' : 'cards'}
            {studyMode && knownCount > 0 && (
              <span className="ml-2">
                • {knownCount} known • {remainingCount} remaining
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => exportAsJSON(flashcards, `flashcards-${Date.now()}`)}
            className="flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            JSON
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => exportFlashcardsAsCSV(flashcards, `flashcards-${Date.now()}`)}
            className="flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            CSV
          </Button>
          <Button
            variant={studyMode ? 'primary' : 'secondary'}
            size="sm"
            onClick={handleToggleStudyMode}
          >
            <BookOpen className="w-4 h-4 mr-2" />
            {studyMode ? 'Study Mode' : 'Normal Mode'}
          </Button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-text-secondary font-medium">
            Card {currentPosition} of {studyMode ? shuffledIndices.length : totalCards}
          </span>
          <span className="text-text-tertiary">
            {Math.round((currentPosition / (studyMode ? shuffledIndices.length : totalCards)) * 100)}%
          </span>
        </div>
        <div className="w-full h-2.5 bg-surface-subtle rounded-full overflow-hidden">
          <div
            className="h-full bg-accent-blue rounded-full transition-all duration-300 ease-out"
            style={{ width: `${(currentPosition / (studyMode ? shuffledIndices.length : totalCards)) * 100}%` }}
          />
        </div>
      </div>

      {/* Flashcard */}
      <div className="flex items-center justify-center min-h-[400px]">
        <div
          className="relative w-full max-w-2xl h-[400px]"
          style={{ perspective: '1000px' }}
          onClick={handleFlip}
        >
          {/* Card Container with 3D Flip Effect */}
          <div
            className="relative w-full h-full transition-transform duration-500 cursor-pointer"
            style={{
              transformStyle: 'preserve-3d',
              transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
            }}
          >
            {/* Front of Card */}
            <div
              className="absolute inset-0 rounded-2xl border-2"
              style={{
                backfaceVisibility: 'hidden',
                WebkitBackfaceVisibility: 'hidden',
                transform: 'rotateY(0deg)',
              }}
            >
              <div className="w-full h-full bg-surface border-border-default rounded-2xl p-8 flex flex-col items-center justify-center shadow-lg hover:shadow-xl transition-shadow">
                <div className="text-center space-y-4 w-full">
                  {isCurrentCardKnown && (
                    <div className="flex items-center justify-center mb-4">
                      <CheckCircle2 className="w-5 h-5 text-accent-green" />
                    </div>
                  )}
                  <p className="text-2xl font-bold text-text-primary leading-relaxed">
                    {currentCard.front}
                  </p>
                  <p className="text-sm text-text-secondary mt-6">
                    Click or press Space to flip
                  </p>
                </div>
              </div>
            </div>

            {/* Back of Card */}
            <div
              className="absolute inset-0 rounded-2xl border-2"
              style={{
                backfaceVisibility: 'hidden',
                WebkitBackfaceVisibility: 'hidden',
                transform: 'rotateY(180deg)',
              }}
            >
              <div className="w-full h-full bg-accent-blue/5 border-accent-blue/20 rounded-2xl p-8 flex flex-col items-center justify-center shadow-lg hover:shadow-xl transition-shadow">
                <div className="text-center space-y-4 w-full">
                  {isCurrentCardKnown && (
                    <div className="flex items-center justify-center mb-4">
                      <CheckCircle2 className="w-5 h-5 text-accent-green" />
                    </div>
                  )}
                  <p className="text-2xl font-bold text-text-primary leading-relaxed">
                    {currentCard.back}
                  </p>
                  <p className="text-sm text-text-secondary mt-6">
                    Click or press Space to flip
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="space-y-4">
        {/* Navigation Buttons */}
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="secondary"
            size="md"
            onClick={handlePrevious}
            disabled={currentIndex === 0}
            className="flex items-center gap-2"
          >
            <ChevronLeft className="w-5 h-5" />
            Previous
          </Button>

          <Button
            variant="secondary"
            size="md"
            onClick={handleNext}
            disabled={currentIndex >= (studyMode ? shuffledIndices.length - 1 : totalCards - 1)}
            className="flex items-center gap-2"
          >
            Next
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>

        {/* Study Mode Controls */}
        {studyMode && (
          <div className="flex items-center justify-center gap-3 pt-4 border-t border-border-default">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleShuffle}
              className="flex items-center gap-2"
            >
              <Shuffle className="w-4 h-4" />
              Shuffle
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleMarkAsKnown}
              disabled={isCurrentCardKnown}
              className="flex items-center gap-2"
            >
              <CheckCircle2 className="w-4 h-4" />
              {isCurrentCardKnown ? 'Already Known' : 'Mark as Known'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              className="flex items-center gap-2"
            >
              Reset
            </Button>
          </div>
        )}
      </div>

    </div>
  );
}
