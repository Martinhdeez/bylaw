// Bylaw's logo (web/public/logo.svg), inline so it takes the current text colour for the tile.
export function BylawMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 120" className={className} aria-hidden="true">
      <defs>
        <mask id="bylaw-m" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">
          <rect width="120" height="120" fill="#fff" />
          <g transform="translate(60 60) scale(0.84) translate(-60 -60)">
            <rect x="26" y="16" width="22" height="88" rx="5" fill="#000" />
            <rect x="38" y="46" width="56" height="58" rx="24" fill="#000" />
          </g>
          <path
            d="M122.0 6.0 L109.3 12.7 L107.5 25.3 L92.0 33.6 L90.0 47.9 L73.5 57.3 L66.2 73.0 L52.3 76.6 L45.5 94.7 L31.0 101.9 L22.0 118.0"
            fill="none"
            stroke="#000"
            strokeWidth="10"
            strokeLinejoin="round"
          />
        </mask>
      </defs>
      <rect x="8" y="8" width="104" height="104" rx="28" fill="currentColor" mask="url(#bylaw-m)" />
      <circle cx="65.0" cy="72.6" r="7.6" fill="#07090E" stroke="#9152ff" strokeWidth="5" />
    </svg>
  );
}
