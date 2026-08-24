"use client";

import { useEffect, useRef, useState } from "react";

import { photoSrcSet, photoUrl, type Clip, type Photo } from "@/lib/media";

// ---------------------------------------------------------------------------
// Stills
// ---------------------------------------------------------------------------

/**
 * A photograph inside a fixed aspect box.
 *
 * Three things matter here and none of them are decoration. The box reserves
 * its height before the file arrives, so nothing below it jumps. The tint sits
 * underneath, so the gap is the colour of the photo rather than a white flash.
 * And a failed request leaves the tint in place instead of collapsing the
 * element — a hotlinked CDN will fail eventually, and when it does the page
 * should look plain, not broken.
 */
export function Picture({
  photo,
  /** CSS aspect ratio, e.g. "16/9". */
  ratio = "16/10",
  /** Rendered width hint for the browser's `srcset` maths. */
  sizes = "(min-width: 1024px) 33vw, 100vw",
  className = "",
  imgClassName = "",
  priority = false,
  children,
}: {
  photo: Photo;
  ratio?: string;
  sizes?: string;
  className?: string;
  imgClassName?: string;
  priority?: boolean;
  children?: React.ReactNode;
}) {
  const [state, setState] = useState<"loading" | "ready" | "failed">("loading");

  return (
    <div
      className={`relative overflow-hidden ${className}`}
      style={{ aspectRatio: ratio, backgroundColor: photo.tint }}
    >
      {state !== "failed" && (
        <img
          src={photoUrl(photo.src, 1200)}
          srcSet={photoSrcSet(photo.src)}
          sizes={sizes}
          alt={photo.alt}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          fetchPriority={priority ? "high" : "auto"}
          onLoad={() => setState("ready")}
          onError={() => setState("failed")}
          className={`h-full w-full object-cover transition-opacity duration-700 ${
            state === "ready" ? "opacity-100" : "opacity-0"
          } ${imgClassName}`}
        />
      )}

      {/* Holds the tint while the file is in flight, and forever if it never
          arrives. Slightly lightened so a dead image still reads as a surface. */}
      {state !== "ready" && (
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background: `linear-gradient(140deg, ${photo.tint}, rgba(8,13,24,0.85))`,
          }}
        />
      )}

      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Footage
// ---------------------------------------------------------------------------

/**
 * Background footage behind a block of text.
 *
 * Autoplaying video is a liability if handled carelessly, so this hedges on
 * every axis: the poster frame is painted first and never removed underneath,
 * playback is skipped entirely for anyone who asked for reduced motion, the
 * 720p file is used on narrow viewports, and the element is only asked to play
 * once it is actually on screen. If any of that fails the poster still fills
 * the frame and the section looks intentional.
 */
export function AmbientVideo({
  clip,
  className = "",
  /** Slow drift applied to the poster while the video loads. */
  kenburns = true,
}: {
  clip: Clip;
  className?: string;
  kenburns?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [playing, setPlaying] = useState(false);

  // Motion preference decides whether we load the file at all — there is no
  // point spending several megabytes on something we are about to hide.
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setEnabled(!query.matches);
    apply();
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, []);

  // Pause once scrolled past. Decoding video nobody can see costs battery on
  // exactly the phones most likely to be reading this page.
  useEffect(() => {
    const el = videoRef.current;
    if (!el || !enabled) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void el.play().catch(() => undefined);
        else el.pause();
      },
      { threshold: 0.05 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [enabled]);

  const narrow = typeof window !== "undefined" && window.innerWidth < 900;

  return (
    <div className={`absolute inset-0 overflow-hidden ${className}`} style={{ backgroundColor: clip.tint }}>
      <img
        src={clip.poster}
        alt=""
        aria-hidden
        className={`absolute inset-0 h-full w-full object-cover ${
          kenburns && !playing ? "kenburns" : ""
        }`}
      />

      {enabled && (
        <video
          ref={videoRef}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-1000 ${
            playing ? "opacity-100" : "opacity-0"
          }`}
          muted
          loop
          playsInline
          preload="none"
          poster={clip.poster}
          aria-label={clip.alt}
          onPlaying={() => setPlaying(true)}
        >
          <source src={narrow ? clip.srcSmall : clip.src} type="video/mp4" />
        </video>
      )}
    </div>
  );
}

/**
 * The wash that makes text legible over footage.
 *
 * Kept as its own component because every section that uses video needs the
 * same three layers and getting one of them wrong is how hero copy ends up
 * unreadable on a bright frame.
 */
export function MediaScrim({
  /** "left" for text set against the left edge, "bottom" for captions. */
  direction = "left",
  className = "",
}: {
  direction?: "left" | "bottom" | "full" | "panel";
  className?: string;
}) {
  const gradients: Record<string, string> = {
    left:
      "linear-gradient(100deg, rgba(5,9,17,0.97) 0%, rgba(8,13,24,0.92) 38%, rgba(8,13,24,0.62) 66%, rgba(8,13,24,0.35) 100%)",
    bottom:
      "linear-gradient(to top, rgba(5,9,17,0.96) 0%, rgba(8,13,24,0.55) 45%, rgba(8,13,24,0.2) 100%)",
    // Heavy enough to carry body copy anywhere on the frame.
    full: "linear-gradient(180deg, rgba(5,9,17,0.82) 0%, rgba(8,13,24,0.88) 100%)",
    // For a side panel, where the copy sits in the lower half. The top stays
    // light so an already low-key clip still reads as a photograph rather
    // than a black rectangle.
    panel:
      "linear-gradient(180deg, rgba(5,9,17,0.30) 0%, rgba(8,13,24,0.62) 45%, rgba(5,9,17,0.93) 100%)",
  };

  return (
    <>
      <div aria-hidden className={`absolute inset-0 ${className}`} style={{ background: gradients[direction] }} />
      {/* Floor the section into the page background so there is no hard seam. */}
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-surface to-transparent"
      />
    </>
  );
}
