/**
 * Studio Suite Component
 * 
 * Right sidebar top section with Studio generation tools.
 * Uses placeholder functionality until API keys are added.
 */

'use client';

import { useState } from 'react';
import { 
  FileQuestion, 
  Layers, 
  Network, 
  FileText, 
  Presentation, 
  Image as ImageIcon
} from 'lucide-react';
import { StudioCard } from './StudioCard';
import { useApi } from '@/hooks/useApi';
import { useSourceContext } from '@/contexts/SourceContext';

const STUDIO_TOOLS = [
  { icon: <Network className="w-5 h-5" />, title: 'Mind Map', type: 'mind_map' },
  { icon: <FileText className="w-5 h-5" />, title: 'Reports', type: 'reports' },
  { icon: <Layers className="w-5 h-5" />, title: 'Flashcards', type: 'flashcards' },
  { icon: <FileQuestion className="w-5 h-5" />, title: 'Quiz', type: 'quiz' },
  { icon: <ImageIcon className="w-5 h-5" />, title: 'Infographic', type: 'infographic' },
  { icon: <Presentation className="w-5 h-5" />, title: 'Slide Deck', type: 'slide_deck' },
];

export function StudioSuite() {
  const { loading, error, handleRequest, apiClient } = useApi();
  const { selectedSources } = useSourceContext();
  const [generating, setGenerating] = useState<string | null>(null);

  const handleGenerate = async (type: string) => {
    const sourceIds = Array.from(selectedSources);
    
    if (sourceIds.length === 0) {
      alert('Please select at least one source to generate content');
      return;
    }
    
    setGenerating(type);
    try {
      
      const result = await handleRequest(() =>
        apiClient.generateStudio(type as any, sourceIds)
      );
      
      if (result) {
        // TODO: Display the generated content in a modal or new view
        alert(`${type} generated successfully! Check the console for details.`);
        console.log('Generated content:', result);
      }
    } catch (err) {
      console.error('Generation error:', err);
    } finally {
      setGenerating(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border-default">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-text-secondary" />
          <h2 className="text-lg font-medium text-text-primary">Studio</h2>
        </div>
      </div>

      {/* Studio Grid */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="grid grid-cols-2 gap-3">
          {STUDIO_TOOLS.map((tool) => (
            <StudioCard
              key={tool.type}
              icon={tool.icon}
              title={tool.title}
              onClick={() => handleGenerate(tool.type)}
            />
          ))}
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-border-default">
        <p className="text-xs text-text-tertiary text-center">
          Select sources to generate content
        </p>
      </div>
    </div>
  );
}

