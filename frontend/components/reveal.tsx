"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Fades a block in the first time it reaches the viewport.
 *
 * Deliberately one-shot: elements that re-animate on every scroll past are
 * distracting on a long page. It also starts visible and only hides itself
 * once the observer is wired up, so the content is still there if JavaScript
 * never runs or the browser lacks IntersectionObserver.
 */
export function Reveal({
  children,
  delay = 0,
  className = "",
  as: Tag = "div",
}: {
  children: React.ReactNode;
  /** Milliseconds, for staggering a row of cards. */
  delay?: number;
  className?: string;
  as?: "div" | "section" | "li";
}) {
  const ref = useRef<HTMLElement | null>(null);
  const [shown, setShown] = useState(false);
  const [armed, setArmed] = useState(false);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") {
      setShown(true);
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(true);
      return;
    }

    setArmed(true);
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.05 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const hidden = armed && !shown;

  return (
    <Tag
      ref={ref as never}
      className={`transition-all duration-700 ease-out ${
        hidden ? "translate-y-5 opacity-0" : "translate-y-0 opacity-100"
      } ${className}`}
      style={{ transitionDelay: hidden ? "0ms" : `${delay}ms` }}
    >
      {children}
    </Tag>
  );
}
