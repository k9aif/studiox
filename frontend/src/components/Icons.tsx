// Small hand-drawn line-icon set shared by LandingPage's "How it works"
// cards and OnboardingWizard's capability rows — kept in one place so both
// surfaces stay visually consistent (Process Studio uses one icon style
// throughout, not a mix).
export type IconKind = 'architecture' | 'shield' | 'gauge' | 'loop' | 'flow' | 'package' | 'document' | 'checklist' | 'bolt' | 'shield-check';

const ICON_PATHS: Record<IconKind, React.ReactNode> = {
  architecture: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.2" />
      <rect x="14" y="3" width="7" height="7" rx="1.2" />
      <rect x="3" y="14" width="7" height="7" rx="1.2" />
      <rect x="14" y="14" width="7" height="7" rx="1.2" />
    </>
  ),
  shield: <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />,
  gauge: (
    <>
      <path d="M4 16a8 8 0 0 1 16 0" />
      <path d="M12 16l4-5" />
      <circle cx="12" cy="16" r="1.1" fill="currentColor" stroke="none" />
    </>
  ),
  loop: (
    <>
      <path d="M4 12a8 8 0 0 1 14-5" />
      <path d="M18 3v4h-4" />
      <path d="M20 12a8 8 0 0 1-14 5" />
      <path d="M6 21v-4h4" />
    </>
  ),
  flow: (
    <>
      <circle cx="4.5" cy="18" r="2" />
      <circle cx="12" cy="6" r="2" />
      <circle cx="19.5" cy="18" r="2" />
      <path d="M6.2 16.3 10.3 7.7M13.7 7.7 17.8 16.3" />
    </>
  ),
  package: (
    <>
      <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z" />
      <path d="M4 7.5 12 12l8-4.5M12 12v9" />
    </>
  ),
  document: (
    <>
      <path d="M6 2.5h9l3 3v16a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-19a.5.5 0 0 1 .5-.5z" />
      <path d="M15 2.5V6h3.5" />
      <path d="M8 12h8M8 15.5h8M8 19h5" />
    </>
  ),
  checklist: (
    <>
      <rect x="3" y="4" width="4" height="4" rx="0.8" />
      <path d="M4 6l1 1 2-2" />
      <rect x="3" y="11" width="4" height="4" rx="0.8" />
      <path d="M4 13l1 1 2-2" />
      <path d="M10 6h11M10 13h6" />
      <circle cx="16.5" cy="17.5" r="3.2" />
      <path d="M18.9 19.9 21 22" />
    </>
  ),
  bolt: <path d="M13 2 4 14h6l-1 8 9-12h-6z" />,
  'shield-check': (
    <>
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
      <path d="M9 12.2l2 2 4-4.4" />
    </>
  ),
};

export function Icon({ kind, size = 24 }: { kind: IconKind; size?: number }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="1.7"
      strokeLinecap="round" strokeLinejoin="round"
    >
      {ICON_PATHS[kind]}
    </svg>
  );
}
