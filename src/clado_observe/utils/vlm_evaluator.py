"""
VLM (Vision-Language Model) Evaluator for analyzing browser automation run success.
Uses OpenAI's GPT-4 Vision to evaluate screenshots and logs.
"""

import json
from typing import List, Optional, Tuple, TypedDict
from dataclasses import dataclass
from openai import OpenAI
import re


class ImageUrl(TypedDict):
    """Type definition for image URL object in VLM input."""

    url: str
    detail: str


class ImageContent(TypedDict):
    """Type definition for image content in VLM messages."""

    type: str
    image_url: ImageUrl


@dataclass
class RunData:
    """Container for collected run data"""

    task: str
    screenshots: List[str]
    logs: List[Tuple[str, str]]
    final_result: Optional[str] = None


@dataclass
class EvaluationResult:
    """Result of VLM evaluation"""

    success: bool
    confidence: float
    reasoning: str
    key_findings: List[str]
    suggestions: List[str]


class VLMEvaluator:
    """Evaluates browser automation runs using Vision-Language Models"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the VLM evaluator.

        Args:
            api_key: OpenAI API key. If not provided, will look for OPENAI_API_KEY env var
        """
        self.client = OpenAI(api_key=api_key)

    def prepare_screenshots_for_vlm(self, screenshots: List[str]) -> List[dict]:
        """
        Prepare screenshots for VLM input.

        Args:
            screenshots: List of base64 encoded images (already include data URI prefix)

        Returns:
            List of formatted image inputs for the VLM
        """
        image_inputs = []
        for i, screenshot in enumerate(screenshots):
            image_inputs.append(
                {"type": "image_url", "image_url": {"url": screenshot, "detail": "low"}}
            )
        return image_inputs

    def prepare_logs_summary(self, logs: List[Tuple[str, str]]) -> str:
        """
        Prepare a summary of logs for VLM analysis.

        Args:
            logs: List of (log_entry, log_type) tuples

        Returns:
            Formatted log summary
        """
        action_logs = []
        eval_logs = []
        tool_logs = []
        final_logs = []
        error_logs = []
        thought_logs = []

        for log_entry, log_type in logs:
            if "error" in log_entry.lower() or "failed" in log_entry.lower():
                error_logs.append(log_entry)

            if log_type == "action":
                action_logs.append(log_entry)
            elif log_type == "eval":
                eval_logs.append(log_entry)
            elif log_type == "tool":
                tool_logs.append(log_entry)
            elif log_type == "final":
                final_logs.append(log_entry)
            elif log_type == "thought":
                thought_logs.append(log_entry)

        summary = "=== Log Summary ===\n"

        if final_logs:
            summary += f"\nFINAL RESULTS ({len(final_logs)}):\n"
            summary += "\n".join(final_logs[-3:]) + "\n"

        if error_logs:
            summary += f"\nERRORS ({len(error_logs)}):\n"
            summary += "\n".join(error_logs[-5:]) + "\n"

        summary += f"\nACTIONS TAKEN ({len(action_logs)}):\n"
        summary += "\n".join(action_logs[-10:]) + "\n"

        summary += f"\nEVALUATIONS ({len(eval_logs)}):\n"
        summary += "\n".join(eval_logs[-5:]) + "\n"

        return summary

    async def evaluate_run(self, run_data: RunData) -> EvaluationResult:
        """
        Evaluate a browser automation run using the VLM.

        Args:
            run_data: Collected data from the automation run

        Returns:
            Evaluation result with success determination and analysis
        """
        content: List[dict] = []

        content.append(
            {
                "type": "text",
                "text": f"You are evaluating a browser automation run. The task was: '{run_data.task}'\n\n"
                f"Please analyze the screenshots and logs to determine if the task was completed successfully.\n\n",
            }
        )

        log_summary = self.prepare_logs_summary(run_data.logs)
        content.append({"type": "text", "text": log_summary})

        if run_data.screenshots:
            content.append(
                {
                    "type": "text",
                    "text": "\n=== Screenshots from the automation run (in chronological order) ===\n",
                }
            )
            content.extend(self.prepare_screenshots_for_vlm(run_data.screenshots))

        if run_data.final_result:
            content.append(
                {
                    "type": "text",
                    "text": f"\n=== Agent's Final Result ===\n{run_data.final_result}\n",
                }
            )

        content.append(
            {
                "type": "text",
                "text": """
Please provide a detailed evaluation with the following structure:

1. SUCCESS: Was the task completed successfully? (YES/NO)
2. CONFIDENCE: How confident are you in this assessment? (0.0 to 1.0)
3. REASONING: Explain your reasoning in 2-3 sentences.
4. KEY_FINDINGS: List 3-5 key observations from the screenshots and logs.
5. SUGGESTIONS: List 2-3 suggestions for improvement (if any).

Format your response as JSON:
{
    "success": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "...",
    "key_findings": ["finding1", "finding2", ...],
    "suggestions": ["suggestion1", "suggestion2", ...]
}
""",
            }
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=[{"role": "user", "content": content}],
                max_completion_tokens=128000,
            )

            response_text = response.choices[0].message.content

            try:
                json_match = re.search(r"\{[^}]+\}", response_text, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group())
                else:
                    result_data = {
                        "success": "success" in response_text.lower()
                        or "yes" in response_text.lower(),
                        "confidence": 0.5,
                        "reasoning": response_text[:200],
                        "key_findings": [],
                        "suggestions": [],
                    }

                return EvaluationResult(
                    success=result_data.get("success", False),
                    confidence=float(result_data.get("confidence", 0.5)),
                    reasoning=result_data.get("reasoning", "No reasoning provided"),
                    key_findings=result_data.get("key_findings", []),
                    suggestions=result_data.get("suggestions", []),
                )

            except json.JSONDecodeError:
                success = "success" in response_text.lower() or "completed" in response_text.lower()
                return EvaluationResult(
                    success=success,
                    confidence=0.5,
                    reasoning=response_text[:500] if response_text else "Unable to parse response",
                    key_findings=["Response parsing failed"],
                    suggestions=["Check VLM response format"],
                )

        except Exception as e:
            return EvaluationResult(
                success=False,
                confidence=0.0,
                reasoning=f"Evaluation failed: {str(e)}",
                key_findings=["Evaluation error occurred"],
                suggestions=["Check VLM API connection and credentials"],
            )
