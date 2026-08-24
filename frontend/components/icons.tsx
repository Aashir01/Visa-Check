// ---------------------------------------------------------------------------
// Icon set.
//
// One stroke weight (1.6), one 24-unit grid, round caps and joins throughout.
// Icons drift out of step the moment they are drawn inline in whichever page
// happens to need them, so they all live here instead.
// ---------------------------------------------------------------------------

type IconProps = { className?: string };

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function ShieldIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M12 2.8 4.8 5.6v5.8c0 4.4 3.1 8.5 7.2 9.6 4.1-1.1 7.2-5.2 7.2-9.6V5.6L12 2.8Z" />
      <path d="m8.9 12.1 2.2 2.2 4.2-4.3" />
    </svg>
  );
}

export function UploadIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M12 15.5V4m0 0L8.2 7.8M12 4l3.8 3.8" />
      <path d="M4 15.5v2.8A1.7 1.7 0 0 0 5.7 20h12.6a1.7 1.7 0 0 0 1.7-1.7v-2.8" />
    </svg>
  );
}

export function CheckIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="m5 12.5 4.5 4.5L19 7" />
    </svg>
  );
}

export function CheckCircleIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="8.6" />
      <path d="m8.3 12.2 2.4 2.4 4.9-5" />
    </svg>
  );
}

export function ScanIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M4 8V5.6A1.6 1.6 0 0 1 5.6 4H8M16 4h2.4A1.6 1.6 0 0 1 20 5.6V8M20 16v2.4a1.6 1.6 0 0 1-1.6 1.6H16M8 20H5.6A1.6 1.6 0 0 1 4 18.4V16" />
      <path d="M4 12h16" />
    </svg>
  );
}

export function ChartIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M4 20V4" />
      <path d="M4 20h16" />
      <path d="M8.5 20v-6M13 20V8.5M17.5 20v-9" />
    </svg>
  );
}

export function SparkleIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M12 3.2 13.4 8.6 18.8 10 13.4 11.4 12 16.8 10.6 11.4 5.2 10 10.6 8.6 12 3.2Z" />
      <path d="M18.3 15.2 19 17.4 21.2 18.1 19 18.8 18.3 21 17.6 18.8 15.4 18.1 17.6 17.4 18.3 15.2Z" opacity="0.55" />
    </svg>
  );
}

export function FormIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <rect x="4.8" y="3.2" width="14.4" height="17.6" rx="1.8" />
      <path d="M8.6 8h1M8.6 12h1M8.6 16h1" />
      <path d="M12.4 8h3.2M12.4 12h3.2M12.4 16h3.2" opacity="0.55" />
    </svg>
  );
}

export function CalendarIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <rect x="3.6" y="5" width="16.8" height="15.4" rx="1.8" />
      <path d="M3.6 9.6h16.8M8.2 3v4M15.8 3v4" />
      <circle cx="15.6" cy="15" r="1.7" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function RepeatIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M4 9.6a5 5 0 0 1 5-5h9m0 0-3-3m3 3-3 3" />
      <path d="M20 14.4a5 5 0 0 1-5 5H6m0 0 3 3m-3-3 3-3" />
    </svg>
  );
}

export function GlobeIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M3.4 12h17.2" />
      <path d="M12 3.4c2.2 2.4 3.4 5.4 3.4 8.6S14.2 18.2 12 20.6C9.8 18.2 8.6 15.2 8.6 12S9.8 5.8 12 3.4Z" />
    </svg>
  );
}

export function LockIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <rect x="4.8" y="10.2" width="14.4" height="10" rx="2" />
      <path d="M8.4 10.2V7.6a3.6 3.6 0 1 1 7.2 0v2.6" />
    </svg>
  );
}

export function ClockIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M12 7.4V12l3 1.8" />
    </svg>
  );
}

export function ArrowRightIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M4.5 12h15m0 0-5.4-5.4M19.5 12l-5.4 5.4" />
    </svg>
  );
}

export function ChevronDownIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="m6 9.5 6 6 6-6" />
    </svg>
  );
}

export function MenuIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}

export function CloseIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M6.4 6.4 17.6 17.6M17.6 6.4 6.4 17.6" />
    </svg>
  );
}

export function AlertIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M12 4.4 21 19.6H3L12 4.4Z" />
      <path d="M12 10v3.6M12 16.6h.01" />
    </svg>
  );
}

export function InfoIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M12 11.2v4.6M12 8.2h.01" />
    </svg>
  );
}

export function XCircleIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="8.6" />
      <path d="m9.4 9.4 5.2 5.2M14.6 9.4l-5.2 5.2" />
    </svg>
  );
}

export function FileIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M13.4 3.4H7.2a1.8 1.8 0 0 0-1.8 1.8v13.6a1.8 1.8 0 0 0 1.8 1.8h9.6a1.8 1.8 0 0 0 1.8-1.8V8.4l-5-5Z" />
      <path d="M13.2 3.6v4.6h4.8" />
    </svg>
  );
}

export function PassportIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <rect x="5" y="2.8" width="14" height="18.4" rx="2" />
      <circle cx="12" cy="9.6" r="3.2" />
      <path d="M8.8 16.8h6.4" />
    </svg>
  );
}

export function PlaneIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M10.6 4.2a1.4 1.4 0 0 1 2.8 0v5l6.6 3.8v2.2l-6.6-2v3.4l2.2 1.6v1.6L12 18.6l-3.6 1.2v-1.6l2.2-1.6v-3.4l-6.6 2v-2.2l6.6-3.8v-5Z" />
    </svg>
  );
}
