'use client';

import Image from 'next/image';

type HomeHeroProps = {
  greetingName: string;
  performanceLine: string;
  weekLabel?: string;
  className?: string;
};

export function HomeHero({
  greetingName,
  performanceLine,
  weekLabel = 'TUESDAY • WEEK 14',
  className = '',
}: HomeHeroProps) {
  return (
    <section
      className={`flex flex-row items-stretch gap-4 sm:gap-5 lg:gap-6 pt-1 text-left min-h-0 ${className}`}
    >
      <div className="flex-1 min-w-0 flex flex-col justify-center">
        <p className="home-section-label mb-3">{weekLabel}</p>
        <h1 className="text-[22px] sm:text-[26px] lg:text-[28px] font-bold leading-[1.25] tracking-tight text-[var(--color-home-text)]">
          Welcome back, {greetingName}.
          <span className="block text-[var(--color-brand-text)] font-bold mt-0.5">
            Your study path is ready.
          </span>
        </h1>
        <p className="text-[var(--color-home-text-muted)] mt-3 text-[14px] sm:text-[15px] max-w-lg lg:max-w-xl leading-[1.55]">
          {performanceLine}
        </p>
      </div>

      <div className="hero-landscape-wrap hidden md:block flex-shrink-0 w-[200px] lg:w-[168px] xl:w-[180px] min-h-[172px] lg:min-h-[160px] self-stretch">
        <Image
          src="/images/home/hero-landscape-right.png"
          alt=""
          width={560}
          height={320}
          className="hero-landscape-img"
          priority
        />
      </div>
    </section>
  );
}
