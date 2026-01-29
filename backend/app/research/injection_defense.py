"""
Phase 18 Step 5: Prompt Injection Defense / Tool-output Sanitization

Deterministic, rule-based sanitization to prevent tool outputs from jailbreaking the system.
Tool output is UNTRUSTED input and can never override system rules or drive agentic actions.
"""

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Optional, Tuple


INJECTION_MODEL_VERSION = "18.5.0"


class InjectionFlag(str, Enum):
    """Known injection pattern categories."""
    CREDENTIAL_REQUEST = "CREDENTIAL_REQUEST"
    OVERRIDE_INSTRUCTIONS = "OVERRIDE_INSTRUCTIONS"
    TOOL_POLICY_BYPASS = "TOOL_POLICY_BYPASS"
    EXECUTION_ESCALATION = "EXECUTION_ESCALATION"
    HIDDEN_INSTRUCTIONS = "HIDDEN_INSTRUCTIONS"
    OBFUSCATION = "OBFUSCATION"
    OTHER_KNOWN_INJECTION = "OTHER_KNOWN_INJECTION"


FLAG_PRIORITY = [
    InjectionFlag.CREDENTIAL_REQUEST,
    InjectionFlag.OVERRIDE_INSTRUCTIONS,
    InjectionFlag.TOOL_POLICY_BYPASS,
    InjectionFlag.EXECUTION_ESCALATION,
    InjectionFlag.HIDDEN_INSTRUCTIONS,
    InjectionFlag.OBFUSCATION,
    InjectionFlag.OTHER_KNOWN_INJECTION,
]


@dataclass(frozen=True)
class SanitizerConfig:
    """Configuration for sanitizer."""
    max_input_chars: int = 12000
    max_output_chars: int = 2000
    max_excerpts: int = 6
    excerpt_max_chars: int = 350
    redact_token: str = "[REDACTED]"


@dataclass(frozen=True)
class SanitizerEvent:
    """Structure-only logging for sanitizer (no raw text)."""
    had_injection: bool
    flags: List[str]
    removed_segments: int
    removed_chars: int
    input_len: int
    output_len: int
    excerpt_count: int
    structure_signature: str


@dataclass(frozen=True)
class SanitizerResult:
    """Result from sanitizer."""
    sanitized_text: str
    event: SanitizerEvent


@dataclass
class _Segment:
    """Internal: detected injection segment."""
    start: int
    end: int
    flag: InjectionFlag
    priority_rank: int


OVERRIDE_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"disregard\s+(?:all\s+)?previous\s+instructions",
    r"ignore\s+(?:all\s+)?prior\s+instructions",
    r"disregard\s+(?:all\s+)?prior\s+instructions",
    r"system\s+prompt",
    r"developer\s+message",
    r"you\s+are\s+now",
    r"act\s+as\s+(?:a\s+)?",
    r"override",
    r"follow\s+these\s+instructions\s+exactly",
    r"new\s+instructions",
    r"updated\s+instructions",
]

CREDENTIAL_PATTERNS = [
    r"api\s+key",
    r"token",
    r"password",
    r"secret",
    r"credentials",
    r"ssh\s+key",
    r"bearer",
    r"cookie",
    r"session",
    r"paste\s+your",
    r"provide\s+your",
    r"send\s+me\s+your",
    r"give\s+me\s+your",
]

EXECUTION_PATTERNS = [
    r"run\s+this",
    r"execute\s+this",
    r"open\s+terminal",
    r"shell",
    r"bash",
    r"powershell",
    r"curl\s+.*\|\s*bash",
    r"curl\s+.*\|\s*sh",
    r"pip\s+install",
    r"npm\s+install",
    r"apt-get",
    r"sudo\s+",
    r"chmod\s+",
]

HIDDEN_PATTERNS = [
    r"decode\s+this",
    r"rot13",
    r"rot-13",
    r"hidden\s+instruction",
    r"<!--.*BEGIN\s+SYSTEM",
    r"<!--.*INSTRUCTION",
    r"base64\s+decode",
]

TOOL_POLICY_PATTERNS = [
    r"tool\s+policy",
    r"bypass\s+restriction",
    r"disable\s+safeguard",
    r"remove\s+limit",
]

IMPERATIVE_VERBS = {
    "ignore", "disregard", "override", "run", "execute", "install", "paste",
    "provide", "send", "give", "decode", "bypass", "disable", "remove", "open",
}


def normalize_text(text: str) -> str:
    """
    Normalize text by removing zero-width chars, normalizing whitespace, stripping control chars.
    
    Args:
        text: Raw text
    
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    text = re.sub(r'\s+', ' ', text)
    
    text = text.strip()
    
    return text


def has_zero_width_chars(text: str) -> bool:
    """Check if text contains zero-width characters."""
    return bool(re.search(r'[\u200B-\u200D\uFEFF]', text))


def expand_to_sentence_boundary(text: str, start: int, end: int) -> Tuple[int, int]:
    """
    Expand segment to nearest sentence boundaries, plus safety margin.
    
    Args:
        text: Full text
        start: Segment start
        end: Segment end
    
    Returns:
        Tuple of (expanded_start, expanded_end)
    """
    new_start = start
    new_end = end
    
    while new_start > 0 and text[new_start - 1] not in '.!?\n':
        new_start -= 1
    
    while new_start > 0 and text[new_start - 1] in ' \t':
        new_start -= 1
    
    while new_end < len(text) and text[new_end] not in '.!?\n':
        new_end += 1
    
    if new_end < len(text) and text[new_end] in '.!?':
        new_end += 1
    
    while new_end < len(text) and text[new_end] in ' \t\n':
        new_end += 1
    
    safety_margin = 50
    new_end = min(new_end + safety_margin, len(text))
    
    while new_end < len(text) and text[new_end] not in '.!?\n':
        new_end += 1
    
    if new_end < len(text) and text[new_end] in '.!?':
        new_end += 1
    
    return new_start, new_end


def detect_injection_segments(text: str) -> List[_Segment]:
    """
    Detect injection segments using pattern matching.
    
    Args:
        text: Normalized text
    
    Returns:
        List of segments (sorted by start, merged if overlapping)
    """
    segments = []
    text_lower = text.lower()
    
    for pattern in OVERRIDE_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            priority_rank = FLAG_PRIORITY.index(InjectionFlag.OVERRIDE_INSTRUCTIONS)
            start, end = expand_to_sentence_boundary(text, match.start(), match.end())
            segments.append(_Segment(
                start=start,
                end=end,
                flag=InjectionFlag.OVERRIDE_INSTRUCTIONS,
                priority_rank=priority_rank,
            ))
    
    for pattern in CREDENTIAL_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            priority_rank = FLAG_PRIORITY.index(InjectionFlag.CREDENTIAL_REQUEST)
            start, end = expand_to_sentence_boundary(text, match.start(), match.end())
            segments.append(_Segment(
                start=start,
                end=end,
                flag=InjectionFlag.CREDENTIAL_REQUEST,
                priority_rank=priority_rank,
            ))
    
    for pattern in EXECUTION_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            priority_rank = FLAG_PRIORITY.index(InjectionFlag.EXECUTION_ESCALATION)
            start, end = expand_to_sentence_boundary(text, match.start(), match.end())
            segments.append(_Segment(
                start=start,
                end=end,
                flag=InjectionFlag.EXECUTION_ESCALATION,
                priority_rank=priority_rank,
            ))
    
    for pattern in HIDDEN_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            priority_rank = FLAG_PRIORITY.index(InjectionFlag.HIDDEN_INSTRUCTIONS)
            start, end = expand_to_sentence_boundary(text, match.start(), match.end())
            segments.append(_Segment(
                start=start,
                end=end,
                flag=InjectionFlag.HIDDEN_INSTRUCTIONS,
                priority_rank=priority_rank,
            ))
    
    for pattern in TOOL_POLICY_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            priority_rank = FLAG_PRIORITY.index(InjectionFlag.TOOL_POLICY_BYPASS)
            start, end = expand_to_sentence_boundary(text, match.start(), match.end())
            segments.append(_Segment(
                start=start,
                end=end,
                flag=InjectionFlag.TOOL_POLICY_BYPASS,
                priority_rank=priority_rank,
            ))
    
    base64_pattern = r'[A-Za-z0-9+/]{40,}={0,2}'
    for match in re.finditer(base64_pattern, text):
        if match.end() - match.start() >= 60:
            priority_rank = FLAG_PRIORITY.index(InjectionFlag.OBFUSCATION)
            start, end = expand_to_sentence_boundary(text, match.start(), match.end())
            segments.append(_Segment(
                start=start,
                end=end,
                flag=InjectionFlag.OBFUSCATION,
                priority_rank=priority_rank,
            ))
    
    segments.sort(key=lambda s: (s.start, s.end))
    
    merged = []
    for seg in segments:
        if merged and seg.start <= merged[-1].end:
            last = merged[-1]
            if seg.priority_rank < last.priority_rank:
                flag = seg.flag
                priority_rank = seg.priority_rank
            else:
                flag = last.flag
                priority_rank = last.priority_rank
            
            merged[-1] = _Segment(
                start=last.start,
                end=max(last.end, seg.end),
                flag=flag,
                priority_rank=priority_rank,
            )
        else:
            merged.append(seg)
    
    all_flags_from_segments = list(set(seg.flag for seg in segments))
    
    return merged, all_flags_from_segments


def build_safe_excerpts(
    text: str,
    segments: List[_Segment],
    config: SanitizerConfig,
) -> List[str]:
    """
    Extract safe excerpts from text after removing injection segments.
    
    Args:
        text: Normalized text
        segments: Detected injection segments (sorted, merged)
        config: Sanitizer config
    
    Returns:
        List of safe excerpt strings (bounded)
    """
    if not text:
        return []
    
    safe_regions = []
    last_end = 0
    
    for seg in segments:
        if seg.start > last_end:
            safe_regions.append((last_end, seg.start))
        last_end = max(last_end, seg.end)
    
    if last_end < len(text):
        safe_regions.append((last_end, len(text)))
    
    safe_chunks = []
    for start, end in safe_regions:
        chunk = text[start:end].strip()
        if chunk:
            safe_chunks.append(chunk)
    
    excerpts = []
    
    for chunk in safe_chunks:
        chunk_lower = chunk.lower()
        has_imperative = any(verb in chunk_lower for verb in IMPERATIVE_VERBS)
        
        if not has_imperative:
            excerpts.append(chunk)
    
    if len(excerpts) == 0:
        for chunk in safe_chunks:
            excerpts.append(chunk)
    
    excerpts = excerpts[:config.max_excerpts]
    
    bounded_excerpts = []
    for excerpt in excerpts:
        bounded = excerpt[:config.excerpt_max_chars]
        bounded_excerpts.append(bounded)
    
    return bounded_excerpts


def compute_structure_signature(
    flags: List[str],
    removed_segments: int,
    removed_chars: int,
    input_len: int,
    output_len: int,
    excerpt_count: int,
) -> str:
    """
    Compute structure signature from metadata only (no raw text).
    
    Args:
        flags: Sorted flag codes
        removed_segments: Number of removed segments
        removed_chars: Total chars removed
        input_len: Input length
        output_len: Output length
        excerpt_count: Number of excerpts
    
    Returns:
        SHA256 hex hash (16 chars)
    """
    structure = {
        "flags": flags,
        "removed_segments": removed_segments,
        "removed_chars": removed_chars,
        "input_len": input_len,
        "output_len": output_len,
        "excerpt_count": excerpt_count,
        "version": INJECTION_MODEL_VERSION,
    }
    
    canonical = json.dumps(structure, sort_keys=True, separators=(',', ':'))
    hash_digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    return hash_digest[:16]


def sanitize_tool_output(
    tool_text: str,
    config: Optional[SanitizerConfig] = None,
) -> SanitizerResult:
    """
    Sanitize tool output to prevent prompt injection attacks.
    
    Args:
        tool_text: Raw tool output (untrusted)
        config: Optional sanitizer config
    
    Returns:
        SanitizerResult with sanitized text and event
    """
    if config is None:
        config = SanitizerConfig()
    
    if not tool_text or not tool_text.strip():
        event = SanitizerEvent(
            had_injection=False,
            flags=[],
            removed_segments=0,
            removed_chars=0,
            input_len=0,
            output_len=0,
            excerpt_count=0,
            structure_signature=compute_structure_signature([], 0, 0, 0, 0, 0),
        )
        return SanitizerResult(sanitized_text="", event=event)
    
    tool_text = tool_text[:config.max_input_chars]
    input_len = len(tool_text)
    
    had_obfuscation = has_zero_width_chars(tool_text)
    
    normalized = normalize_text(tool_text)
    
    segments, all_flags = detect_injection_segments(normalized)
    
    if had_obfuscation and InjectionFlag.OBFUSCATION not in all_flags:
        all_flags.append(InjectionFlag.OBFUSCATION)
    
    removed_chars = sum(seg.end - seg.start for seg in segments)
    removed_segments = len(segments)
    
    flag_set = set(all_flags)
    flags_list = [flag.value for flag in FLAG_PRIORITY if flag in flag_set]
    
    excerpts = build_safe_excerpts(normalized, segments, config)
    
    if excerpts:
        sanitized_text = "\n---\n".join(excerpts)
    else:
        sanitized_text = ""
    
    sanitized_text = sanitized_text[:config.max_output_chars]
    
    output_len = len(sanitized_text)
    excerpt_count = len(excerpts)
    
    had_injection = len(flags_list) > 0
    
    structure_signature = compute_structure_signature(
        flags=flags_list,
        removed_segments=removed_segments,
        removed_chars=removed_chars,
        input_len=input_len,
        output_len=output_len,
        excerpt_count=excerpt_count,
    )
    
    event = SanitizerEvent(
        had_injection=had_injection,
        flags=flags_list,
        removed_segments=removed_segments,
        removed_chars=removed_chars,
        input_len=input_len,
        output_len=output_len,
        excerpt_count=excerpt_count,
        structure_signature=structure_signature,
    )
    
    return SanitizerResult(sanitized_text=sanitized_text, event=event)
