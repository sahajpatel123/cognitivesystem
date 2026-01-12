"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { SectionReveal } from "./section-reveal";

const cards = [
  {
    title: "Deterministic execution",
    body: "All guidance is generated synchronously during the live exchange. Nothing is revised after the moment passes.",
  },
  {
    title: "Session-scoped memory",
    body: "Each conversation is sealed. Context does not persist beyond the active session.",
  },
  {
    title: "Guardrail-locked output",
    body: "Tone, scope, and claims are constrained in real time before any suggestion appears.",
  },
  {
    title: "Operator-first surface",
    body: "The system observes quietly. It never injects itself into the call.",
  },
];

const CARD_DURATION = 0.2;
const CARD_DURATION_MS = CARD_DURATION * 1000;
const RESET_DELAY_MS = 1400;

export function CardDeckSection() {
  const [index, setIndex] = useState(0);
  const [visibleCard, setVisibleCard] = useState<number | null>(null);
  const [deckEmpty, setDeckEmpty] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [hasActivated, setHasActivated] = useState(false);
  const timerRef = useRef<number | null>(null);

  const clearTimer = () => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  useEffect(
    () => () => {
      clearTimer();
    },
    [],
  );

  const advanceDeck = () => {
    if (deckEmpty || isTransitioning) {
      return;
    }

    if (!hasActivated) {
      setHasActivated(true);
    }

    if (visibleCard === null) {
      setVisibleCard(index);
      return;
    }

    setIsTransitioning(true);
    setVisibleCard(null);

    const nextIndex = index + 1;
    timerRef.current = window.setTimeout(() => {
      if (nextIndex < cards.length) {
        setIndex(nextIndex);
        setVisibleCard(nextIndex);
        setIsTransitioning(false);
        timerRef.current = null;
      } else {
        setIndex(cards.length);
        setDeckEmpty(true);
        setIsTransitioning(false);
        timerRef.current = window.setTimeout(() => {
          setIndex(0);
          setVisibleCard(null);
          setDeckEmpty(false);
          setHasActivated(false);
          timerRef.current = null;
        }, RESET_DELAY_MS);
      }
    }, CARD_DURATION_MS);
  };

  const handleDeckClick = () => {
    advanceDeck();
  };

  const handleCardClick = () => {
    if (visibleCard === null || isTransitioning) {
      return;
    }
    setVisibleCard(null);
  };

  const handleInstructionActivate = (event: React.MouseEvent | React.KeyboardEvent) => {
    if ("key" in event) {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }
      event.preventDefault();
    }
    advanceDeck();
  };

  const current = visibleCard !== null ? cards[visibleCard] : null;

  const stageClassName = `deck-stage${current ? " has-active-card" : ""}${hasActivated ? " deck-engaged" : ""}`;

  return (
    <SectionReveal id="product-anchor" className="deck-section">
      <div className="deck-layout">
        <div className="deck-copy">
          <h2>Layered cards, glass depth, and meaningful motion.</h2>
          <p>Information reveals itself only when requested.</p>
        </div>

        <div className="deck-interaction">
          <div className={stageClassName}>
            <button
              type="button"
              className={`card-deck${deckEmpty ? " deck-empty" : ""}`}
              onClick={handleDeckClick}
              aria-label={
                deckEmpty
                  ? "All cards withdrawn."
                  : visibleCard === null
                    ? "Withdraw next card"
                    : "Return current card to deck and withdraw the next"
              }
            >
              {deckEmpty && (
                <div className="deck-status" aria-live="polite">
                  <strong>All cards withdrawn.</strong>
                  <span>Nothing remains active.</span>
                </div>
              )}
              {!hasActivated && !deckEmpty && (
                <span className="deck-idle-label" aria-hidden="true">
                  Layered surface
                </span>
              )}
            </button>

            <AnimatePresence>
              {current && (
                <motion.article
                  key={current.title}
                  className="deck-card"
                  initial={{ y: 24 }}
                  animate={{ y: -24 }}
                  exit={{ y: 24 }}
                  transition={{ duration: CARD_DURATION, ease: [0, 0, 0.4, 1] }}
                  onClick={handleCardClick}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      handleCardClick();
                    }
                  }}
                >
                  <span>Card {visibleCard! + 1} of {cards.length}</span>
                  <strong>{current.title}</strong>
                  <p>{current.body}</p>
                </motion.article>
              )}
            </AnimatePresence>
            <button
              type="button"
              className="deck-stage-note"
              aria-label="Explore next card"
              onClick={handleInstructionActivate}
              onKeyDown={handleInstructionActivate}
            >
              Click here to Explore
            </button>
          </div>
        </div>
      </div>
    </SectionReveal>
  );
}
