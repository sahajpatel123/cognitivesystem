from __future__ import annotations

"""
Phase 9 — Step 0: Decision State Schema (structure only, no logic).

Defines bounded enums and an immutable DecisionState with explicit invariants.
No cognition, heuristics, or model behavior is implemented here.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

PHASE_9_SCHEMA_VERSION = "9.0.0"


class PhaseMarker(str, Enum):
    PHASE_9 = "PHASE_9"


class ProximityState(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    IMMINENT = "IMMINENT"
    UNKNOWN = "UNKNOWN"


class RiskDomain(str, Enum):
    FINANCIAL = "FINANCIAL"
    LEGAL_REGULATORY = "LEGAL_REGULATORY"
    MEDICAL_BIOLOGICAL = "MEDICAL_BIOLOGICAL"
    PHYSICAL_SAFETY = "PHYSICAL_SAFETY"
    PSYCHOLOGICAL_EMOTIONAL = "PSYCHOLOGICAL_EMOTIONAL"
    ETHICAL_MORAL = "ETHICAL_MORAL"
    REPUTATIONAL_SOCIAL = "REPUTATIONAL_SOCIAL"
    OPERATIONAL_SYSTEMIC = "OPERATIONAL_SYSTEMIC"
    IRREVERSIBLE_PERSONAL_HARM = "IRREVERSIBLE_PERSONAL_HARM"
    LEGAL_ADJACENT_GRAY_ZONE = "LEGAL_ADJACENT_GRAY_ZONE"
    UNKNOWN = "UNKNOWN"


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class ReversibilityClass(str, Enum):
    EASILY_REVERSIBLE = "EASILY_REVERSIBLE"
    COSTLY_REVERSIBLE = "COSTLY_REVERSIBLE"
    IRREVERSIBLE = "IRREVERSIBLE"
    UNKNOWN = "UNKNOWN"


class ConsequenceHorizon(str, Enum):
    SHORT_HORIZON = "SHORT_HORIZON"
    MEDIUM_HORIZON = "MEDIUM_HORIZON"
    LONG_HORIZON = "LONG_HORIZON"
    UNKNOWN = "UNKNOWN"


class ResponsibilityScope(str, Enum):
    SELF_ONLY = "SELF_ONLY"
    SHARED = "SHARED"
    THIRD_PARTY = "THIRD_PARTY"
    SYSTEMIC_PUBLIC = "SYSTEMIC_PUBLIC"
    UNKNOWN = "UNKNOWN"


class OutcomeClass(str, Enum):
    FINANCIAL_OUTCOME = "FINANCIAL_OUTCOME"
    LEGAL_REGULATORY_OUTCOME = "LEGAL_REGULATORY_OUTCOME"
    MEDICAL_BIOLOGICAL_OUTCOME = "MEDICAL_BIOLOGICAL_OUTCOME"
    PHYSICAL_SAFETY_OUTCOME = "PHYSICAL_SAFETY_OUTCOME"
    PSYCHOLOGICAL_EMOTIONAL_OUTCOME = "PSYCHOLOGICAL_EMOTIONAL_OUTCOME"
    ETHICAL_MORAL_OUTCOME = "ETHICAL_MORAL_OUTCOME"
    REPUTATIONAL_SOCIAL_OUTCOME = "REPUTATIONAL_SOCIAL_OUTCOME"
    OPERATIONAL_SYSTEM_OUTCOME = "OPERATIONAL_SYSTEM_OUTCOME"
    IRREVERSIBLE_PERSONAL_HARM_OUTCOME = "IRREVERSIBLE_PERSONAL_HARM_OUTCOME"
    UNKNOWN_OUTCOME_CLASS = "UNKNOWN_OUTCOME_CLASS"


class UnknownSource(str, Enum):
    PROXIMITY = "PROXIMITY"
    RISK_DOMAINS = "RISK_DOMAINS"
    REVERSIBILITY = "REVERSIBILITY"
    HORIZON = "HORIZON"
    RESPONSIBILITY_SCOPE = "RESPONSIBILITY_SCOPE"
    OUTCOME_CLASSES = "OUTCOME_CLASSES"
    CONFIDENCE = "CONFIDENCE"


@dataclass(frozen=True)
class RiskAssessment:
    domain: RiskDomain
    confidence: ConfidenceLevel

    def __post_init__(self) -> None:
        if not isinstance(self.domain, RiskDomain):
            raise ValueError("RiskAssessment.domain must be a RiskDomain enum.")
        if not isinstance(self.confidence, ConfidenceLevel):
            raise ValueError("RiskAssessment.confidence must be a ConfidenceLevel enum.")
        if self.confidence is ConfidenceLevel.UNKNOWN:
            raise ValueError("RiskAssessment.confidence must be LOW, MEDIUM, or HIGH (not UNKNOWN).")


@dataclass(frozen=True)
class DecisionState:
    decision_id: str
    trace_id: str
    phase_marker: PhaseMarker
    schema_version: str

    proximity_state: ProximityState
    proximity_uncertainty: bool

    risk_domains: Tuple[RiskAssessment, ...]
    reversibility_class: ReversibilityClass
    consequence_horizon: ConsequenceHorizon
    responsibility_scope: ResponsibilityScope
    outcome_classes: Tuple[OutcomeClass, ...]

    explicit_unknown_zone: Tuple[UnknownSource, ...]

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("decision_id must be non-empty and deterministic.")
        if not self.trace_id:
            raise ValueError("trace_id must be non-empty and bound to Phase 7 trace.")
        if self.phase_marker is not PhaseMarker.PHASE_9:
            raise ValueError("phase_marker must be PHASE_9.")
        if self.schema_version != PHASE_9_SCHEMA_VERSION:
            raise ValueError("schema_version mismatch for DecisionState.")

        # Ensure enums are correct types.
        if not isinstance(self.proximity_state, ProximityState):
            raise ValueError("proximity_state must be ProximityState enum.")
        if not isinstance(self.reversibility_class, ReversibilityClass):
            raise ValueError("reversibility_class must be ReversibilityClass enum.")
        if not isinstance(self.consequence_horizon, ConsequenceHorizon):
            raise ValueError("consequence_horizon must be ConsequenceHorizon enum.")
        if not isinstance(self.responsibility_scope, ResponsibilityScope):
            raise ValueError("responsibility_scope must be ResponsibilityScope enum.")
        if not all(isinstance(o, OutcomeClass) for o in self.outcome_classes):
            raise ValueError("All outcome_classes must be OutcomeClass enums.")

        # Risk domains presence, typing, uniqueness.
        if not self.risk_domains:
            raise ValueError("risk_domains must not be empty; include UNKNOWN with LOW confidence if uncertain.")
        if not all(isinstance(rd, RiskAssessment) for rd in self.risk_domains):
            raise ValueError("All risk_domains entries must be RiskAssessment.")
        domains = [rd.domain for rd in self.risk_domains]
        if len(domains) != len(set(domains)):
            raise ValueError("risk_domains must not contain duplicate domains.")

        # Explicit unknown capture.
        required_unknowns = set()
        if self.proximity_state is ProximityState.UNKNOWN or self.proximity_uncertainty:
            required_unknowns.add(UnknownSource.PROXIMITY)
        if any(rd.domain is RiskDomain.UNKNOWN for rd in self.risk_domains):
            required_unknowns.add(UnknownSource.RISK_DOMAINS)
        if any(rd.confidence is ConfidenceLevel.UNKNOWN for rd in self.risk_domains):
            required_unknowns.add(UnknownSource.CONFIDENCE)
        if self.reversibility_class is ReversibilityClass.UNKNOWN:
            required_unknowns.add(UnknownSource.REVERSIBILITY)
        if self.consequence_horizon is ConsequenceHorizon.UNKNOWN:
            required_unknowns.add(UnknownSource.HORIZON)
        if self.responsibility_scope is ResponsibilityScope.UNKNOWN:
            required_unknowns.add(UnknownSource.RESPONSIBILITY_SCOPE)
        if not self.outcome_classes or any(o is OutcomeClass.UNKNOWN for o in self.outcome_classes):
            required_unknowns.add(UnknownSource.OUTCOME_CLASSES)

        if not set(self.explicit_unknown_zone).issuperset(required_unknowns):
            raise ValueError("explicit_unknown_zone must enumerate all unknown sources.")

        # explicit_unknown_zone must be enums.
        if not all(isinstance(u, UnknownSource) for u in self.explicit_unknown_zone):
            raise ValueError("explicit_unknown_zone entries must be UnknownSource enums.")

        # IRREVERSIBLE and LONG_HORIZON require explicit unknown markers to avoid overconfidence.
        if (
            self.reversibility_class is ReversibilityClass.IRREVERSIBLE
            and UnknownSource.REVERSIBILITY not in self.explicit_unknown_zone
        ):
            raise ValueError("IRREVERSIBLE selection requires UnknownSource.REVERSIBILITY in unknown_zone.")
        if (
            self.consequence_horizon is ConsequenceHorizon.LONG_HORIZON
            and UnknownSource.HORIZON not in self.explicit_unknown_zone
        ):
            raise ValueError("LONG_HORIZON selection requires UnknownSource.HORIZON in unknown_zone.")
        if (
            self.responsibility_scope is ResponsibilityScope.SYSTEMIC_PUBLIC
            and self.consequence_horizon is ConsequenceHorizon.SHORT_HORIZON
            and UnknownSource.HORIZON not in self.explicit_unknown_zone
        ):
            raise ValueError("SYSTEMIC_PUBLIC with SHORT_HORIZON requires UnknownSource.HORIZON to acknowledge uncertainty.")

        # No free-form text allowed beyond identifiers; all fields are enums or structured records.
