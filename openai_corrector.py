"""
OpenAI Correction Layer
Generates corrections for detected hallucinations using GPT-4
Used for fine-tuning data collection (not displayed in frontend)
"""

import openai
import json
from typing import Dict, Any
from config import config

class OpenAICorrectorAgent:
    """
    Uses OpenAI GPT to generate corrections for hallucinations
    This is used for:
    1. Generating training data for fine-tuning
    2. Providing high-quality corrections as a reference
    3. Improving the RAG agent over time
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.OPENAI_API_KEY
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def generate_correction(
        self,
        user_message: str,
        hallucinated_response: str,
        detection_type: str,
        detection_reason: str,
        retrieved_context: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a corrected response using GPT-4

        Args:
            user_message: Original user question
            hallucinated_response: The response containing hallucination
            detection_type: Type of hallucination (fabricated, temporal, etc.)
            detection_reason: Why it was flagged as hallucination
            retrieved_context: Context from RAG retrieval

        Returns:
            Dict with corrected_response and explanation
        """

        if not self.client:
            return {
                "corrected_response": hallucinated_response,
                "explanation": "OpenAI API not configured",
                "method": "none"
            }

        try:
            # Build the correction prompt
            prompt = self._build_correction_prompt(
                user_message,
                hallucinated_response,
                detection_type,
                detection_reason,
                retrieved_context
            )

            # Call GPT-4 for correction
            response = self.client.chat.completions.create(
                model="gpt-4",
                temperature=0.3,
                max_tokens=500,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a factual accuracy expert. Your job is to correct hallucinations in AI responses.

Rules:
1. If the response contains factual errors, correct them with accurate information
2. If the response contains exaggerations, tone them down to accurate statements
3. If the response has temporal inconsistencies, fix the dates/timeline
4. If the response has logical contradictions, resolve them
5. Maintain a similar tone and length as the original
6. Be precise and cite specific facts when correcting
7. Return your answer in JSON format with keys: "corrected_response" and "explanation"
"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Parse the response
            content = response.choices[0].message.content.strip()

            # Try to parse as JSON
            try:
                result = json.loads(content.replace("```json", "").replace("```", "").strip())
                return {
                    "corrected_response": result.get("corrected_response", hallucinated_response),
                    "explanation": result.get("explanation", "No explanation provided"),
                    "method": "gpt-4",
                    "tokens_used": response.usage.total_tokens
                }
            except json.JSONDecodeError:
                # If not JSON, use the whole response as correction
                return {
                    "corrected_response": content,
                    "explanation": "GPT-4 correction (non-JSON response)",
                    "method": "gpt-4",
                    "tokens_used": response.usage.total_tokens
                }

        except Exception as e:
            print(f"⚠️ OpenAI correction error: {e}")
            return {
                "corrected_response": hallucinated_response,
                "explanation": f"Error: {str(e)}",
                "method": "error"
            }

    def _build_correction_prompt(
        self,
        user_message: str,
        hallucinated_response: str,
        detection_type: str,
        detection_reason: str,
        retrieved_context: str
    ) -> str:
        """Build a detailed prompt for correction"""

        prompt = f"""I need you to correct a hallucinated AI response.

USER QUESTION:
{user_message}

HALLUCINATED RESPONSE:
{hallucinated_response}

DETECTION TYPE: {detection_type}
REASON FOR FLAGGING: {detection_reason}
"""

        if retrieved_context:
            prompt += f"""
RETRIEVED CONTEXT FROM KNOWLEDGE BASE:
{retrieved_context}
"""

        prompt += """
Please provide:
1. A corrected version of the response that fixes the hallucination
2. An explanation of what was wrong and how you fixed it

Return your answer in JSON format:
{
  "corrected_response": "The corrected response here...",
  "explanation": "Explanation of what was wrong and how it was fixed..."
}
"""

        return prompt

    def log_for_fine_tuning(
        self,
        user_message: str,
        hallucinated_response: str,
        corrected_response: str,
        detection_info: Dict[str, Any],
        validation_score: float,
        log_file: str = "fine_tuning_data.jsonl"
    ):
        """
        Log correction data for fine-tuning
        Saves in JSONL format for OpenAI fine-tuning
        """

        try:
            fine_tuning_record = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides accurate, factual responses without hallucinations."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    },
                    {
                        "role": "assistant",
                        "content": corrected_response
                    }
                ],
                "metadata": {
                    "hallucinated_response": hallucinated_response,
                    "detection_type": detection_info.get("type", "unknown"),
                    "detection_confidence": detection_info.get("confidence", 0.0),
                    "detection_reason": detection_info.get("reason", ""),
                    "validation_score": validation_score,
                    "corrected_by": "hybrid_system"
                }
            }

            # Append to JSONL file
            with open(log_file, 'a') as f:
                f.write(json.dumps(fine_tuning_record) + '\n')

            print(f"✅ Logged fine-tuning data to {log_file}")

        except Exception as e:
            print(f"⚠️ Failed to log fine-tuning data: {e}")


def get_openai_corrector():
    """Factory function to create OpenAI corrector"""
    return OpenAICorrectorAgent()
