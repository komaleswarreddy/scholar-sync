/**
 * Source Context
 * 
 * Manages selected sources across the application.
 */

'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

interface SourceContextType {
  selectedSources: Set<string>;
  toggleSource: (sourceId: string) => void;
  clearSelection: () => void;
  setSelectedSources: (sources: Set<string>) => void;
}

const SourceContext = createContext<SourceContextType | undefined>(undefined);

export function SourceProvider({ children }: { children: ReactNode }) {
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());

  const toggleSource = (sourceId: string) => {
    setSelectedSources((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sourceId)) {
        newSet.delete(sourceId);
      } else {
        newSet.add(sourceId);
      }
      return newSet;
    });
  };

  const clearSelection = () => {
    setSelectedSources(new Set());
  };

  return (
    <SourceContext.Provider
      value={{
        selectedSources,
        toggleSource,
        clearSelection,
        setSelectedSources,
      }}
    >
      {children}
    </SourceContext.Provider>
  );
}

export function useSourceContext() {
  const context = useContext(SourceContext);
  if (!context) {
    throw new Error('useSourceContext must be used within SourceProvider');
  }
  return context;
}



