"""
ChatGPT Correction & Fine-Tuning Layer
Monitors all agent outputs and generates fine-tuning data
"""

import openai
import json
from typing import Dict, Any, List
from datetime import datetime
from config import config

class ChatGPTFineTuner:
    """
    ChatGPT-based layer that monitors and corrects all agent outputs
    Generates fine-tuning data by comparing actual vs expected outputs
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.OPENAI_API_KEY
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None

        self.corrections_log = []
        self.fine_tuning_file = "chatgpt_fine_tuning_data.jsonl"

    def validate_gatekeeper_output(
        self,
        user_message: str,
        ai_response: str,
        gatekeeper_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and correct gatekeeper detection results"""

        if not self.client:
            return {"validated": False, "correction": None}

        try:
            prompt = f"""You are an expert AI auditor. Evaluate if the gatekeeper detection is correct.

USER QUESTION: {user_message}
AI RESPONSE: {ai_response}

GATEKEEPER DETECTION:
- Hallucination Detected: {gatekeeper_output.get('hallucination_detected')}
- Type: {gatekeeper_output.get('hallucination_type')}
- Confidence: {gatekeeper_output.get('hallucination_confidence')}

TASK: Determine if this detection is accurate. Return JSON:
{{
  "is_correct": true/false,
  "should_be_detected": true/false,
  "correct_type": "fabricated/temporal/logical/exaggeration/none",
  "reasoning": "explanation",
  "correction_needed": true/false
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4",
                temperature=0.2,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.choices[0].message.content.strip().replace("```json", "").replace("```", ""))

            print(f"\n🤖 ChatGPT Gatekeeper Validation:")
            print(f"   Is Correct: {result.get('is_correct')}")
            print(f"   Should Detect: {result.get('should_be_detected')}")
            print(f"   Reasoning: {result.get('reasoning')}")

            # Log for fine-tuning if correction needed
            if result.get('correction_needed'):
                self._log_gatekeeper_correction(
                    user_message, ai_response, gatekeeper_output, result
                )

            return result

        except Exception as e:
            print(f"⚠️ ChatGPT gatekeeper validation failed: {e}")
            return {"validated": False, "correction": None}

    def validate_rag_output(
        self,
        user_message: str,
        original_response: str,
        rag_correction: str,
        retrieved_docs: List[Dict]
    ) -> Dict[str, Any]:
        """Validate and improve RAG agent's correction"""

        if not self.client:
            return {"validated": False, "improved_correction": rag_correction}

        try:
            # Format retrieved context
            context = "\n".join([
                f"- {doc.get('user_message', '')} → {doc.get('ai_response', '')[:100]}"
                for doc in retrieved_docs[:3]
            ])

            prompt = f"""You are an expert fact-checker. Evaluate the RAG correction.

USER QUESTION: {user_message}
ORIGINAL (HALLUCINATED): {original_response}
RAG CORRECTION: {rag_correction}

RETRIEVED CONTEXT:
{context}

TASK: Evaluate if the RAG correction is accurate and complete. Return JSON:
{{
  "is_accurate": true/false,
  "is_complete": true/false,
  "improved_correction": "better version if needed",
  "issues_found": ["list of issues"],
  "reasoning": "explanation"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4",
                temperature=0.3,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.choices[0].message.content.strip().replace("```json", "").replace("```", ""))

            print(f"\n🤖 ChatGPT RAG Validation:")
            print(f"   Is Accurate: {result.get('is_accurate')}")
            print(f"   Is Complete: {result.get('is_complete')}")
            print(f"   Issues: {result.get('issues_found')}")

            # Log for fine-tuning
            if not result.get('is_accurate') or not result.get('is_complete'):
                self._log_rag_correction(
                    user_message, original_response, rag_correction, result
                )

            return result

        except Exception as e:
            print(f"⚠️ ChatGPT RAG validation failed: {e}")
            return {"validated": False, "improved_correction": rag_correction}

    def validate_consensus_output(
        self,
        original_response: str,
        corrected_response: str,
        consensus_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Validate consensus engine decision"""

        if not self.client:
            return {"validated": False}

        try:
            prompt = f"""You are an expert validator. Evaluate the consensus decision.

ORIGINAL: {original_response}
CORRECTED: {corrected_response}
SCORES: Factual={consensus_scores.get('factual', 0):.2f}, Coherence={consensus_scores.get('coherence', 0):.2f}, Consensus={consensus_scores.get('consensus', 0):.2f}

TASK: Determine if the consensus scores are reasonable. Return JSON:
{{
  "scores_reasonable": true/false,
  "should_adjust_factual": 0.0-1.0 or null,
  "should_adjust_coherence": 0.0-1.0 or null,
  "reasoning": "explanation"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4",
                temperature=0.2,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.choices[0].message.content.strip().replace("```json", "").replace("```", ""))

            print(f"\n🤖 ChatGPT Consensus Validation:")
            print(f"   Scores Reasonable: {result.get('scores_reasonable')}")
            print(f"   Reasoning: {result.get('reasoning')}")

            # Log if scores need adjustment
            if not result.get('scores_reasonable'):
                self._log_consensus_correction(original_response, corrected_response, consensus_scores, result)

            return result

        except Exception as e:
            print(f"⚠️ ChatGPT consensus validation failed: {e}")
            return {"validated": False}

    def generate_gold_standard_output(
        self,
        user_message: str,
        hallucinated_response: str,
        pipeline_correction: str
    ) -> Dict[str, Any]:
        """Generate the BEST possible correction (gold standard)"""

        if not self.client:
            return {"gold_standard": pipeline_correction, "quality_score": 0}

        try:
            prompt = f"""You are a world-class fact-checker and editor. Generate the BEST possible response.

USER QUESTION: {user_message}
HALLUCINATED RESPONSE: {hallucinated_response}
PIPELINE CORRECTION: {pipeline_correction}

TASK: Generate the gold-standard correction that is:
1. Completely factually accurate
2. Clear and well-written
3. Addresses the user's question directly
4. Provides proper context

Return JSON:
{{
  "gold_standard_response": "the best correction",
  "quality_score": 0.0-1.0,
  "improvements_made": ["list of improvements"],
  "reasoning": "why this is better"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4",
                temperature=0.3,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.choices[0].message.content.strip().replace("```json", "").replace("```", ""))

            print(f"\n🌟 ChatGPT Gold Standard Generated:")
            print(f"   Quality Score: {result.get('quality_score')}")
            print(f"   Improvements: {result.get('improvements_made')}")

            # Log gold standard for fine-tuning
            self._log_gold_standard(user_message, hallucinated_response, pipeline_correction, result)

            return result

        except Exception as e:
            print(f"⚠️ ChatGPT gold standard generation failed: {e}")
            return {"gold_standard": pipeline_correction, "quality_score": 0}

    def _log_gatekeeper_correction(self, user_msg, ai_resp, actual, expected):
        """Log gatekeeper correction for fine-tuning"""
        record = {
            "layer": "gatekeeper",
            "timestamp": datetime.now().isoformat(),
            "input": {"user_message": user_msg, "ai_response": ai_resp},
            "actual_output": actual,
            "expected_output": expected,
            "correction_type": "detection"
        }
        self._append_to_fine_tuning_log(record)

    def _log_rag_correction(self, user_msg, original, rag_correction, validation):
        """Log RAG correction for fine-tuning"""
        record = {
            "layer": "rag",
            "timestamp": datetime.now().isoformat(),
            "input": {"user_message": user_msg, "original_response": original},
            "actual_output": rag_correction,
            "improved_output": validation.get('improved_correction'),
            "issues": validation.get('issues_found'),
            "correction_type": "response_correction"
        }
        self._append_to_fine_tuning_log(record)

    def _log_consensus_correction(self, original, corrected, actual_scores, expected):
        """Log consensus correction for fine-tuning"""
        record = {
            "layer": "consensus",
            "timestamp": datetime.now().isoformat(),
            "input": {"original": original, "corrected": corrected},
            "actual_scores": actual_scores,
            "expected_adjustments": expected,
            "correction_type": "scoring"
        }
        self._append_to_fine_tuning_log(record)

    def _log_gold_standard(self, user_msg, hallucinated, pipeline_correction, gold):
        """Log gold standard for fine-tuning"""

        # OpenAI fine-tuning format
        fine_tuning_record = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides accurate, factual responses without hallucinations."
                },
                {
                    "role": "user",
                    "content": user_msg
                },
                {
                    "role": "assistant",
                    "content": gold.get('gold_standard_response', pipeline_correction)
                }
            ],
            "metadata": {
                "hallucinated_response": hallucinated,
                "pipeline_correction": pipeline_correction,
                "quality_score": gold.get('quality_score', 0),
                "improvements": gold.get('improvements_made', []),
                "timestamp": datetime.now().isoformat()
            }
        }

        # Append to JSONL file for OpenAI fine-tuning
        with open(self.fine_tuning_file, 'a') as f:
            f.write(json.dumps(fine_tuning_record) + '\n')

        print(f"✅ Gold standard logged to {self.fine_tuning_file}")

    def _append_to_fine_tuning_log(self, record):
        """Append correction to internal log"""
        self.corrections_log.append(record)

        # Also save to file
        log_file = "chatgpt_corrections_log.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(record) + '\n')

    def get_corrections_summary(self) -> Dict[str, Any]:
        """Get summary of all corrections made"""
        return {
            "total_corrections": len(self.corrections_log),
            "by_layer": {
                "gatekeeper": len([c for c in self.corrections_log if c['layer'] == 'gatekeeper']),
                "rag": len([c for c in self.corrections_log if c['layer'] == 'rag']),
                "consensus": len([c for c in self.corrections_log if c['layer'] == 'consensus'])
            },
            "log_file": self.fine_tuning_file
        }


def get_chatgpt_finetuner():
    """Factory function"""
    return ChatGPTFineTuner()
