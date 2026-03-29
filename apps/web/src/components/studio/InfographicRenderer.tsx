'use client';

import React, { forwardRef } from 'react';
import {
  Zap, Brain, Heart, Clock, Layers, Target, Shield, Leaf, Sun,
  Droplets, Eye, Scale, TrendingUp, Activity, BookOpen, Lightbulb,
  Cog, Globe, BarChart, Microscope, Thermometer, ArrowRight,
  GitBranch, FlaskConical, Dna, Atom, Users, Map, Flag, Star,
  type LucideIcon,
} from 'lucide-react';

const ICON_MAP: Record<string, LucideIcon> = {
  zap: Zap, brain: Brain, heart: Heart, clock: Clock, layers: Layers,
  target: Target, shield: Shield, leaf: Leaf, sun: Sun, droplets: Droplets,
  eye: Eye, scale: Scale, 'trending-up': TrendingUp, activity: Activity,
  'book-open': BookOpen, lightbulb: Lightbulb, cog: Cog, globe: Globe,
  'bar-chart': BarChart, microscope: Microscope, thermometer: Thermometer,
  'arrow-right': ArrowRight, 'git-branch': GitBranch, flask: FlaskConical,
  dna: Dna, atom: Atom, users: Users, map: Map, flag: Flag, star: Star,
};

function getIcon(name?: string): LucideIcon {
  if (!name) return BookOpen;
  return ICON_MAP[name.toLowerCase()] ?? BookOpen;
}

interface Point {
  label: string;
  detail: string;
}

interface Section {
  heading: string;
  icon?: string;
  tagline?: string;
  points: Point[];
}

interface ComparisonTable {
  title?: string;
  headers: string[];
  rows: string[][];
}

interface FlowStep {
  step: number;
  label: string;
  detail: string;
}

export interface InfographicData {
  title: string;
  subtitle?: string;
  layout: 'comparison' | 'process' | 'timeline' | 'sections';
  color_theme: 'blue' | 'green' | 'purple' | 'teal' | 'orange';
  sections: Section[];
  comparison?: ComparisonTable;
  flow_steps?: FlowStep[];
  key_takeaway?: string;
}

const THEME_COLORS: Record<string, {
  primary: string; primaryBg: string; primaryBorder: string;
  secondary: string; secondaryBg: string; secondaryBorder: string;
  accent: string; headerBg: string; headerText: string;
  tableBorder: string; tableHeaderBg: string; takeawayBg: string;
  stepBg: string; stepBorder: string; stepConnector: string;
}> = {
  blue: {
    primary: '#2563eb', primaryBg: '#eff6ff', primaryBorder: '#bfdbfe',
    secondary: '#7c3aed', secondaryBg: '#f5f3ff', secondaryBorder: '#ddd6fe',
    accent: '#2563eb', headerBg: '#1e40af', headerText: '#ffffff',
    tableBorder: '#bfdbfe', tableHeaderBg: '#dbeafe', takeawayBg: '#eff6ff',
    stepBg: '#eff6ff', stepBorder: '#93c5fd', stepConnector: '#93c5fd',
  },
  green: {
    primary: '#059669', primaryBg: '#ecfdf5', primaryBorder: '#a7f3d0',
    secondary: '#0891b2', secondaryBg: '#ecfeff', secondaryBorder: '#a5f3fc',
    accent: '#059669', headerBg: '#065f46', headerText: '#ffffff',
    tableBorder: '#a7f3d0', tableHeaderBg: '#d1fae5', takeawayBg: '#ecfdf5',
    stepBg: '#ecfdf5', stepBorder: '#6ee7b7', stepConnector: '#6ee7b7',
  },
  purple: {
    primary: '#7c3aed', primaryBg: '#f5f3ff', primaryBorder: '#ddd6fe',
    secondary: '#db2777', secondaryBg: '#fdf2f8', secondaryBorder: '#fbcfe8',
    accent: '#7c3aed', headerBg: '#5b21b6', headerText: '#ffffff',
    tableBorder: '#ddd6fe', tableHeaderBg: '#ede9fe', takeawayBg: '#f5f3ff',
    stepBg: '#f5f3ff', stepBorder: '#c4b5fd', stepConnector: '#c4b5fd',
  },
  teal: {
    primary: '#0d9488', primaryBg: '#f0fdfa', primaryBorder: '#99f6e4',
    secondary: '#2563eb', secondaryBg: '#eff6ff', secondaryBorder: '#bfdbfe',
    accent: '#0d9488', headerBg: '#115e59', headerText: '#ffffff',
    tableBorder: '#99f6e4', tableHeaderBg: '#ccfbf1', takeawayBg: '#f0fdfa',
    stepBg: '#f0fdfa', stepBorder: '#5eead4', stepConnector: '#5eead4',
  },
  orange: {
    primary: '#ea580c', primaryBg: '#fff7ed', primaryBorder: '#fed7aa',
    secondary: '#ca8a04', secondaryBg: '#fefce8', secondaryBorder: '#fef08a',
    accent: '#ea580c', headerBg: '#9a3412', headerText: '#ffffff',
    tableBorder: '#fed7aa', tableHeaderBg: '#ffedd5', takeawayBg: '#fff7ed',
    stepBg: '#fff7ed', stepBorder: '#fdba74', stepConnector: '#fdba74',
  },
};

function SectionCard({ section, theme, index }: {
  section: Section; theme: typeof THEME_COLORS.blue; index: number;
}) {
  const colors = index % 2 === 0
    ? { bg: theme.primaryBg, border: theme.primaryBorder, icon: theme.primary }
    : { bg: theme.secondaryBg, border: theme.secondaryBorder, icon: theme.secondary };
  const Icon = getIcon(section.icon);

  return (
    <div
      style={{ backgroundColor: colors.bg, borderColor: colors.border }}
      className="rounded-xl border-2 p-5 flex flex-col gap-3"
    >
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: colors.icon + '18' }}
        >
          <Icon className="w-5 h-5" style={{ color: colors.icon }} />
        </div>
        <div>
          <h3 className="font-bold text-base text-gray-900 leading-tight">{section.heading}</h3>
          {section.tagline && (
            <p className="text-xs font-medium mt-0.5" style={{ color: colors.icon }}>
              {section.tagline}
            </p>
          )}
        </div>
      </div>
      <ul className="space-y-2.5">
        {section.points.map((pt, i) => (
          <li key={i} className="flex items-start gap-2.5">
            <span
              className="mt-1.5 w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: colors.icon }}
            />
            <div>
              <span className="font-semibold text-sm text-gray-900">{pt.label}</span>
              {pt.detail && (
                <span className="text-sm text-gray-600"> — {pt.detail}</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ComparisonTableView({ table, theme }: {
  table: ComparisonTable; theme: typeof THEME_COLORS.blue;
}) {
  if (!table.headers?.length || !table.rows?.length) return null;
  return (
    <div className="mt-4">
      {table.title && (
        <h4 className="text-sm font-bold text-gray-800 mb-2 text-center">{table.title}</h4>
      )}
      <div className="overflow-x-auto rounded-lg border-2" style={{ borderColor: theme.tableBorder }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ backgroundColor: theme.tableHeaderBg }}>
              {table.headers.map((h, i) => (
                <th key={i} className="px-4 py-2.5 text-left font-bold text-gray-800 border-b-2"
                  style={{ borderColor: theme.tableBorder }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, ri) => (
              <tr key={ri} className={ri % 2 === 0 ? 'bg-white' : ''} style={ri % 2 !== 0 ? { backgroundColor: theme.primaryBg } : {}}>
                {row.map((cell, ci) => (
                  <td key={ci}
                    className={`px-4 py-2 border-b text-gray-700 ${ci === 0 ? 'font-semibold text-gray-800' : ''}`}
                    style={{ borderColor: theme.tableBorder }}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProcessFlow({ steps, theme }: {
  steps: FlowStep[]; theme: typeof THEME_COLORS.blue;
}) {
  if (!steps?.length) return null;
  return (
    <div className="mt-4 flex flex-col gap-0">
      {steps.map((s, i) => (
        <React.Fragment key={i}>
          <div className="flex items-start gap-4">
            <div className="flex flex-col items-center">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm shrink-0"
                style={{ backgroundColor: theme.primary }}
              >
                {s.step}
              </div>
              {i < steps.length - 1 && (
                <div className="w-0.5 h-8" style={{ backgroundColor: theme.stepConnector }} />
              )}
            </div>
            <div className="pt-1.5 pb-4">
              <p className="font-bold text-sm text-gray-900">{s.label}</p>
              <p className="text-sm text-gray-600 mt-0.5">{s.detail}</p>
            </div>
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}

function KeyTakeaway({ text, theme }: { text: string; theme: typeof THEME_COLORS.blue }) {
  return (
    <div
      className="rounded-xl p-4 mt-4 border-2 border-dashed flex items-start gap-3"
      style={{ backgroundColor: theme.takeawayBg, borderColor: theme.primaryBorder }}
    >
      <Lightbulb className="w-5 h-5 shrink-0 mt-0.5" style={{ color: theme.primary }} />
      <p className="text-sm font-medium text-gray-800">{text}</p>
    </div>
  );
}

export const InfographicRenderer = forwardRef<HTMLDivElement, { data: InfographicData }>(
  function InfographicRenderer({ data }, ref) {
    const theme = THEME_COLORS[data.color_theme] || THEME_COLORS.blue;

    return (
      <div
        ref={ref}
        className="w-full bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-200"
        style={{ minWidth: 320, maxWidth: 900 }}
      >
        {/* Header */}
        <div
          className="px-6 py-5 text-center"
          style={{ backgroundColor: theme.headerBg }}
        >
          <h1 className="text-xl font-extrabold tracking-tight" style={{ color: theme.headerText }}>
            {data.title}
          </h1>
          {data.subtitle && (
            <p className="text-sm mt-1 font-medium" style={{ color: theme.headerText + 'cc' }}>
              {data.subtitle}
            </p>
          )}
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Sections grid */}
          {data.sections?.length > 0 && (
            <div className={
              data.layout === 'comparison' && data.sections.length === 2
                ? 'grid grid-cols-1 md:grid-cols-2 gap-4'
                : data.sections.length >= 3
                  ? 'grid grid-cols-1 md:grid-cols-2 gap-4'
                  : 'space-y-4'
            }>
              {data.sections.map((sec, i) => (
                <SectionCard key={i} section={sec} theme={theme} index={i} />
              ))}
            </div>
          )}

          {/* Comparison table */}
          {data.layout === 'comparison' && data.comparison && (
            <ComparisonTableView table={data.comparison} theme={theme} />
          )}

          {/* Process / Timeline flow */}
          {(data.layout === 'process' || data.layout === 'timeline') && data.flow_steps && (
            <ProcessFlow steps={data.flow_steps} theme={theme} />
          )}

          {/* Key takeaway */}
          {data.key_takeaway && (
            <KeyTakeaway text={data.key_takeaway} theme={theme} />
          )}
        </div>

        {/* Footer watermark */}
        <div className="px-6 py-2 border-t border-gray-100 text-center">
          <p className="text-[10px] text-gray-400 font-medium tracking-wide uppercase">
            Generated Study Infographic
          </p>
        </div>
      </div>
    );
  },
);
