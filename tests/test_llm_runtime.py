# OpenAIResponsesRuntime의 API key 처리, 오류 매핑, structured output 호출 형식을 검증한다.

from __future__ import annotations

import os
import sys
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.config import RuntimeConfig
from mission_generation.draft_generator import MissionDraftGenerator
from mission_generation.llm_runtime import OpenAIResponsesRuntime
from mission_generation.repair_manager import RepairManager


class CapturingRuntime(OpenAIResponsesRuntime):
    def __init__(self, config: RuntimeConfig) -> None:
        self.last_body: dict[str, Any] | None = None
        super().__init__(config)

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        self.last_body = body
        return {
            "status": "completed",
            "output_text": "{\"ok\": true}",
            "usage": {
                "input_tokens": 1,
                "output_tokens": 1,
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": 2,
            },
        }


class SequenceRuntime(OpenAIResponsesRuntime):
    def __init__(self, config: RuntimeConfig, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.post_count = 0
        super().__init__(config)

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        self.post_count += 1
        return self.responses.pop(0)


class RecordingDraftRuntime:
    def __init__(self) -> None:
        self.config = RuntimeConfig()
        self.json_schema: dict[str, Any] | None = None
        self.user_prompt: str | None = None

    def api_key_available(self) -> bool:
        return True

    def call_structured(
        self,
        *,
        call_type: str,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        temperature: float,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        self.json_schema = json_schema
        self.user_prompt = user_prompt
        return {
            "schema_version": "llm_call_result.v1",
            "provider": "test",
            "status": "completed",
            "output_json": {"ok": True},
            "usage": {"input_tokens": 1, "output_tokens": 1, "reasoning_tokens": 0, "total_tokens": 2},
            "errors": [],
        }


def success_response(output_text: str = "{\"ok\": true}") -> dict[str, Any]:
    return {
        "status": "completed",
        "output_text": output_text,
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": 2,
        },
    }


class LLMRuntimeTest(unittest.TestCase):
    def test_responses_request_omits_temperature(self) -> None:
        env_name = "TEST_OPENAI_API_KEY"
        os.environ[env_name] = "test-key"
        runtime = CapturingRuntime(RuntimeConfig(api_key_env=env_name))
        result = runtime.call_structured(
            call_type="draft_generation",
            system_prompt="Return JSON.",
            user_prompt="Return {\"ok\": true}.",
            json_schema={"type": "object"},
            temperature=0.8,
            max_output_tokens=100,
        )
        os.environ.pop(env_name, None)

        self.assertIsNotNone(runtime.last_body)
        self.assertNotIn("temperature", runtime.last_body or {})
        self.assertEqual(result["configured_temperature"], 0.8)
        self.assertFalse(result["temperature_applied"])
        self.assertEqual(result["temperature_omitted_reason"], "unsupported_by_model")
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(result["retry_count"], 0)
        self.assertEqual(result["retry_errors"], [])

    def test_responses_request_accepts_custom_schema_name(self) -> None:
        env_name = "TEST_OPENAI_API_KEY"
        os.environ[env_name] = "test-key"
        runtime = CapturingRuntime(RuntimeConfig(api_key_env=env_name))
        try:
            runtime.call_structured(
                call_type="decision_selection",
                system_prompt="Return JSON.",
                user_prompt="Return {\"ok\": true}.",
                json_schema={"type": "object"},
                temperature=0.8,
                max_output_tokens=100,
                schema_name="decision_selector_v1",
            )
        finally:
            os.environ.pop(env_name, None)

        self.assertEqual(runtime.last_body["text"]["format"]["name"], "decision_selector_v1")  # type: ignore[index]

    def test_output_parse_failed_is_retryable(self) -> None:
        runtime = OpenAIResponsesRuntime(RuntimeConfig(api_key_env="TEST_OPENAI_API_KEY"))
        self.assertTrue(runtime._should_retry("OUTPUT_PARSE_FAILED", 0))
        self.assertFalse(runtime._should_retry("OUTPUT_PARSE_FAILED", 1))

    def test_parse_failure_retries_and_returns_success_metadata(self) -> None:
        env_name = "TEST_OPENAI_API_KEY"
        os.environ[env_name] = "test-key"
        runtime = SequenceRuntime(
            RuntimeConfig(api_key_env=env_name),
            [{"status": "completed", "output": []}, success_response()],
        )

        try:
            with patch("mission_generation.llm_runtime.time.sleep", lambda _: None):
                result = runtime.call_structured(
                    call_type="draft_generation",
                    system_prompt="Return JSON.",
                    user_prompt="Return {\"ok\": true}.",
                    json_schema={"type": "object"},
                    temperature=0.8,
                    max_output_tokens=100,
                )
        finally:
            os.environ.pop(env_name, None)

        self.assertEqual(runtime.post_count, 2)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["output_json"], {"ok": True})
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(result["retry_errors"][0]["code"], "OUTPUT_PARSE_FAILED")
        self.assertEqual(result["errors"], [])

    def test_parse_failure_retry_exhaustion_returns_failed_metadata(self) -> None:
        env_name = "TEST_OPENAI_API_KEY"
        os.environ[env_name] = "test-key"
        runtime = SequenceRuntime(
            RuntimeConfig(api_key_env=env_name),
            [{"status": "completed", "output": []}, success_response("{\"ok\": ")],
        )

        try:
            with patch("mission_generation.llm_runtime.time.sleep", lambda _: None):
                result = runtime.call_structured(
                    call_type="draft_generation",
                    system_prompt="Return JSON.",
                    user_prompt="Return {\"ok\": true}.",
                    json_schema={"type": "object"},
                    temperature=0.8,
                    max_output_tokens=100,
                )
        finally:
            os.environ.pop(env_name, None)

        self.assertEqual(runtime.post_count, 2)
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["output_json"])
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(result["retry_errors"][0]["code"], "OUTPUT_PARSE_FAILED")
        self.assertEqual(result["errors"][0]["code"], "OUTPUT_PARSE_FAILED")

    def test_mock_call_results_include_temperature_metadata(self) -> None:
        config = RuntimeConfig()
        draft_result = MissionDraftGenerator()._mock_call_result("draft_generation", config, {}, 0.8)
        self.assertEqual(draft_result["configured_temperature"], 0.8)
        self.assertFalse(draft_result["temperature_applied"])
        self.assertEqual(draft_result["attempt_count"], 1)
        self.assertEqual(draft_result["retry_count"], 0)
        self.assertEqual(draft_result["retry_errors"], [])

        repair_request = {
            "mission_output_draft": {"mission": {"materials": []}, "evaluation": {"rubric": []}},
            "system_decisions": {
                "selected_exec_job": {},
                "primary_task_type": "research_and_analysis",
                "secondary_task_types": [],
                "difficulty": {"level": "normal"},
                "allowed_material_types": [],
            },
        }
        repair_result = RepairManager(force_mock=True).repair(repair_request=repair_request, json_schema={})
        repair_call = repair_result["llm_call_result"]
        self.assertEqual(repair_call["configured_temperature"], 0.4)
        self.assertFalse(repair_call["temperature_applied"])
        self.assertEqual(repair_call["temperature_omitted_reason"], "unsupported_by_model")
        self.assertEqual(repair_call["attempt_count"], 1)
        self.assertEqual(repair_call["retry_count"], 0)
        self.assertEqual(repair_call["retry_errors"], [])

    def test_draft_generator_keeps_api_schema_outside_prompt(self) -> None:
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
        package = {
            "schema_version": "llm_input_package.v1",
            "job_profile": {},
            "system_decisions": {},
            "schema_constraints": {
                "schema_version": "schema_constraints.v1",
                "material_rules": {"allowed_evidence_names": ["evidence_a"]},
                "structured_output_schema": schema,
            },
        }
        runtime = RecordingDraftRuntime()

        result = MissionDraftGenerator(runtime=runtime, allow_mock_without_key=False).generate(package)  # type: ignore[arg-type]

        self.assertEqual(runtime.json_schema, schema)
        self.assertNotIn("structured_output_schema", runtime.user_prompt or "")
        self.assertIn("material_rules", runtime.user_prompt or "")
        self.assertEqual(result["mission_draft"], {"ok": True})

    def test_repair_prompt_includes_json_completeness_instruction(self) -> None:
        prompts = RepairManager(force_mock=True)._repair_prompts({"mission_output_draft": {}})
        self.assertIn("Return one complete valid JSON object", prompts["user"])
        self.assertIn("Do not truncate the JSON", prompts["user"])
        self.assertIn("Stability requirements", prompts["user"])
        self.assertIn("mission_fact_refs as key names only", prompts["user"])
        self.assertIn("rubric points sum exactly to 100", prompts["user"])
        self.assertIn("do not use material ids", prompts["user"])
        self.assertIn("beginner-friendly job-experience", prompts["user"])
        self.assertIn("professional knowledge requirements", prompts["user"])
        self.assertIn("Make the mission easier than a real workplace task", prompts["user"])
        self.assertIn("Prefer everyday workplace words over specialist terms", prompts["user"])
        self.assertIn("easy has 1 material and 1 task", prompts["user"])
        self.assertIn("hard has 3 materials and 2 tasks", prompts["user"])
        self.assertIn("Hard means more materials, not expert-level reasoning", prompts["user"])
        self.assertIn("Each task must require only one learner action", prompts["user"])
        self.assertIn("short descriptive written response", prompts["user"])

    def test_http_error_message_uses_safe_openai_error_body(self) -> None:
        body = b'{"error":{"message":"Bad request detail.","type":"invalid_request_error","param":"text.format"}}'
        error = urllib.error.HTTPError(
            url="https://api.openai.com/v1/responses",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=BytesIO(body),
        )
        mapped = OpenAIResponsesRuntime(RuntimeConfig(api_key_env="TEST_OPENAI_API_KEY"))._map_http_error(error)
        self.assertEqual(mapped["code"], "OPENAI_BAD_REQUEST")
        self.assertIn("Bad request detail.", mapped["message"])
        self.assertIn("param=text.format", mapped["message"])


if __name__ == "__main__":
    unittest.main()
