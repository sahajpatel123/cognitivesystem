from enum import Enum, auto


class PhaseStep(Enum):
    """Ordered reference to Phase 4–6 steps for trace markers."""

    PHASE4_STEP0 = auto()
    PHASE4_STEP1 = auto()
    PHASE4_STEP2 = auto()
    PHASE4_STEP3 = auto()
    PHASE4_STEP4 = auto()
    PHASE5_STEP0 = auto()
    PHASE5_STEP1 = auto()
    PHASE5_STEP2 = auto()
    PHASE5_STEP3 = auto()
    PHASE5_STEP4 = auto()
    PHASE5_STEP5 = auto()
    PHASE6_STEP0 = auto()
    PHASE6_STEP1 = auto()
    PHASE6_STEP2 = auto()
    PHASE6_STEP3 = auto()
    PHASE6_STEP4 = auto()
    PHASE6_STEP5 = auto()


class TraceLifecycleStatus(Enum):
    STARTED = auto()
    COMPLETED = auto()
    ABORTED = auto()


class DecisionCategory(Enum):
    """Aligned with Phase 4 Step 0 intent taxonomy."""

    INFORMATIONAL = auto()
    EXPLORATORY = auto()
    ADVISORY = auto()
    DECISION_ADJACENT = auto()
    DECISION_IMMINENT = auto()
    UNSPECIFIED = auto()


class RuleKey(Enum):
    """Bounded rule identifiers aligned with existing invariants."""

    REQUEST_BOUNDARY = auto()
    REASONING_ISOLATION = auto()
    MEMORY_UPDATE = auto()
    EXPRESSION_NON_EMPTY = auto()


class BoundaryKey(Enum):
    """Bounded boundary identifiers for activation evidence."""

    REFUSAL = auto()
    CLOSURE = auto()
    CLARIFICATION_EXHAUSTION = auto()
    GATING_SUPPRESSION = auto()


class RuleEvidenceOutcome(Enum):
    CHECKED = auto()
    PASS = auto()
    FAIL = auto()
    NOT_APPLICABLE = auto()


class BoundaryActivationType(Enum):
    REFUSAL = auto()
    CLOSURE = auto()
    CLARIFICATION_EXHAUSTION = auto()
    GATING_SUPPRESSION = auto()


class FailureOrigin(Enum):
    RULE_ENFORCEMENT = auto()
    BOUNDARY_ACTIVATION = auto()
    SYSTEM_LOGIC = auto()
    EXTERNAL_DEPENDENCY = auto()
    OUT_OF_SCOPE = auto()


class FailureType(Enum):
    OMISSION = auto()
    COMMISSION = auto()
    MISCLASSIFICATION = auto()
    INCONSISTENCY = auto()
    AMBIGUITY_EXPOSURE = auto()


class AccountabilityClass(Enum):
    WITHIN_GUARANTEES = auto()
    OUTSIDE_GUARANTEES = auto()
    EXPLICITLY_EXCLUDED = auto()


class AuditOutcome(Enum):
    PASS = auto()
    FAIL_MISSING_EVIDENCE = auto()
    FAIL_INCONSISTENCY = auto()
    INCONCLUSIVE = auto()


class OutcomeDomain(Enum):
    """Outcome domains align with Phase 4 Step 2 categories."""

    FINANCIAL = auto()
    LEGAL_REGULATORY = auto()
    MEDICAL_BIOLOGICAL = auto()
    OPERATIONAL_PHYSICAL = auto()
    PSYCHOLOGICAL_EMOTIONAL = auto()
    ETHICAL_MORAL = auto()
    REPUTATIONAL_SOCIAL = auto()
    IRREVERSIBLE_PERSONAL_HARM = auto()
    LEGAL_ADJACENT_GRAY = auto()
