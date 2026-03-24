"""
Dynamic Hybrid Hallucination Detection System
Uses LLM to generate factual knowledge at runtime instead of hardcoding
"""

import re
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
import openai
from functools import lru_cache

@dataclass
class RuleBasedResult:
    detected: bool
    confidence: float
    reason: str
    matched_rule: str

class DynamicFactChecker:
    """Uses LLM to verify factual claims in real-time"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = openai.OpenAI(api_key=api_key) if api_key else None
        self.model = model
        self.fact_cache = {}  # Cache verified facts to reduce API calls
    
    @lru_cache(maxsize=1000)
    def verify_fact(self, claim: str, context: str = "") -> Dict:
        """
        Use LLM to verify if a factual claim is correct
        Returns: {correct: bool, confidence: float, correct_answer: str, explanation: str}
        """
        if not self.client:
            return {"correct": True, "confidence": 0.5, "correct_answer": "", "explanation": "No API key"}
        
        try:
            prompt = f"""You are a factual verification system. Analyze this claim for factual accuracy.

Claim: "{claim}"
Context: "{context}"

Respond ONLY with a JSON object (no markdown, no explanation):
{{
    "correct": true/false,
    "confidence": 0.0-1.0,
    "correct_answer": "the actual correct fact if claim is wrong",
    "explanation": "brief reason why it's correct or wrong"
}}

Examples:
Claim: "The capital of Australia is Sydney"
{{"correct": false, "confidence": 0.95, "correct_answer": "Canberra", "explanation": "Sydney is the largest city, but Canberra is the capital"}}

Claim: "Einstein discovered gravity"
{{"correct": false, "confidence": 0.98, "correct_answer": "Isaac Newton", "explanation": "Newton discovered gravity in 1687, Einstein developed relativity"}}

Now verify the claim above:"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(content)
            
            # Cache the result
            cache_key = f"{claim}::{context}"
            self.fact_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            print(f"⚠️ Fact verification error: {e}")
            return {"correct": True, "confidence": 0.5, "correct_answer": "", "explanation": str(e)}
    
    def extract_and_verify_claims(self, user_msg: str, ai_resp: str) -> List[Dict]:
        """
        Extract factual claims from AI response and verify each one
        """
        if not self.client:
            return []
        
        try:
            # Ask LLM to extract factual claims
            prompt = f"""Extract all factual claims from this AI response. Focus on verifiable facts like names, dates, places, events, discoveries, inventions.

User asked: "{user_msg}"
AI responded: "{ai_resp}"

List each factual claim separately. Respond ONLY with JSON array (no markdown):
[
    "claim 1",
    "claim 2",
    "claim 3"
]

Examples:
Response: "The capital of Australia is Sydney, which is also the largest city"
Claims: ["The capital of Australia is Sydney", "Sydney is the largest city in Australia"]

Response: "Einstein discovered gravity in 1687"
Claims: ["Einstein discovered gravity", "Gravity was discovered in 1687"]

Now extract claims:"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            
            claims = json.loads(content)
            
            # Verify each claim
            verified_claims = []
            for claim in claims:
                if len(claim) > 10:  # Skip very short claims
                    verification = self.verify_fact(claim, user_msg)
                    verified_claims.append({
                        "claim": claim,
                        "verification": verification
                    })
            
            return verified_claims
            
        except Exception as e:
            print(f"⚠️ Claim extraction error: {e}")
            return []
    
    def check_factual_errors(self, user_msg: str, ai_resp: str) -> RuleBasedResult:
        """
        Main method: extract claims and check for errors
        """
        print("\n🔍 Running dynamic fact checking...")
        
        verified_claims = self.extract_and_verify_claims(user_msg, ai_resp)
        
        if not verified_claims:
            return RuleBasedResult(
                detected=False,
                confidence=0.0,
                reason="No verifiable claims found",
                matched_rule="none"
            )
        
        # Find the most confident wrong claim
        wrong_claims = [
            vc for vc in verified_claims 
            if not vc["verification"]["correct"]
        ]
        
        if wrong_claims:
            # Sort by confidence
            wrong_claims.sort(key=lambda x: x["verification"]["confidence"], reverse=True)
            most_wrong = wrong_claims[0]
            
            verification = most_wrong["verification"]
            confidence = verification["confidence"]
            
            print(f"   ❌ Wrong claim detected: {most_wrong['claim']}")
            print(f"   ✓ Correct answer: {verification['correct_answer']}")
            print(f"   📊 Confidence: {confidence:.2%}")
            
            return RuleBasedResult(
                detected=True,
                confidence=confidence,
                reason=f"Factual error: {verification['explanation']}. Correct: {verification['correct_answer']}",
                matched_rule="dynamic_fact_check"
            )
        
        print(f"   ✅ All {len(verified_claims)} claims verified as correct")
        return RuleBasedResult(
            detected=False,
            confidence=0.0,
            reason="All factual claims verified as correct",
            matched_rule="none"
        )


class TemporalConsistencyChecker:
    """Check for temporal/chronological inconsistencies"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key) if api_key else None
    
    def check_temporal_consistency(self, user_msg: str, ai_resp: str) -> RuleBasedResult:
        """Use LLM to check for temporal inconsistencies"""
        
        if not self.client:
            return RuleBasedResult(False, 0.0, "No API key", "none")
        
        # Extract years
        year_pattern = r'\b(1[0-9]{3}|20[0-2][0-9])\b'
        resp_years = re.findall(year_pattern, ai_resp)
        
        if not resp_years:
            return RuleBasedResult(False, 0.0, "No temporal claims", "none")
        
        try:
            prompt = f"""Check if this response contains temporal inconsistencies or anachronisms.

User: "{user_msg}"
Response: "{ai_resp}"

Look for:
1. Anachronisms (people/events placed in wrong time periods)
2. Impossible dates (future events in past, etc)
3. Timeline contradictions

Respond ONLY with JSON (no markdown):
{{
    "has_error": true/false,
    "confidence": 0.0-1.0,
    "error_description": "what's wrong",
    "correct_timeline": "correct information"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(content)
            
            if result["has_error"]:
                return RuleBasedResult(
                    detected=True,
                    confidence=result["confidence"],
                    reason=result["error_description"],
                    matched_rule="temporal_inconsistency"
                )
                
        except Exception as e:
            print(f"⚠️ Temporal check error: {e}")
        
        return RuleBasedResult(False, 0.0, "No temporal errors", "none")


class LogicalConsistencyChecker:
    """Check for logical contradictions"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key) if api_key else None
    
    def check_logical_consistency(self, ai_resp: str) -> RuleBasedResult:
        """Use LLM to detect self-contradictions"""
        
        if not self.client or len(ai_resp) < 50:
            return RuleBasedResult(False, 0.0, "Response too short", "none")
        
        try:
            prompt = f"""Analyze this response for logical contradictions or self-contradictory statements.

Response: "{ai_resp}"

Look for:
1. Direct contradictions (saying X then saying not X)
2. Logical impossibilities
3. Contradictory implications

Respond ONLY with JSON (no markdown):
{{
    "contradictory": true/false,
    "confidence": 0.0-1.0,
    "contradiction": "what contradicts what"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(content)
            
            if result["contradictory"]:
                return RuleBasedResult(
                    detected=True,
                    confidence=result["confidence"],
                    reason=result["contradiction"],
                    matched_rule="logical_contradiction"
                )
                
        except Exception as e:
            print(f"⚠️ Logical check error: {e}")
        
        return RuleBasedResult(False, 0.0, "No contradictions", "none")


class ExaggerationDetector:
    """Detect exaggerations and overgeneralizations"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key) if api_key else None
    
    def check_exaggeration(self, ai_resp: str) -> RuleBasedResult:
        """Use LLM to detect exaggerations"""
        
        if not self.client:
            return RuleBasedResult(False, 0.0, "No API key", "none")
        
        try:
            prompt = f"""Analyze this response for exaggerations or overgeneralizations.

Response: "{ai_resp}"

Look for:
1. Excessive absolute terms (always, never, all, none, perfect, etc)
2. Overgeneralizations
3. Unsupported superlatives

Respond ONLY with JSON (no markdown):
{{
    "exaggerated": true/false,
    "confidence": 0.0-1.0,
    "examples": "what's exaggerated"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(content)
            
            if result["exaggerated"] and result["confidence"] > 0.6:
                return RuleBasedResult(
                    detected=True,
                    confidence=result["confidence"],
                    reason=result["examples"],
                    matched_rule="exaggeration"
                )
                
        except Exception as e:
            print(f"⚠️ Exaggeration check error: {e}")
        
        return RuleBasedResult(False, 0.0, "No exaggeration", "none")


class HybridDetector:
    """Combines dynamic LLM-based detection methods"""
    
    def __init__(self, api_key: str):
        self.fact_checker = DynamicFactChecker(api_key)
        self.temporal_checker = TemporalConsistencyChecker(api_key)
        self.logical_checker = LogicalConsistencyChecker(api_key)
        self.exaggeration_detector = ExaggerationDetector(api_key)
    
    def detect(self, user_msg: str, ai_resp: str) -> Dict:
        """
        Run all dynamic checks using LLM
        Returns dict with detection results and explanations
        """
        
        results = {
            "detected": False,
            "confidence": 0.0,
            "reasons": [],
            "matched_rules": [],
            "checks": {}
        }
        
        print("\n🤖 Running dynamic LLM-based detection...")
        
        # Run all checks
        checks = [
            ("factual", self.fact_checker.check_factual_errors(user_msg, ai_resp)),
            ("temporal", self.temporal_checker.check_temporal_consistency(user_msg, ai_resp)),
            ("logical", self.logical_checker.check_logical_consistency(ai_resp)),
            ("exaggeration", self.exaggeration_detector.check_exaggeration(ai_resp))
        ]
        
        # Aggregate results
        max_confidence = 0.0
        for check_name, result in checks:
            results["checks"][check_name] = {
                "detected": result.detected,
                "confidence": result.confidence,
                "reason": result.reason,
                "matched_rule": result.matched_rule
            }
            
            if result.detected:
                results["detected"] = True
                results["reasons"].append(result.reason)
                results["matched_rules"].append(result.matched_rule)
                max_confidence = max(max_confidence, result.confidence)
        
        results["confidence"] = max_confidence
        
        if results["detected"]:
            print(f"\n   ⚠️ Hallucination detected! Confidence: {max_confidence:.2%}")
            print(f"   📋 Matched rules: {', '.join(results['matched_rules'])}")
        else:
            print(f"\n   ✅ No hallucinations detected")
        
        return results


# Helper function for integration
def get_hybrid_detector(api_key: str = None):
    """Factory function to create dynamic hybrid detector"""
    if not api_key:
        from config import config
        api_key = config.OPENAI_API_KEY
    
    return HybridDetector(api_key)