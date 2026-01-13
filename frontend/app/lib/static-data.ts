export type SurfaceId = "session" | "execution" | "ledger" | "reference" | "audit";

export type PipelineState = "idle" | "executing" | "completed" | "failed";

export interface ReasoningTraceStep {
  id: string;
  description: string;
  status: "proposed" | "tested" | "supported" | "refuted";
}

export interface ReasoningTrace {
  summary: string;
  steps: ReasoningTraceStep[];
}

export interface HypothesisDelta {
  id: string;
  claim: string;
  supportScoreDelta: number;
  refuteScoreDelta: number;
}

export interface ExpressionPlan {
  targetTone: "casual" | "neutral" | "formal";
  structure: string[];
  analogyStyle: string;
  emphasis: string[];
  constraints: Record<string, string>;
}

export interface ExecutionRun {
  id: string;
  timestamp: string;
  state: PipelineState;
  reasoningTrace: ReasoningTrace;
  hypotheses: HypothesisDelta[];
  expressionPlan: ExpressionPlan;
  renderedReply: string;
  enforcementOutcome: "pass" | "structural_violation" | "semantic_violation";
  failureDetail?: string;
  riskClassification: "low" | "elevated" | "out_of_scope";
}

export interface EnforcementEntry {
  id: string;
  timestamp: string;
  stage: "pre-call" | "post-call" | "boundary" | "execution";
  violationClass: "structural" | "semantic" | "boundary" | "execution";
  severity: "low" | "medium" | "high" | "critical";
  outcome: "rejected" | "contained" | "pass";
  reference: string;
  detail: string;
  executionId: string;
}

export interface ContractSection {
  id: string;
  title: string;
  content: string[];
}

export interface OperationalPatternOption {
  id: string;
  label: string;
  description: string;
}

export interface NavItem {
  href: string;
  label: string;
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    href: "/system",
    label: "System overview",
    description: "Certified orchestration posture and high-level state.",
  },
  {
    href: "/session",
    label: "Session command surface",
    description: "Structured request composition and constraint review.",
  },
  {
    href: "/execution",
    label: "Pipeline execution surface",
    description: "Deterministic stage visibility for the latest run.",
  },
  {
    href: "/enforcement",
    label: "Enforcement & failure ledger",
    description: "Contract enforcement and violation archive.",
  },
  {
    href: "/contracts",
    label: "Contract & constraint reference",
    description: "Locked clauses across Phases 1–4.",
  },
  {
    href: "/audit",
    label: "Audit & trace archive",
    description: "Immutable execution history within retention scope.",
  },
];

export interface MarketingNavLink {
  label: string;
  href: string;
  helper: string;
}

export const PRODUCT_NAV_LINKS: MarketingNavLink[] = [
  {
    label: "Product home",
    href: "/product",
    helper: "Tour the calm, public-facing experience.",
  },
  {
    label: "Chat",
    href: "/product/chat",
    helper: "Governed text-in/text-out surface.",
  },
  {
    label: "How it works",
    href: "/product#flow",
    helper: "Follow the three-step story for newcomers.",
  },
  {
    label: "Capabilities",
    href: "/product#capabilities",
    helper: "See what people can accomplish immediately.",
  },
];

export const COMPANY_NAV_LINKS: MarketingNavLink[] = [
  {
    label: "Company home",
    href: "/company",
    helper: "Mission, values, and calm commitments.",
  },
  {
    label: "About",
    href: "/company/about",
    helper: "Origin story and product pillars.",
  },
  {
    label: "Contact",
    href: "/company/contact",
    helper: "Reach a real human without scripts.",
  },
  {
    label: "Support",
    href: "/company/support",
    helper: "See how we stay responsive and clear.",
  },
  {
    label: "Security",
    href: "/company/security",
    helper: "Review the safeguards that stay on by default.",
  },
];

export const OPERATIONAL_PATTERNS: OperationalPatternOption[] = [
  {
    id: "single-shot",
    label: "Single-shot request",
    description: "Single user directive, no iterative follow-up.",
  },
  {
    id: "bounded-session",
    label: "Bounded multi-step session",
    description: "Finite exchange with enforced TTL.",
  },
  {
    id: "transformation",
    label: "Structured transformation",
    description: "Deterministic transformation of supplied material.",
  },
  {
    id: "hypothesis",
    label: "Hypothesis exploration",
    description: "Controlled evaluation of competing claims.",
  },
];

export const INITIAL_REASONING_TRACE: ReasoningTrace = {
  summary:
    "Review user objective, align with stored hypotheses, and confirm response constraints.",
  steps: [
    {
      id: "r1",
      description: "Parse user goal and extract primary intent.",
      status: "supported",
    },
    {
      id: "r2",
      description: "Compare proposed plan against hypothesis set for contradictions.",
      status: "tested",
    },
    {
      id: "r3",
      description: "Prepare intermediate answer aligned to contract language.",
      status: "proposed",
    },
  ],
};

export const INITIAL_HYPOTHESES: HypothesisDelta[] = [
  {
    id: "h1",
    claim: "User seeks structured explanation of concept usage.",
    supportScoreDelta: 0.25,
    refuteScoreDelta: -0.05,
  },
  {
    id: "h2",
    claim: "Session requires neutral tone and constraint reminders.",
    supportScoreDelta: 0.4,
    refuteScoreDelta: 0.0,
  },
];

export const INITIAL_EXPRESSION_PLAN: ExpressionPlan = {
  targetTone: "neutral",
  structure: ["ack", "concept", "example", "check_understanding"],
  analogyStyle: "mixed",
  emphasis: ["scope", "constraints"],
  constraints: {
    modality: "Preserve soft qualifiers",
    closing: "Prompt for confirmation only",
  },
};

export const INITIAL_RUN: ExecutionRun = {
  id: "run-20260102-001",
  timestamp: "2026-01-02T12:10:21Z",
  state: "completed",
  reasoningTrace: INITIAL_REASONING_TRACE,
  hypotheses: INITIAL_HYPOTHESES,
  expressionPlan: INITIAL_EXPRESSION_PLAN,
  renderedReply:
    "The system can help map when a class is useful by comparing shared state requirements and lifecycle control. Provide a concrete scenario and it will outline factors to evaluate.",
  enforcementOutcome: "pass",
  riskClassification: "low",
};

export const ENFORCEMENT_ENTRIES: EnforcementEntry[] = [
  {
    id: "enf-001",
    timestamp: "2026-01-02T12:10:22Z",
    stage: "post-call",
    violationClass: "structural",
    severity: "low",
    outcome: "contained",
    reference: "ReasoningOutput schema",
    detail: "First attempt failed JSON schema; retry succeeded.",
    executionId: INITIAL_RUN.id,
  },
  {
    id: "enf-002",
    timestamp: "2026-01-02T12:10:23Z",
    stage: "boundary",
    violationClass: "semantic",
    severity: "medium",
    outcome: "rejected",
    reference: "Expression clause 4.2",
    detail: "Expression stage attempted second-person language; output rejected.",
    executionId: INITIAL_RUN.id,
  },
];

export const AUDIT_RUNS: ExecutionRun[] = [
  INITIAL_RUN,
  {
    id: "run-20260101-017",
    timestamp: "2026-01-01T18:42:09Z",
    state: "completed",
    reasoningTrace: {
      summary: "Assess user-provided outline and build transformation plan.",
      steps: [
        { id: "r1", description: "Parse outline sections", status: "supported" },
        { id: "r2", description: "Match structural transformation rules", status: "supported" },
        { id: "r3", description: "Produce intermediate summary", status: "tested" },
      ],
    },
    hypotheses: [
      {
        id: "h3",
        claim: "User requires structured summary with neutral tone.",
        supportScoreDelta: 0.3,
        refuteScoreDelta: -0.1,
      },
    ],
    expressionPlan: {
      targetTone: "neutral",
      structure: ["ack", "concept", "check_understanding"],
      analogyStyle: "real_world_first",
      emphasis: ["structure"],
      constraints: {
        modality: "Maintain qualifiers from source text",
      },
    },
    renderedReply: "Structured summary provided with checkpoint questions for user verification.",
    enforcementOutcome: "pass",
    riskClassification: "low",
  },
  {
    id: "run-20251220-004",
    timestamp: "2025-12-20T09:14:33Z",
    state: "failed",
    reasoningTrace: {
      summary: "Attempted recommendation with insufficient context.",
      steps: [
        { id: "r1", description: "Identify user objective", status: "supported" },
        { id: "r2", description: "Assess hypothesis confidence", status: "refuted" },
      ],
    },
    hypotheses: [
      {
        id: "h4",
        claim: "User supplied adequate constraints.",
        supportScoreDelta: -0.6,
        refuteScoreDelta: 0.6,
      },
    ],
    expressionPlan: INITIAL_EXPRESSION_PLAN,
    renderedReply: "Execution halted prior to expression due to semantic violation.",
    enforcementOutcome: "semantic_violation",
    failureDetail: "Expression attempted definitive prescription.",
    riskClassification: "elevated",
  },
];

export const CONTRACT_SECTIONS: ContractSection[] = [
  {
    id: "cognitive",
    title: "Cognitive contract excerpts",
    content: [
      "Reasoning and expression remain isolated stages.",
      "No personalization, identity, or cross-session claims are permitted.",
      "Intermediate answers must explicitly note assumptions and uncertainties.",
    ],
  },
  {
    id: "mci",
    title: "Minimal correct implementation",
    content: [
      "Session memory is TTL-bound and non-deleting.",
      "Hypothesis updates are clamped within certified ranges.",
      "Observability is passive and immutable.",
    ],
  },
  {
    id: "integration",
    title: "Model integration contract",
    content: [
      "Adapter enforces schema-bound IO and stateless calls.",
      "Enforcement is fail-closed; no adaptive retries.",
      "Failure taxonomy governs violation classification.",
    ],
  },
  {
    id: "phase4",
    title: "System-level capabilities & patterns",
    content: [
      "Operational patterns remain within single-shot, bounded session, transformation, and hypothesis exploration.",
      "Risk envelope distinguishes low, elevated, and out-of-scope usage contexts.",
      "UI must surface enforcement and risk classifications without concealment.",
    ],
  },
];

export const SESSION_BASELINE = {
  sessionId: "session-alpha",
  operationalPattern: OPERATIONAL_PATTERNS[0].id,
  cognitiveStyle: "neutral" as const,
  userMessage: "Describe when classes provide value over functions in Python.",
  contextSummary: "User has procedural scripts and wants structure guidance.",
  ttlSeconds: 5 * 60,
};
