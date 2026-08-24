// ---------------------------------------------------------------------------
// Visa / immigration themed vector illustrations.
// All artwork is original SVG drawn for this project — no third-party assets.
// Palette follows the professional navy + blue + emerald brand theme.
// ---------------------------------------------------------------------------

/**
 * Passport booklet with a visa page, visa stamp and a small plane route.
 * Used in the landing hero.
 */
export function PassportIllustration({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 460 360" fill="none" className={className} aria-hidden>
      <defs>
        <linearGradient id="pp-cover" x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#1E3A5F" />
          <stop offset="1" stopColor="#0D1B30" />
        </linearGradient>
        <linearGradient id="pp-page" x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#FFFFFF" />
          <stop offset="1" stopColor="#E7EEF7" />
        </linearGradient>
        <linearGradient id="pp-stamp" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#3B82F6" />
          <stop offset="1" stopColor="#1D4ED8" />
        </linearGradient>
        <radialGradient id="pp-halo" cx="0.5" cy="0.5" r="0.5">
          <stop stopColor="#3B82F6" stopOpacity="0.22" />
          <stop offset="1" stopColor="#3B82F6" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="pp-gold" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#FCD34D" />
          <stop offset="1" stopColor="#B45309" />
        </linearGradient>
      </defs>

      {/* soft halo */}
      <ellipse cx="230" cy="180" rx="210" ry="160" fill="url(#pp-halo)" />

      {/* dashed flight route */}
      <path
        d="M120 92 C 180 40, 290 48, 358 108"
        stroke="#60A5FA"
        strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray="1 9"
        opacity="0.7"
      />

      {/* plane */}
      <g transform="translate(342 104) rotate(18)">
        <path d="M0 8 L22 8 L28 0 L32 0 L28 8 L32 16 L28 16 L22 8 L0 8 Z" fill="#93C5FD" />
        <path d="M6 8 L22 8 L18 3 L6 3 Z" fill="#3B82F6" opacity="0.55" />
      </g>

      {/* shadow */}
      <ellipse cx="232" cy="322" rx="150" ry="14" fill="#020617" opacity="0.55" />

      {/* back cover */}
      <path
        d="M92 44 c-13 0 -22 9.5 -22 22.5 v 211 c0 13 9 22.5 22 22.5 h 48 V 44 Z"
        fill="url(#pp-cover)"
      />
      {/* cover emblem */}
      <circle cx="126" cy="110" r="20" stroke="url(#pp-gold)" strokeWidth="1.6" />
      <path
        d="M126 94 a16 16 0 1 0 0.1 0 M126 94 v 32 M126 102 c -7 3 -7 10 0 14 c 7 -4 7 -11 0 -14 M110 110 h 32"
        stroke="url(#pp-gold)"
        strokeWidth="1.3"
        fill="none"
      />
      <rect x="118" y="140" width="20" height="3.4" rx="1.7" fill="#FCD34D" opacity="0.85" />
      <rect x="112" y="149" width="32" height="2.4" rx="1.2" fill="#FCD34D" opacity="0.5" />

      {/* spine shading */}
      <rect x="140" y="44" width="10" height="256" fill="#020617" opacity="0.28" />

      {/* visa page */}
      <path
        d="M150 44 h 208 c 13 0 22 9.5 22 22.5 v 211 c 0 13 -9 22.5 -22 22.5 H 150 Z"
        fill="url(#pp-page)"
      />

      {/* page header band */}
      <rect x="150" y="44" width="230" height="34" fill="#0F1E33" />
      <rect x="168" y="56" width="70" height="10" rx="5" fill="#3B82F6" opacity="0.9" />
      <rect x="250" y="58" width="60" height="6" rx="3" fill="#64748B" opacity="0.6" />
      <rect x="322" y="58" width="42" height="6" rx="3" fill="#64748B" opacity="0.6" />

      {/* photo */}
      <rect x="172" y="98" width="72" height="88" rx="8" fill="#DBEAFE" />
      <circle cx="208" cy="130" r="16" fill="#93C5FD" />
      <path d="M184 178 a24 24 0 0 1 48 0 Z" fill="#93C5FD" />
      <rect x="172" y="98" width="72" height="88" rx="8" stroke="#60A5FA" strokeOpacity="0.6" strokeWidth="1.5" fill="none" />

      {/* text lines */}
      <rect x="260" y="102" width="92" height="8" rx="4" fill="#CBD5E1" />
      <rect x="260" y="120" width="74" height="7" rx="3.5" fill="#CBD5E1" opacity="0.75" />
      <rect x="260" y="138" width="84" height="7" rx="3.5" fill="#CBD5E1" opacity="0.75" />
      <rect x="260" y="158" width="66" height="7" rx="3.5" fill="#CBD5E1" opacity="0.6" />

      {/* visa stamp */}
      <g transform="translate(318 220)">
        <circle r="34" fill="url(#pp-stamp)" opacity="0.16" />
        <circle r="34" stroke="url(#pp-stamp)" strokeWidth="2.5" />
        <circle r="26.5" stroke="url(#pp-stamp)" strokeWidth="1.2" strokeDasharray="3 4" opacity="0.8" />
        <circle r="8" stroke="#2563EB" strokeWidth="1.6" fill="none" />
        <path d="M0 -5.5 L1.9 -1.3 L5 -0.2 L1.9 0.9 L0 5 L-1.9 0.9 L-5 -0.2 L-1.9 -1.3 Z" fill="#2563EB" />
        <text x="0" y="16.5" textAnchor="middle" fontSize="8" fontWeight="700" fill="#1D4ED8" fontFamily="Sora, Inter, sans-serif" letterSpacing="1">
          VISA
        </text>
      </g>

      {/* approval ticks */}
      <path d="m258 218 5 5 11-12" stroke="#10B981" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="m258 240 5 5 11-12" stroke="#10B981" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />

      {/* MRZ lines */}
      <g opacity="0.85">
        <rect x="168" y="286" width="196" height="9" rx="4.5" fill="#0F1E33" opacity="0.12" />
        <text x="172" y="293.5" fontSize="8" letterSpacing="2.5" fill="#334155" fontFamily="JetBrains Mono, ui-monospace, monospace">
          P&lt;PAK&lt;&lt;NAME&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;
        </text>
        <rect x="168" y="301" width="196" height="9" rx="4.5" fill="#0F1E33" opacity="0.12" />
        <text x="172" y="308.5" fontSize="8" letterSpacing="2.5" fill="#334155" fontFamily="JetBrains Mono, ui-monospace, monospace">
          1234567890&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;
        </text>
      </g>
    </svg>
  );
}

/**
 * Globe with flight routes and destination pins.
 * Used in the corridors / coverage section.
 */
export function GlobeIllustration({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 560 220" fill="none" className={className} aria-hidden>
      <defs>
        <radialGradient id="gl-sphere" cx="0.35" cy="0.3" r="1">
          <stop stopColor="#24415F" />
          <stop offset="1" stopColor="#0D1B30" />
        </radialGradient>
        <linearGradient id="gl-arc" x1="0" y1="0" x2="1" y2="0">
          <stop stopColor="#60A5FA" stopOpacity="0" />
          <stop offset="0.5" stopColor="#60A5FA" />
          <stop offset="1" stopColor="#60A5FA" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* globe */}
      <circle cx="250" cy="110" r="84" fill="url(#gl-sphere)" stroke="#3E5E84" strokeWidth="1.5" />
      <ellipse cx="250" cy="110" rx="84" ry="30" stroke="#3E5E84" strokeOpacity="0.8" fill="none" />
      <ellipse cx="250" cy="110" rx="30" ry="84" stroke="#3E5E84" strokeOpacity="0.8" fill="none" />
      <line x1="166" y1="110" x2="334" y2="110" stroke="#3E5E84" strokeOpacity="0.7" />
      <ellipse cx="250" cy="110" rx="84" ry="56" stroke="#3E5E84" strokeOpacity="0.5" fill="none" />

      {/* continents */}
      <path
        d="M205 58 c 8 -10 20 -8 28 0 c 10 10 4 24 -6 30 c -12 7 -28 2 -34 -10 c -4 -8 -2 -14 12 -20 Z"
        fill="#4C86C9"
        opacity="0.85"
      />
      <path
        d="M272 76 c 14 -8 30 -4 38 8 c 8 12 0 28 -12 34 c -14 7 -30 0 -36 -12 c -5 -10 -2 -24 10 -30 Z"
        fill="#4C86C9"
        opacity="0.7"
      />
      <path
        d="M224 150 c 10 -8 26 -6 32 6 c 6 12 -2 26 -14 30 c -12 4 -26 -6 -28 -18 c -1 -8 2 -14 10 -18 Z"
        fill="#4C86C9"
        opacity="0.7"
      />

      {/* route arcs */}
      <path d="M110 60 C 160 10, 330 4, 424 52" stroke="url(#gl-arc)" strokeWidth="2" strokeLinecap="round" strokeDasharray="6 6" />
      <path d="M96 150 C 150 200, 330 210, 440 170" stroke="url(#gl-arc)" strokeWidth="2" strokeLinecap="round" strokeDasharray="6 6" opacity="0.8" />
      <path d="M188 40 C 210 2, 296 -4, 390 30" stroke="url(#gl-arc)" strokeWidth="1.6" strokeLinecap="round" strokeDasharray="5 7" opacity="0.55" />

      {/* plane on arc */}
      <g transform="translate(300 46) rotate(14)">
        <path d="M0 7 L17 7 L22 0 L25 0 L22 7 L25 14 L22 14 L17 7 L0 7 Z" fill="#93C5FD" />
      </g>

      {/* destination pins */}
      <g transform="translate(424 52)">
        <circle r="10" fill="#3B82F6" opacity="0.18" />
        <path d="M0 0 c -5 -6 -10 -6 -10 -12 a10 10 0 1 1 20 0 c 0 6 -5 6 -10 12 Z" fill="#3B82F6" />
        <circle cy="-10" r="3.4" fill="#0B1220" />
      </g>
      <g transform="translate(440 170)">
        <circle r="10" fill="#10B981" opacity="0.18" />
        <path d="M0 0 c -5 -6 -10 -6 -10 -12 a10 10 0 1 1 20 0 c 0 6 -5 6 -10 12 Z" fill="#10B981" />
        <circle cy="-10" r="3.4" fill="#0B1220" />
      </g>
      <g transform="translate(96 150)">
        <circle r="10" fill="#F59E0B" opacity="0.18" />
        <path d="M0 0 c -5 -6 -10 -6 -10 -12 a10 10 0 1 1 20 0 c 0 6 -5 6 -10 12 Z" fill="#F59E0B" />
        <circle cy="-10" r="3.4" fill="#0B1220" />
      </g>
    </svg>
  );
}

/**
 * Stylised refusal form (Schengen-style) with one ground ticked.
 * Used in the refusal decoder section.
 */
export function RefusalFormIllustration({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 420 300" fill="none" className={className} aria-hidden>
      <defs>
        <linearGradient id="rf-page" x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#FFFFFF" />
          <stop offset="1" stopColor="#E9EFF7" />
        </linearGradient>
        <linearGradient id="rf-head" x1="0" y1="0" x2="1" y2="0">
          <stop stopColor="#0F1E33" />
          <stop offset="1" stopColor="#1E3A5F" />
        </linearGradient>
      </defs>

      {/* soft halo */}
      <ellipse cx="210" cy="150" rx="190" ry="130" fill="#3B82F6" opacity="0.06" />

      {/* shadow */}
      <rect x="72" y="36" width="276" height="232" rx="12" fill="#020617" opacity="0.45" transform="translate(6 8)" />

      {/* form page */}
      <rect x="72" y="36" width="276" height="232" rx="12" fill="url(#rf-page)" />

      {/* header */}
      <path d="M72 48 a12 12 0 0 1 12 -12 h 252 a12 12 0 0 1 12 12 v 40 h -276 Z" fill="url(#rf-head)" />
      <text x="210" y="64" textAnchor="middle" fontSize="11" fontWeight="700" letterSpacing="1.4" fill="#E9EEF6" fontFamily="Sora, Inter, sans-serif">
        REFUSAL OF VISA
      </text>
      <rect x="160" y="72" width="100" height="5" rx="2.5" fill="#60A5FA" opacity="0.7" />

      {/* section label */}
      <rect x="96" y="102" width="130" height="7" rx="3.5" fill="#CBD5E1" />

      {/* checkbox rows */}
      {[0, 1, 2, 3].map((i) => {
        const y = 126 + i * 30;
        return (
          <g key={i}>
            <rect x="96" y={y} width="13" height="13" rx="2.5" stroke="#64748B" strokeWidth="1.5" fill="none" />
            <rect x="120" y={y + 2} width={150 - (i === 1 ? 26 : 0)} height="7" rx="3.5" fill="#CBD5E1" opacity="0.8" />
          </g>
        );
      })}

      {/* the ground that was refused — box 3 ticked in red */}
      <rect x="96" y="186" width="13" height="13" rx="2.5" fill="#EF4444" />
      <path d="m99.5 192.5 2.6 2.6 5.4 -5.6" stroke="#FFFFFF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />

      {/* officer's note */}
      <rect x="96" y="224" width="230" height="8" rx="4" fill="#F1F5F9" />
      <rect x="96" y="240" width="180" height="8" rx="4" fill="#F1F5F9" />

      {/* stamp */}
      <g transform="translate(312 240)">
        <circle r="27" stroke="#2563EB" strokeWidth="2.2" />
        <circle r="21" stroke="#2563EB" strokeWidth="1.1" strokeDasharray="3 3.5" opacity="0.75" />
        <text x="0" y="1.5" textAnchor="middle" fontSize="6.4" fontWeight="700" fill="#2563EB" fontFamily="Sora, Inter, sans-serif" letterSpacing="0.6">
          ANNEX
        </text>
        <text x="0" y="10.5" textAnchor="middle" fontSize="6.4" fontWeight="700" fill="#2563EB" fontFamily="Sora, Inter, sans-serif" letterSpacing="0.6">
          VI
        </text>
      </g>
    </svg>
  );
}
