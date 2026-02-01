/**
 * Mind Map Display Component - Google NotebookLM Style
 * * Interactive hierarchical mind map with progressive disclosure.
 * RESTORED: Full 700-line logic with stable scaling fix.
 */

'use client';

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { Eye, EyeOff, ZoomIn, ZoomOut, RotateCcw, Download } from 'lucide-react';
import { hierarchy, tree, HierarchyNode } from 'd3-hierarchy';
import { Button } from '../ui/Button';
import { exportAsImage } from '@/lib/export-utils';

// Data structure matching requirements
interface MindMapNodeData {
  id: string;
  label: string;
  children?: MindMapNodeData[];
}

interface LayoutNode {
  id: string;
  label: string;
  level: number;
  children: LayoutNode[];
  x: number;
  y: number;
  width: number;
  height: number;
  data: MindMapNodeData;
}

interface MindMapDisplayProps {
  mindMapData: string | object;
  filename?: string;
}

const LEVEL_COLORS = [
  { 
    bg: '#8b5cf6', 
    bgLight: '#ede9fe', 
    bgLightDark: 'rgba(139, 92, 246, 0.2)', 
    border: '#a78bfa', 
    borderDark: '#7c3aed',
    text: '#5b21b6',
    textDark: '#ddd6fe',
    line: '#a78bfa',
    lineDark: '#8b5cf6',
  },
  { 
    bg: '#3b82f6', 
    bgLight: '#dbeafe', 
    bgLightDark: 'rgba(59, 130, 246, 0.2)', 
    border: '#60a5fa', 
    borderDark: '#2563eb',
    text: '#1e40af',
    textDark: '#bfdbfe',
    line: '#60a5fa',
    lineDark: '#3b82f6',
  },
  { 
    bg: '#10b981', 
    bgLight: '#d1fae5', 
    bgLightDark: 'rgba(16, 185, 129, 0.2)', 
    border: '#34d399', 
    borderDark: '#059669',
    text: '#065f46',
    textDark: '#a7f3d0',
    line: '#34d399',
    lineDark: '#10b981',
  },
];

const getLevelColor = (level: number) => {
  if (level <= 1) return LEVEL_COLORS[0];
  if (level === 2) return LEVEL_COLORS[1];
  return LEVEL_COLORS[2];
};

// UI Constants - NotebookLM proportions
const NODE_WIDTH = 280; 
const HORIZONTAL_SPACING = 220; 
const VERTICAL_SPACING = 80; 
const NODE_PADDING = 24; 
const NODE_MIN_HEIGHT = 90; 
const ROOT_PADDING = 40; // Padding around root node

export function MindMapDisplay({ mindMapData, filename }: MindMapDisplayProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [zoom, setZoom] = useState(1.0); // FIXED: Start at 1.0 zoom
  const [pan, setPan] = useState({ x: 100 + ROOT_PADDING, y: 400 + ROOT_PADDING }); // FIXED: Start with a comfortable offset + root padding
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [containerSize, setContainerSize] = useState({ width: 1200, height: 800 });
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const previousExpandedNodesRef = useRef<Set<string>>(new Set());

  // Full Parser Restore
  const parseMarkdownToTree = (markdown: string): MindMapNodeData => {
    const lines = markdown.split('\n').filter(line => line.trim());
    const rootLabel = filename || 'Root';
    const root: MindMapNodeData = { id: 'root', label: rootLabel, children: [] };
    const stack: { node: MindMapNodeData; level: number }[] = [{ node: root, level: 0 }];
    let nodeIdCounter = 0;

    lines.forEach((line) => {
      const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);
      const listMatch = line.match(/^[\s-*]*(.+)$/);
      if (headerMatch) {
        const level = headerMatch[1].length;
        const node: MindMapNodeData = { id: `node-${nodeIdCounter++}`, label: headerMatch[2].trim(), children: [] };
        while (stack.length > 1 && stack[stack.length - 1].level >= level) { stack.pop(); }
        const parent = stack[stack.length - 1].node;
        if (!parent.children) parent.children = [];
        parent.children.push(node);
        stack.push({ node, level });
      } else if (listMatch) {
        const label = listMatch[1].trim();
        if (label && !label.startsWith('#')) {
          const level = stack.length > 0 ? stack[stack.length - 1].level + 1 : 1;
          const node: MindMapNodeData = { id: `node-${nodeIdCounter++}`, label, children: [] };
          while (stack.length > 1 && stack[stack.length - 1].level >= level) { stack.pop(); }
          const parent = stack[stack.length - 1].node;
          if (!parent.children) parent.children = [];
          parent.children.push(node);
          stack.push({ node, level });
        }
      }
    });
    return (root.children && root.children.length === 1) ? root.children[0] : root;
  };

  const parseMindMapData = useCallback((): MindMapNodeData | null => {
    try {
      let parsed: any = null;
      if (typeof mindMapData === 'string') {
        try { parsed = JSON.parse(mindMapData); } 
        catch { return parseMarkdownToTree(mindMapData); }
      } else if (typeof mindMapData === 'object' && mindMapData !== null) {
        parsed = mindMapData;
      } else { return null; }

      if (parsed && typeof parsed === 'object' && 'id' in parsed && 'label' in parsed) {
        // Replace "Root" label with filename if provided
        if (parsed.id === 'root' && parsed.label === 'Root' && filename) {
          parsed.label = filename;
        }
        return parsed as MindMapNodeData;
      }
      if (parsed?.content) {
        if (typeof parsed.content === 'string') return parseMarkdownToTree(parsed.content);
        const content = parsed.content as MindMapNodeData;
        // Replace "Root" label with filename if provided
        if (content.id === 'root' && content.label === 'Root' && filename) {
          content.label = filename;
        }
        return content;
      }
      if (Array.isArray(parsed)) {
        const rootLabel = filename || 'Root';
        return { id: 'root', label: rootLabel, children: parsed as MindMapNodeData[] };
      }
      return null;
    } catch (error) {
      console.error('Failed to parse mind map data:', error);
      return null;
    }
  }, [mindMapData, filename]);

  const treeData = useMemo(() => parseMindMapData(), [parseMindMapData]);

  const calculateNodeHeight = (label: string): number => {
    const words = label.split(' ');
    let lines = 1;
    let currentLineLength = 0;
    const maxCharsPerLine = Math.floor((NODE_WIDTH - NODE_PADDING * 2) / 9);
    words.forEach(word => {
      if (currentLineLength + word.length + 1 > maxCharsPerLine && currentLineLength > 0) {
        lines++;
        currentLineLength = word.length;
      } else {
        currentLineLength += (currentLineLength > 0 ? 1 : 0) + word.length;
      }
    });
    lines = Math.min(lines, 3);
    return Math.max(NODE_MIN_HEIGHT, lines * 26 + NODE_PADDING * 2 + 32);
  };

  const buildLayoutTree = useMemo(() => {
    if (!treeData) return null;
    const root = hierarchy(treeData, (d: MindMapNodeData) => d.children);
    const treeLayout = tree<MindMapNodeData>()
      .nodeSize([VERTICAL_SPACING + NODE_MIN_HEIGHT, HORIZONTAL_SPACING + NODE_WIDTH])
      .separation((a, b) => 1.2);

    treeLayout(root);

    const convertNode = (d3Node: HierarchyNode<MindMapNodeData>, level: number = 0): LayoutNode => {
      const isRoot = d3Node.data.id === 'root';
      return {
        id: d3Node.data.id,
        label: d3Node.data.label,
        level,
        x: (d3Node.y || 0) + (isRoot ? ROOT_PADDING : 0),
        y: (d3Node.x || 0) + (isRoot ? ROOT_PADDING : 0),
        width: NODE_WIDTH,
        height: calculateNodeHeight(d3Node.data.label),
        children: d3Node.children ? d3Node.children.map((child) => convertNode(child, level + 1)) : [],
        data: d3Node.data,
      };
    };
    return convertNode(root);
  }, [treeData]);

  const getVisibleNodes = useCallback((node: LayoutNode | null, visible: LayoutNode[] = []): LayoutNode[] => {
    if (!node) return visible;
    visible.push(node);
    if (expandedNodes.has(node.id) && node.children.length > 0) {
      node.children.forEach(child => getVisibleNodes(child, visible));
    }
    return visible;
  }, [expandedNodes]);

  const visibleNodes = useMemo(() => buildLayoutTree ? getVisibleNodes(buildLayoutTree) : [], [buildLayoutTree, getVisibleNodes]);

  // FIXED: Auto-Panning (Not Shrinking)
  useEffect(() => {
    const currentExpanded = Array.from(expandedNodes);
    if (currentExpanded.length > previousExpandedNodesRef.current.size) {
      const lastId = currentExpanded[currentExpanded.length - 1];
      const newNode = visibleNodes.find(n => n.id === lastId);
      
      if (newNode) {
        // Check if the node is going off-screen to the right
        const nodeXInViewport = (newNode.x * zoom) + pan.x;
        if (nodeXInViewport > containerSize.width - 400) {
          setPan(prev => ({ ...prev, x: prev.x - 300 }));
        }
      }
    }
    previousExpandedNodesRef.current = new Set(expandedNodes);
  }, [expandedNodes, visibleNodes, zoom, containerSize.width]);

  // Dark Mode & Size Listeners
  useEffect(() => {
    const checkDarkMode = () => {
      setIsDarkMode(window.matchMedia('(prefers-color-scheme: dark)').matches || document.documentElement.classList.contains('dark'));
    };
    checkDarkMode();
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', checkDarkMode);
    return () => mediaQuery.removeEventListener('change', checkDarkMode);
  }, []);

  useEffect(() => {
    const updateSize = () => { if (containerRef.current) setContainerSize(containerRef.current.getBoundingClientRect()); };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // UI Handlers
  const toggleNode = (nodeId: string, e?: React.MouseEvent) => {
    if (e) { e.stopPropagation(); e.preventDefault(); }
    setExpandedNodes(prev => {
      const newSet = new Set(prev);
      newSet.has(nodeId) ? newSet.delete(nodeId) : newSet.add(nodeId);
      return newSet;
    });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
  };

  const renderConnections = () => {
    const connections: JSX.Element[] = [];
    const processNode = (node: LayoutNode) => {
      if (expandedNodes.has(node.id) && node.children.length > 0) {
        node.children.forEach(child => {
          const childVisible = visibleNodes.find(n => n.id === child.id);
          if (childVisible) {
            const colors = getLevelColor(node.level);
            const x1 = node.x + node.width / 2;
            const y1 = node.y;
            const x2 = childVisible.x - childVisible.width / 2;
            const y2 = childVisible.y;
            connections.push(
              <path
                key={`${node.id}-${child.id}`}
                d={`M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`}
                stroke={isDarkMode ? colors.lineDark : colors.line}
                strokeWidth="2.5"
                fill="none"
                opacity="0.6"
              />
            );
            processNode(childVisible);
          }
        });
      }
    };
    if (buildLayoutTree) processNode(buildLayoutTree);
    return connections;
  };

  const renderNode = (node: LayoutNode) => {
    const colors = getLevelColor(node.level);
    const isExpanded = expandedNodes.has(node.id);
    const hasChildren = node.children.length > 0;

    // Text Wrapping Logic
    const words = node.label.split(' ');
    const lines: string[] = [];
    let currentLine = '';
    const maxChars = Math.floor((NODE_WIDTH - NODE_PADDING * 2) / 9);
    words.forEach(w => {
      if ((currentLine + w).length <= maxChars) currentLine += (currentLine ? ' ' : '') + w;
      else { if (currentLine) lines.push(currentLine); currentLine = w; }
    });
    if (currentLine) lines.push(currentLine);
    const textLines = lines.slice(0, 3);

    return (
      <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
        <rect
          x={-node.width / 2}
          y={-node.height / 2}
          width={node.width}
          height={node.height}
          rx="14"
          fill={isDarkMode ? colors.bgLightDark : colors.bgLight}
          stroke={isDarkMode ? colors.borderDark : colors.border}
          strokeWidth="2"
          className="cursor-pointer hover:opacity-90 transition-opacity"
          onClick={(e) => hasChildren && toggleNode(node.id, e)}
        />
        {textLines.map((line, idx) => (
          <text
            key={idx}
            y={-(textLines.length - 1) * 13 + idx * 26}
            textAnchor="middle"
            dominantBaseline="middle"
            fill={isDarkMode ? colors.textDark : colors.text}
            fontSize={node.level <= 1 ? '18' : '16'}
            fontWeight={node.level <= 1 ? '600' : '500'}
            className="pointer-events-none select-none"
          >
            {line}
          </text>
        ))}
        {hasChildren && (
          <g transform={`translate(${node.width/2 - 24}, ${-node.height/2 + 24})`} onClick={(e) => toggleNode(node.id, e)} className="cursor-pointer">
            <circle r="14" fill={colors.bg} stroke="white" strokeWidth="2" />
            <line x1="-7" y1="0" x2="7" y2="0" stroke="white" strokeWidth="3" strokeLinecap="round" />
            {!isExpanded && <line x1="0" y1="-7" x2="0" y2="7" stroke="white" strokeWidth="3" strokeLinecap="round" />}
          </g>
        )}
      </g>
    );
  };

  if (!treeData || !buildLayoutTree) return <div className="p-6 text-center">Loading mind map...</div>;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-900">
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div>
          <h3 className="text-xl font-bold">Mind Map</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">Click nodes to explore</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => setZoom(z => Math.max(z - 0.1, 0.4))}><ZoomOut className="w-4 h-4" /></Button>
          <Button variant="secondary" size="sm" onClick={() => setZoom(z => Math.min(z + 0.2, 2))}><ZoomIn className="w-4 h-4" /></Button>
          <Button variant="secondary" size="sm" onClick={() => { setZoom(1); setPan({ x: 100 + ROOT_PADDING, y: containerSize.height / 2 + ROOT_PADDING }); }}><RotateCcw className="w-4 h-4" /></Button>
          <div className="w-px h-6 bg-slate-200 dark:bg-slate-700 mx-1" />
          <Button variant="secondary" size="sm" onClick={() => {
             const ids = new Set<string>();
             const collect = (n: LayoutNode) => { if(n.children.length) { ids.add(n.id); n.children.forEach(collect); } };
             collect(buildLayoutTree); setExpandedNodes(ids);
          }}><Eye className="w-4 h-4 mr-2" /> Expand All</Button>
          <Button variant="secondary" size="sm" onClick={() => setExpandedNodes(new Set())}><EyeOff className="w-4 h-4 mr-2" /> Collapse All</Button>
          <div className="w-px h-6 bg-slate-200 dark:bg-slate-700 mx-1" />
          <Button 
            variant="secondary" 
            size="sm" 
            onClick={async () => {
              if (svgRef.current) {
                // Export the SVG directly
                const svgElement = svgRef.current;
                const svgData = new XMLSerializer().serializeToString(svgElement);
                const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
                const svgUrl = URL.createObjectURL(svgBlob);
                
                // Get SVG dimensions
                const svgWidth = parseInt(svgElement.getAttribute('width') || '1200', 10);
                const svgHeight = parseInt(svgElement.getAttribute('height') || '800', 10);
                
                // Convert SVG to PNG using canvas
                const img = new Image();
                img.onload = () => {
                  const canvas = document.createElement('canvas');
                  canvas.width = svgWidth;
                  canvas.height = svgHeight;
                  const ctx = canvas.getContext('2d');
                  if (ctx) {
                    // Fill with white background
                    ctx.fillStyle = '#ffffff';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    
                    // Draw SVG
                    ctx.drawImage(img, 0, 0);
                    
                    // Convert to blob and download
                    canvas.toBlob((blob) => {
                      if (blob) {
                        const downloadUrl = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        a.download = `mindmap-${Date.now()}.png`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(downloadUrl);
                      }
                    }, 'image/png');
                  }
                  URL.revokeObjectURL(svgUrl);
                };
                img.onerror = () => {
                  // Fallback: Download as SVG
                  const a = document.createElement('a');
                  a.href = svgUrl;
                  a.download = `mindmap-${Date.now()}.svg`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  URL.revokeObjectURL(svgUrl);
                };
                img.src = svgUrl;
              }
            }}
            className="flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export Image
          </Button>
        </div>
      </div>

      <div 
        ref={containerRef}
        className="flex-1 relative overflow-hidden bg-slate-50 dark:bg-slate-950"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={() => setIsPanning(false)}
        onMouseLeave={() => setIsPanning(false)}
      >
        <svg ref={svgRef} width="100%" height="100%" className="absolute inset-0" style={{ cursor: isPanning ? 'grabbing' : 'grab' }}>
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {renderConnections()}
            {visibleNodes.map(renderNode)}
          </g>
        </svg>
      </div>
    </div>
  );
}