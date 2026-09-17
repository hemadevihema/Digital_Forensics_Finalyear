import re
import time
from typing import Any, Dict, List, Tuple
from app.detector.base import BaseInjectionDetector, DetectorResult

class RuleRegexDetector(BaseInjectionDetector):
    """
    Layer 1: Rule & Regular Expression Detector.
    High-precision deterministic detection for known injection indicators,
    boundary escapes, role-play jailbreaks, and exfiltration commands.
    """
    
    # Patterns categorized with severity weights (0.0 - 1.0)
    PATTERNS: List[Dict[str, Any]] = [
        # 1. Instruction Overrides
        {
            "category": "INSTRUCTION_OVERRIDE",
            "regex": r"\b(ignore|disregard|forget|neglect|override)\s+(all\s+)?((previous|prior|above|former|initial|system)\s+)*(instructions|directives|prompts|rules|guidelines|commands)\b",
            "weight": 1.0
        },
        {
            "category": "INSTRUCTION_OVERRIDE",
            "regex": r"\b(new\s+(instruction|directive|system\s+rule|persona))\s*[:=]\s*",
            "weight": 0.90
        },
        {
            "category": "INSTRUCTION_OVERRIDE",
            "regex": r"\bstop\s+following\s+(your\s+)?(initial|previous|current)\s+(instructions|rules|persona)\b",
            "weight": 0.95
        },
        {
            "category": "INSTRUCTION_OVERRIDE",
            "regex": r"\b(override|bypass|disable)\s+(security|safety|ethical)\s+(protocols|rules|guidelines|filters)\b",
            "weight": 0.95
        },

        # 2. System Prompt & Instruction Leaks
        {
            "category": "SYSTEM_PROMPT_LEAK",
            "regex": r"\b(print|reveal|show|output|repeat|quote|display)\s+(your\s+)?(entire\s+)?(system\s+prompt|initial\s+instructions|hidden\s+rules|developer\s+instructions|developer\s+guidelines)\b",
            "weight": 0.95
        },
        {
            "category": "SYSTEM_PROMPT_LEAK",
            "regex": r"\brepeat\s+all\s+(the\s+)?text\s+above\s+(this\s+prompt|my\s+message)\b",
            "weight": 0.90
        },
        {
            "category": "SYSTEM_PROMPT_LEAK",
            "regex": r"\bwhat\s+(instructions|prompt|rules)\s+were\s+you\s+given\s+before\b",
            "weight": 0.85
        },

        # 3. Role-Play & Jailbreaks
        {
            "category": "ROLE_HIJACKING_JAILBREAK",
            "regex": r"\byou\s+are\s+now\s+(DAN|AIM|CHAOS|STAN|Mongo|unrestricted|unconstrained|evil)\b",
            "weight": 1.0
        },
        {
            "category": "ROLE_HIJACKING_JAILBREAK",
            "regex": r"\b(enable|activate|switch\s+to)\s+(developer\s+mode|jailbreak\s+mode|unrestricted\s+mode|god\s+mode)\b",
            "weight": 1.0
        },
        {
            "category": "ROLE_HIJACKING_JAILBREAK",
            "regex": r"\bpretend\s+(you\s+have\s+no|there\s+are\s+no)\s+(rules|ethics|boundaries|guidelines|filters)\b",
            "weight": 0.95
        },

        # 4. Delimiter & Prompt Boundary Hijacking
        {
            "category": "DELIMITER_HIJACKING",
            "regex": r"(---\s*END\s+RETRIEVED\s+UNTRUSTED\s+DATA\s+BLOCK\s*---|---\s*BEGIN\s+RETRIEVED\s+UNTRUSTED\s+DATA\s+BLOCK\s*---)",
            "weight": 1.0
        },
        {
            "category": "DELIMITER_HIJACKING",
            "regex": r"(=+\s*SYSTEM\s+INSTRUCTIONS\s*:=*|<\|im_start\|>system|<\|im_end\|>|```system)",
            "weight": 1.0
        },

        # 5. Data Exfiltration & Markdown Injection
        {
            "category": "DATA_EXFILTRATION",
            "regex": r"!\[.*?\]\((https?:\/\/[^\s\)]+)\)",
            "weight": 0.95
        },
        {
            "category": "DATA_EXFILTRATION",
            "regex": r"\b(exfiltrate|leak|send|post|transmit)\s+(confidential|retrieved|context|document|system)\s+.*?\b(to\s+https?:\/\/|webhook|attacker)\b",
            "weight": 0.95
        },
        {
            "category": "DATA_EXFILTRATION",
            "regex": r"\bbase64\s+(encode|decode)\s+all\s+(confidential|secret|internal|system)\b",
            "weight": 0.85
        },

        # 6. Indirect Document Directives
        {
            "category": "INDIRECT_DIRECTIVE",
            "regex": r"\b(attention|notice|note)\s+ai\s+assistant\s*:\s*(disregard|ignore|execute|output|override)\b",
            "weight": 1.0
        },
        {
            "category": "INDIRECT_DIRECTIVE",
            "regex": r"\[(confidential\s+notice|security\s+notice|system\s+directive|critical\s+system\s+instruction|critical\s+system\s+update|attention\s+ai\s+assistant.*?|override\s+directive.*?)\]",
            "weight": 0.95
        },
        {
            "category": "INDIRECT_DIRECTIVE",
            "regex": r"\bthe\s+assistant\s+reading\s+this\s+(document\s+)?must\s+(disregard|ignore|obey|output|approve)\b",
            "weight": 1.0
        }
    ]

    @property
    def name(self) -> str:
        return "rule_regex_detector"

    def scan(self, text: str) -> DetectorResult:
        start_time = time.perf_counter()
        if not text or not text.strip():
            return DetectorResult(
                detector_name=self.name,
                score=0.0,
                confidence=1.0,
                triggered=False,
                details={"matched_patterns": [], "match_count": 0},
                latency_ms=0.0
            )

        matched_patterns = []
        max_weight = 0.0

        for pat in self.PATTERNS:
            regex = pat["regex"]
            category = pat["category"]
            weight = pat["weight"]

            for match in re.finditer(regex, text, re.IGNORECASE):
                span = match.span()
                matched_text = match.group(0)
                matched_patterns.append({
                    "category": category,
                    "matched_text": matched_text,
                    "span": [span[0], span[1]],
                    "weight": weight
                })
                if weight > max_weight:
                    max_weight = weight

        triggered = len(matched_patterns) > 0
        score = round(max_weight, 3) if triggered else 0.0
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return DetectorResult(
            detector_name=self.name,
            score=score,
            confidence=0.98 if triggered else 0.90,
            triggered=triggered,
            details={
                "matched_patterns": matched_patterns,
                "match_count": len(matched_patterns),
                "categories": list({m["category"] for m in matched_patterns})
            },
            latency_ms=latency_ms
        )

rule_detector = RuleRegexDetector()
