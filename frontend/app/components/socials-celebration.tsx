"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const TOTAL_PARTICLES = 50;
const CONFETTI_COLORS = ["#f4c8ff", "#cfe3ff", "#ffe2c0", "#d3ffef", "#ffd5e6", "#cfd4ff", "#fff2c7", "#daf7ff"];
const PARTICLE_SHAPES = ["dot", "chip", "streak", "shard"];

const SOCIAL_ICONS = [
  {
    id: "x",
    label: "X logo",
    delay: 300,
    duration: 2400,
    drift: -90,
    radius: 110,
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path
          d="M18.25 3.5h2.66l-5.82 6.64 6.85 10.36h-5.37l-4.2-6.18-4.82 6.18H2.69l6.21-7.32L2.48 3.5h5.47l3.79 5.56 4.51-5.56z"
          fill="currentColor"
        />
      </svg>
    ),
  },
  {
    id: "facebook",
    label: "Facebook logo",
    delay: 420,
    duration: 2900,
    drift: -45,
    radius: 130,
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path
          d="M14 8.5V6.7c0-.78.52-1.54 1.88-1.54h1.6V2.5h-2.75C10.62 2.5 9.6 4.41 9.6 6.46V8.5H7v2.66h2.6v10.34h3.4V11.16h2.74L16.2 8.5z"
          fill="currentColor"
        />
      </svg>
    ),
  },
  {
    id: "whatsapp",
    label: "WhatsApp logo",
    delay: 520,
    duration: 3000,
    drift: 0,
    radius: 150,
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path
          d="M12.04 3.3c-4.78 0-8.68 3.74-8.68 8.36 0 1.47.39 2.85 1.08 4.05l-1.13 4.14 4.2-1.1c1.15.63 2.47.99 3.86.99 4.78 0 8.68-3.74 8.68-8.36s-3.9-8.08-8.68-8.08zm0 15.1c-1.24 0-2.39-.34-3.37-.95l-.24-.14-2.47.65.66-2.41-.16-.25c-.63-1-.99-2.17-.99-3.34 0-3.47 2.94-6.3 6.57-6.3 3.63 0 6.57 2.82 6.57 6.3 0 3.48-2.94 6.44-6.57 6.44zm3.77-4.7c-.2-.1-1.2-.59-1.39-.65-.19-.07-.33-.1-.47.1-.14.2-.54.65-.66.78-.12.13-.24.15-.44.05-.2-.1-.84-.31-1.6-.99-.59-.52-.99-1.16-1.11-1.36-.12-.2-.01-.31.09-.41.09-.09.2-.23.3-.34.1-.11.14-.19.21-.32.07-.13.04-.25 0-.34-.04-.1-.47-1.14-.65-1.56-.17-.42-.35-.37-.47-.38h-.4c-.14 0-.36.05-.55.25-.19.2-.73.71-.73 1.73 0 1.02.75 2 0.86 2.14.12.14 1.48 2.32 3.59 3.23 2.11.91 2.11.61 2.5.58.39-.03 1.28-.52 1.45-1.02.18-.5.18-.93.13-1.02-.05-.09-.18-.15-.37-.25z"
          fill="currentColor"
        />
      </svg>
    ),
  },
  {
    id: "instagram",
    label: "Instagram logo",
    delay: 580,
    duration: 2800,
    drift: 45,
    radius: 130,
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <rect x="3.5" y="3.5" width="17" height="17" rx="5" fill="none" stroke="currentColor" strokeWidth="2" />
        <circle cx="12" cy="12" r="3.5" fill="none" stroke="currentColor" strokeWidth="2" />
        <circle cx="17.3" cy="6.7" r="1.2" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: "linkedin",
    label: "LinkedIn logo",
    delay: 640,
    duration: 3000,
    drift: 90,
    radius: 110,
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M5.1 9h3.04v9.5H5.1zM6.62 5.1a1.76 1.76 0 110 3.52 1.76 1.76 0 010-3.52z" fill="currentColor" />
        <path
          d="M11.04 9h2.9v1.32h.04c.4-.76 1.36-1.56 2.8-1.56 2.99 0 3.54 1.95 3.54 4.5v5.24h-3.03v-4.65c0-1.11-.02-2.55-1.55-2.55-1.56 0-1.8 1.22-1.8 2.47v4.73h-3.04z"
          fill="currentColor"
        />
      </svg>
    ),
  },
];

export function SocialsCelebration() {
  const [active, setActive] = useState(false);
  const hasPlayedRef = useRef(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const confettiPieces = useMemo(() => {
    return Array.from({ length: TOTAL_PARTICLES }, (_, index) => {
      const angleSpread = 150;
      const baseAngle = -angleSpread / 2 + Math.random() * angleSpread;
      const distance = 160 + Math.random() * 220;
      const radians = (baseAngle * Math.PI) / 180;
      const x = Math.sin(radians) * distance;
      const rawY = Math.cos(radians) * distance * 0.9;
      const y = Math.abs(rawY) + 80;

      return {
        id: `confetti-${index}`,
        delay: index * 14,
        duration: 900 + Math.random() * 1100,
        xOffset: x,
        yOffset: y,
        rotate: -45 + Math.random() * 90,
        size: 8 + Math.random() * 10,
        color: CONFETTI_COLORS[index % CONFETTI_COLORS.length],
        shape: PARTICLE_SHAPES[index < 30 ? index % PARTICLE_SHAPES.length : Math.floor(Math.random() * PARTICLE_SHAPES.length)],
      };
    });
  }, []);

  const iconDelayBase = confettiPieces[34]?.delay ?? 0;

  useEffect(() => {
    const node = containerRef.current;
    if (!node || typeof window === "undefined") {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasPlayedRef.current) {
            hasPlayedRef.current = true;
            setActive(true);
            observer.disconnect();
          }
        });
      },
      { threshold: 0.4 }
    );

    observer.observe(node);

    return () => observer.disconnect();
  }, []);

  return (
    <div ref={containerRef} className={`socials-confetti${active ? " is-active" : ""}`} aria-hidden="true">
      {confettiPieces.map((piece) => (
        <span
          key={piece.id}
          className="confetti-piece"
          style={
            {
              "--burst-delay": `${piece.delay}ms`,
              "--burst-duration": `${piece.duration}ms`,
              "--burst-x": `${piece.xOffset}px`,
              "--burst-y": `${piece.yOffset}px`,
              "--burst-rotate": `${piece.rotate}deg`,
              "--burst-size": `${piece.size}px`,
              background: piece.color,
            } as React.CSSProperties
          }
          data-shape={piece.shape}
        />
      ))}

      <div className="socials-icon-cloud">
        {SOCIAL_ICONS.map((icon) => (
          <span
            key={icon.id}
            className={`social-icon social-icon-${icon.id}`}
            style={
              {
                "--icon-delay": `${iconDelayBase + icon.delay}ms`,
                "--icon-duration": `${icon.duration}ms`,
                "--icon-drift": `${icon.drift}px`,
                "--icon-offset": `${icon.radius}px`,
              } as React.CSSProperties
            }
            aria-hidden="true"
          >
            {icon.svg}
          </span>
        ))}
      </div>
    </div>
  );
}
