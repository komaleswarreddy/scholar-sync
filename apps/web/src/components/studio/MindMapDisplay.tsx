/**
 * Mind Map Display — ScholarSync brand, always-light canvas inside Studio modal.
 */

'use client';

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { Eye, EyeOff, ZoomIn, ZoomOut, RotateCcw, Download } from 'lucide-react';
import { hierarchy, tree, HierarchyNode } from 'd3-hierarchy';

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

interface NodeColors {
  bg: string;
  border: string;
  text: string;
  line: string;
  badge: string;
  isRoot?: boolean;
}

const BRAND = {
  primary: '#0D3D2E',
  text: '#0F7A52',
  surface: '#F0F7F4',
  muted: '#E8F2EE',
  homeText: '#1A1F1C',
  homeBorder: '#E8EBE9',
  teal: '#14B8A6',
  lineMuted: '#9CA3AF',
  white: '#FFFFFF',
};

const getNodeColors = (level: number, isRoot: boolean): NodeColors => {
  if (isRoot || level === 0) {
    return {
      bg: BRAND.primary,
      border: BRAND.text,
      text: BRAND.white,
      line: BRAND.text,
      badge: BRAND.text,
      isRoot: true,
    };
  }
  if (level <= 1) {
    return {
      bg: BRAND.surface,
      border: BRAND.text,
      text: BRAND.primary,
      line: BRAND.text,
      badge: BRAND.text,
    };
  }
  if (level === 2) {
    return {
      bg: BRAND.muted,
      border: BRAND.teal,
      text: BRAND.homeText,
      line: BRAND.teal,
      badge: BRAND.text,
    };
  }
  return {
    bg: BRAND.white,
    border: BRAND.homeBorder,
    text: BRAND.homeText,
    line: BRAND.lineMuted,
    badge: BRAND.text,
  };
};

const NODE_WIDTH = 280;
const HORIZONTAL_SPACING = 220;
const VERTICAL_SPACING = 80;
const NODE_PADDING = 24;
const NODE_MIN_HEIGHT = 90;
const ROOT_PADDING = 40;

function inlineSvgForExport(source: SVGSVGElement): SVGSVGElement {
  const clone = source.cloneNode(true) as SVGSVGElement;
  clone.querySelectorAll('rect').forEach((rect) => {
    const fill = rect.getAttribute('fill');
    const stroke = rect.getAttribute('stroke');
    if (fill) rect.setAttribute('fill', fill);
    if (stroke) rect.setAttribute('stroke', stroke);
  });
  clone.querySelectorAll('text').forEach((textEl) => {
    const fill = textEl.getAttribute('fill');
    if (fill) {
      textEl.setAttribute('fill', fill);
      textEl.style.fill = fill;
    }
    const stroke = textEl.getAttribute('stroke');
    if (stroke) {
      textEl.setAttribute('stroke', stroke);
      textEl.style.stroke = stroke;
    }
  });
  clone.querySelectorAll('path').forEach((path) => {
    const stroke = path.getAttribute('stroke');
    if (stroke) path.setAttribute('stroke', stroke);
  });
  clone.querySelectorAll('circle, line').forEach((el) => {
    const fill = el.getAttribute('fill');
    const stroke = el.getAttribute('stroke');
    if (fill) el.setAttribute('fill', fill);
    if (stroke) el.setAttribute('stroke', stroke);
  });
  return clone;
}

export function MindMapDisplay({ mindMapData, filename }: MindMapDisplayProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 100 + ROOT_PADDING, y: 400 + ROOT_PADDING });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [containerSize, setContainerSize] = useState({ width: 1200, height: 800 });
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const previousExpandedNodesRef = useRef<Set<string>>(new Set());

  const parseMarkdownToTree = (markdown: string): MindMapNodeData => {
    const lines = markdown.split('\n').filter((line) => line.trim());
    const rootLabel = filename || 'Root';
    const root: MindMapNodeData = { id: 'root', label: rootLabel, children: [] };
    const stack: { node: MindMapNodeData; level: number }[] = [{ node: root, level: 0 }];
    let nodeIdCounter = 0;

    lines.forEach((line) => {
      const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);
      const listMatch = line.match(/^[\s-*]*(.+)$/);
      if (headerMatch) {
        const level = headerMatch[1].length;
        const node: MindMapNodeData = {
          id: `node-${nodeIdCounter++}`,
          label: headerMatch[2].trim(),
          children: [],
        };
        while (stack.length > 1 && stack[stack.length - 1].level >= level) {
          stack.pop();
        }
        const parent = stack[stack.length - 1].node;
        if (!parent.children) parent.children = [];
        parent.children.push(node);
        stack.push({ node, level });
      } else if (listMatch) {
        const label = listMatch[1].trim();
        if (label && !label.startsWith('#')) {
          const level = stack.length > 0 ? stack[stack.length - 1].level + 1 : 1;
          const node: MindMapNodeData = {
            id: `node-${nodeIdCounter++}`,
            label,
            children: [],
          };
          while (stack.length > 1 && stack[stack.length - 1].level >= level) {
            stack.pop();
          }
          const parent = stack[stack.length - 1].node;
          if (!parent.children) parent.children = [];
          parent.children.push(node);
          stack.push({ node, level });
        }
      }
    });
    return root.children && root.children.length === 1 ? root.children[0] : root;
  };

  const parseMindMapData = useCallback((): MindMapNodeData | null => {
    try {
      let parsed: any = null;
      if (typeof mindMapData === 'string') {
        try {
          parsed = JSON.parse(mindMapData);
        } catch {
          return parseMarkdownToTree(mindMapData);
        }
      } else if (typeof mindMapData === 'object' && mindMapData !== null) {
        parsed = mindMapData;
      } else {
        return null;
      }

      if (parsed && typeof parsed === 'object' && 'id' in parsed && 'label' in parsed) {
        if (parsed.id === 'root' && parsed.label === 'Root' && filename) {
          parsed.label = filename;
        }
        return parsed as MindMapNodeData;
      }
      if (parsed?.content) {
        if (typeof parsed.content === 'string') return parseMarkdownToTree(parsed.content);
        const content = parsed.content as MindMapNodeData;
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
    words.forEach((word) => {
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
        children: d3Node.children
          ? d3Node.children.map((child) => convertNode(child, level + 1))
          : [],
        data: d3Node.data,
      };
    };
    return convertNode(root);
  }, [treeData]);

  const getVisibleNodes = useCallback(
    (node: LayoutNode | null, visible: LayoutNode[] = []): LayoutNode[] => {
      if (!node) return visible;
      visible.push(node);
      if (expandedNodes.has(node.id) && node.children.length > 0) {
        node.children.forEach((child) => getVisibleNodes(child, visible));
      }
      return visible;
    },
    [expandedNodes],
  );

  const visibleNodes = useMemo(
    () => (buildLayoutTree ? getVisibleNodes(buildLayoutTree) : []),
    [buildLayoutTree, getVisibleNodes],
  );

  useEffect(() => {
    const currentExpanded = Array.from(expandedNodes);
    if (currentExpanded.length > previousExpandedNodesRef.current.size) {
      const lastId = currentExpanded[currentExpanded.length - 1];
      const newNode = visibleNodes.find((n) => n.id === lastId);

      if (newNode) {
        const nodeXInViewport = newNode.x * zoom + pan.x;
        if (nodeXInViewport > containerSize.width - 400) {
          setPan((prev) => ({ ...prev, x: prev.x - 300 }));
        }
      }
    }
    previousExpandedNodesRef.current = new Set(expandedNodes);
  }, [expandedNodes, visibleNodes, zoom, containerSize.width, pan.x]);

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) setContainerSize(containerRef.current.getBoundingClientRect());
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const toggleNode = (nodeId: string, e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    setExpandedNodes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(nodeId)) newSet.delete(nodeId);
      else newSet.add(nodeId);
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

  const handleExportImage = async () => {
    if (!svgRef.current) return;

    const exportSvg = inlineSvgForExport(svgRef.current);
    const rect = containerRef.current?.getBoundingClientRect();
    const svgWidth = Math.max(Math.round(rect?.width ?? 1200), 1200);
    const svgHeight = Math.max(Math.round(rect?.height ?? 800), 800);
    exportSvg.setAttribute('width', String(svgWidth));
    exportSvg.setAttribute('height', String(svgHeight));
    exportSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

    const svgData = new XMLSerializer().serializeToString(exportSvg);
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const svgUrl = URL.createObjectURL(svgBlob);

    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = svgWidth;
      canvas.height = svgHeight;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = BRAND.white;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);

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
      const a = document.createElement('a');
      a.href = svgUrl;
      a.download = `mindmap-${Date.now()}.svg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(svgUrl);
    };
    img.src = svgUrl;
  };

  const renderConnections = () => {
    const connections: JSX.Element[] = [];
    const processNode = (node: LayoutNode) => {
      if (expandedNodes.has(node.id) && node.children.length > 0) {
        node.children.forEach((child) => {
          const childVisible = visibleNodes.find((n) => n.id === child.id);
          if (childVisible) {
            const colors = getNodeColors(node.level, node.id === 'root');
            const x1 = node.x + node.width / 2;
            const y1 = node.y;
            const x2 = childVisible.x - childVisible.width / 2;
            const y2 = childVisible.y;
            connections.push(
              <path
                key={`${node.id}-${child.id}`}
                d={`M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`}
                stroke={colors.line}
                strokeWidth="2.5"
                fill="none"
                opacity="0.65"
              />,
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
    const isRoot = node.id === 'root' || node.level === 0;
    const colors = getNodeColors(node.level, isRoot);
    const isExpanded = expandedNodes.has(node.id);
    const hasChildren = node.children.length > 0;

    const words = node.label.split(' ');
    const lines: string[] = [];
    let currentLine = '';
    const maxChars = Math.floor((NODE_WIDTH - NODE_PADDING * 2) / 9);
    words.forEach((w) => {
      if ((currentLine + w).length <= maxChars) currentLine += (currentLine ? ' ' : '') + w;
      else {
        if (currentLine) lines.push(currentLine);
        currentLine = w;
      }
    });
    if (currentLine) lines.push(currentLine);
    const textLines = lines.slice(0, 3);
    const fontSize = node.level <= 1 ? 17 : 15;

    return (
      <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
        <rect
          x={-node.width / 2}
          y={-node.height / 2}
          width={node.width}
          height={node.height}
          rx="14"
          fill={colors.bg}
          stroke={colors.border}
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
            fill={colors.text}
            stroke={colors.isRoot ? BRAND.primary : 'none'}
            strokeWidth={colors.isRoot ? 0.4 : 0}
            fontSize={fontSize}
            fontWeight={node.level <= 1 ? '600' : '500'}
            style={{ paintOrder: 'stroke fill' }}
            className="pointer-events-none select-none"
          >
            {line}
          </text>
        ))}
        {hasChildren && (
          <g
            transform={`translate(${node.width / 2 - 24}, ${-node.height / 2 + 24})`}
            onClick={(e) => toggleNode(node.id, e)}
            className="cursor-pointer"
          >
            <circle r="14" fill={colors.badge} stroke={BRAND.white} strokeWidth="2" />
            <line
              x1="-7"
              y1="0"
              x2="7"
              y2="0"
              stroke={BRAND.white}
              strokeWidth="3"
              strokeLinecap="round"
            />
            {!isExpanded && (
              <line
                x1="0"
                y1="-7"
                x2="0"
                y2="7"
                stroke={BRAND.white}
                strokeWidth="3"
                strokeLinecap="round"
              />
            )}
          </g>
        )}
      </g>
    );
  };

  if (!treeData || !buildLayoutTree) {
    const raw =
      typeof mindMapData === 'string' ? mindMapData : JSON.stringify(mindMapData, null, 2);
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[280px] text-center">
        <p className="text-sm font-semibold text-[var(--color-home-text)] mb-2">
          Could not render mind map
        </p>
        <p className="text-xs text-[var(--color-home-text-muted)] mb-4 max-w-md">
          The content could not be parsed into a tree. You can copy the raw output below.
        </p>
        <button
          type="button"
          className="profile-btn-secondary text-xs"
          onClick={() => navigator.clipboard.writeText(raw).catch(() => {})}
        >
          Copy raw content
        </button>
      </div>
    );
  }

  return (
    <div className="mind-map-display flex flex-col h-full">
      <div className="mind-map-display__toolbar flex items-center justify-between px-5 py-3 border-b border-[var(--color-home-border)] bg-white">
        <div>
          <h3 className="text-base font-semibold text-[var(--color-home-text)]">Mind Map</h3>
          <p className="text-xs text-[var(--color-home-text-muted)] mt-0.5">
            Click nodes to explore
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <button
            type="button"
            className="mind-map-display__icon-btn"
            onClick={() => setZoom((z) => Math.max(z - 0.1, 0.4))}
            aria-label="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            type="button"
            className="mind-map-display__icon-btn"
            onClick={() => setZoom((z) => Math.min(z + 0.2, 2))}
            aria-label="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            type="button"
            className="mind-map-display__icon-btn"
            onClick={() => {
              setZoom(1);
              setPan({ x: 100 + ROOT_PADDING, y: containerSize.height / 2 + ROOT_PADDING });
            }}
            aria-label="Reset view"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <div className="w-px h-6 bg-[var(--color-home-border)] mx-0.5" />
          <button
            type="button"
            className="profile-btn-secondary text-xs flex items-center gap-1.5 py-2 px-3"
            onClick={() => {
              const ids = new Set<string>();
              const collect = (n: LayoutNode) => {
                if (n.children.length) {
                  ids.add(n.id);
                  n.children.forEach(collect);
                }
              };
              collect(buildLayoutTree);
              setExpandedNodes(ids);
            }}
          >
            <Eye className="w-3.5 h-3.5" />
            Expand All
          </button>
          <button
            type="button"
            className="profile-btn-secondary text-xs flex items-center gap-1.5 py-2 px-3"
            onClick={() => setExpandedNodes(new Set())}
          >
            <EyeOff className="w-3.5 h-3.5" />
            Collapse All
          </button>
          <div className="w-px h-6 bg-[var(--color-home-border)] mx-0.5" />
          <button
            type="button"
            className="profile-btn-secondary text-xs flex items-center gap-1.5 py-2 px-3"
            onClick={() => void handleExportImage()}
          >
            <Download className="w-3.5 h-3.5" />
            Export Image
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className="mind-map-display__canvas flex-1 relative overflow-hidden"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={() => setIsPanning(false)}
        onMouseLeave={() => setIsPanning(false)}
      >
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          className="absolute inset-0"
          style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
        >
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {renderConnections()}
            {visibleNodes.map(renderNode)}
          </g>
        </svg>
      </div>
    </div>
  );
}
