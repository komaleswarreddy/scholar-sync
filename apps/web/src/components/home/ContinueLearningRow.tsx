'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Plus,
  Atom,
  FlaskConical,
  LayoutGrid,
  Leaf,
  ChevronRight,
} from 'lucide-react';
import { subjectToIcon } from '@/lib/home-mapper';

export type ContinueLearningItem = {
  id: string;
  slug: string;
  title: string;
  subject: string;
  topic: string;
  progress: number;
  lastStudied: string;
};

const subjectConfig = {
  physics: {
    Icon: Atom,
    circle: 'bg-[#0D3D2E]',
    icon: 'text-white',
  },
  chemistry: {
    Icon: FlaskConical,
    circle: 'bg-[#FFF4EC]',
    icon: 'text-[#EA580C]',
  },
  math: {
    Icon: LayoutGrid,
    circle: 'bg-[#E8F0FE]',
    icon: 'text-[#1A73E8]',
  },
  biology: {
    Icon: Leaf,
    circle: 'bg-[#E8F2EE]',
    icon: 'text-[#0D9488]',
  },
} as const;

export function ContinueLearningRow({ items }: { items: ContinueLearningItem[] }) {
  const router = useRouter();

  return (
    <section className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="home-section-label">Continue learning</h3>
        <Link
          href="/library"
          className="text-[13px] font-semibold text-[#0D3D2E] hover:underline"
        >
          View all library →
        </Link>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-1 home-scroll-row">
        {items.map((item) => {
          const iconKey = subjectToIcon(item.subject);
          const { Icon, circle, icon } = subjectConfig[iconKey];
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => router.push(`/notebook/${item.slug}`)}
              className="home-continue-card group"
            >
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${circle}`}
              >
                <Icon className={`w-4 h-4 ${icon}`} strokeWidth={1.75} />
              </div>
              <div className="flex-1 min-w-0 flex flex-col">
                <p className="text-[14px] font-bold text-[#1A1F1C] leading-tight truncate">
                  {item.title}
                </p>
                <p className="text-[12px] text-[#6B7280] mt-0.5 truncate">
                  {item.subject} • {item.topic}
                </p>
                <div className="mt-2 h-[4px] rounded-full bg-[#E8EBE9] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-[#0D3D2E]"
                    style={{ width: `${Math.min(100, Math.max(0, item.progress))}%` }}
                  />
                </div>
                <div className="flex items-center justify-between mt-2">
                  <p className="text-[12px] text-[#9CA3AF]">
                    Last studied • {item.lastStudied}
                  </p>
                  <ChevronRight className="w-4 h-4 text-[#9CA3AF] group-hover:text-[#0D3D2E] flex-shrink-0" />
                </div>
              </div>
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => router.push('/dashboard')}
          className="home-continue-card home-continue-card--create group"
        >
          <div className="w-9 h-9 rounded-full bg-[#F3F4F3] flex items-center justify-center flex-shrink-0">
            <Plus className="w-4 h-4 text-[#6B7280]" strokeWidth={2} />
          </div>
          <div className="flex-1 min-w-0 flex flex-col justify-center">
            <p className="text-[14px] font-bold text-[#1A1F1C]">Create new</p>
            <p className="text-[12px] text-[#9CA3AF] mt-1 leading-snug">
              Start a new notebook PDFs, notes, videos
            </p>
            <div className="flex justify-end mt-2">
              <ChevronRight className="w-4 h-4 text-[#9CA3AF] group-hover:text-[#0D3D2E]" />
            </div>
          </div>
        </button>
      </div>
    </section>
  );
}
