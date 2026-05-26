from __future__ import annotations

import copy
import json
from typing import Any

from .config import RuntimeConfig
from .llm_runtime import OpenAIResponsesRuntime


class LLMInputPackageBuilder:
    def build(
        self,
        job_profile: dict[str, Any],
        system_decisions: dict[str, Any],
        schema_constraints: dict[str, Any],
        job_practice_profile_excerpt: dict[str, Any] | None = None,
        mission_seed: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        package = {
            "schema_version": "llm_input_package.v1",
            "job_profile": job_profile,
            "system_decisions": system_decisions,
            "schema_constraints": schema_constraints,
        }
        if job_practice_profile_excerpt is not None:
            package["job_practice_profile_excerpt"] = job_practice_profile_excerpt
        if mission_seed is not None:
            package["mission_seed"] = mission_seed
        return package


class MissionDraftGenerator:
    def __init__(
        self,
        runtime: OpenAIResponsesRuntime | None = None,
        allow_mock_without_key: bool = True,
        force_mock: bool = False,
    ) -> None:
        self.runtime = runtime or OpenAIResponsesRuntime()
        self.allow_mock_without_key = allow_mock_without_key
        self.force_mock = force_mock

    def generate(self, llm_input_package: dict[str, Any]) -> dict[str, Any]:
        config = self.runtime.config
        if self.force_mock or (not self.runtime.api_key_available() and self.allow_mock_without_key):
            draft = MockMissionDraftBuilder().build(llm_input_package)
            return {
                "llm_call_result": self._mock_call_result("draft_generation", config, draft, config.draft_temperature),
                "mission_draft": draft,
            }

        prompts = PromptBuilder().draft_prompts(llm_input_package)
        call_result = self.runtime.call_structured(
            call_type="draft_generation",
            system_prompt=prompts["system"],
            user_prompt=prompts["user"],
            json_schema=llm_input_package["schema_constraints"]["structured_output_schema"],
            temperature=config.draft_temperature,
            max_output_tokens=config.max_output_tokens_draft,
        )
        return {"llm_call_result": call_result, "mission_draft": call_result.get("output_json")}

    def _mock_call_result(
        self,
        call_type: str,
        config: RuntimeConfig,
        draft: dict[str, Any],
        temperature: float,
    ) -> dict[str, Any]:
        return {
            "schema_version": "llm_call_result.v1",
            "provider": "mock",
            "api": "local_dry_run",
            "model": config.model,
            "call_type": call_type,
            "reasoning_effort": config.reasoning_effort,
            "configured_temperature": temperature,
            "temperature_applied": False,
            "temperature_omitted_reason": config.temperature_application()["temperature_omitted_reason"],
            "status": "mocked",
            "output_json": draft,
            "usage": {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "total_tokens": 0},
            "errors": [],
            "attempt_count": 1,
            "retry_count": 0,
            "retry_errors": [],
        }


class PromptBuilder:
    def draft_prompts(self, llm_input_package: dict[str, Any]) -> dict[str, str]:
        practice_requirements = ""
        if llm_input_package.get("mission_seed"):
            practice_requirements = (
                "\nPractice survey requirements:\n"
                "- Use mission_seed as the main design brief for scenario, materials, tasks, submission format, and evaluation.\n"
                "- Keep system_decisions and schema_constraints higher priority than mission_seed when they conflict.\n"
                "- For normal difficulty with mission_seed, create 2-3 learner-visible materials: one primary material and one or two supporting materials.\n"
                "- Derive those materials from mission_seed.material_blueprints while staying within system_decisions.allowed_material_types.\n"
                "- If mission_seed.scenario_basis.request_sentence is empty, do not create a direct quoted request sentence.\n"
                "- Reflect guide_plan through mission.tasks instructions and mission.submission_format.required_sections; do not create a mission.guide field.\n"
                "- Tasks must require the learner to inspect and connect at least two provided materials.\n"
                "- Evaluation must be based on mission_seed.evaluation_basis and the selected decision situation.\n"
                "- Do not expose source_refs to the learner-facing mission text.\n"
                "- If a table uses a priority column, use it only as a comparison clue, not as a final answer or recommendation.\n"
            )
        prompt_input_package = self._prompt_input_package(llm_input_package)
        system_prompt = (
            "너는 직업 데이터 기반 미션 초안을 작성하는 작성자다. "
            "시스템이 지정한 selected_exec_job, task_type, difficulty, allowed_material_types를 변경하지 않는다. "
            "mission_output.v1 형식의 JSON만 출력한다. "
            "실제 기업명, 실제 브랜드명, 실제 인명, 외부 검색이 필요한 과제는 만들지 않는다. "
            "reliability는 {\"status\":\"pending_validation\"}만 출력하고 evidence_chain은 만들지 않는다."
        )
        user_prompt = (
            "다음 llm_input_package를 바탕으로 mission_output.v1 초안을 생성하라.\n"
            "JSON만 출력하고 Markdown 코드블록을 사용하지 마라.\n"
            "mission_id는 \"draft\"로 둔다.\n"
            "target_exec_job, mission.task_type, mission.secondary_task_types, mission.difficulty는 system_decisions 값을 복사한다.\n"
            "materials는 system_decisions.allowed_material_types 안에서만 생성한다.\n"
            "모든 material은 factual_status, evidence_source, mission_fact_refs를 가진다.\n"
            "reliability는 {\"status\":\"pending_validation\"}만 출력한다.\n\n"
            "Return one complete valid JSON object.\n"
            "Do not truncate the JSON.\n"
            "Do not include comments, trailing commas, Markdown, or text outside JSON.\n"
            "Ensure all strings are properly closed and escaped.\n\n"
            "Use system_decisions.mission_design as the design intent for the mission.\n"
            "Reflect mission_design_type and design_intent when creating scenario, materials, tasks, and evaluation.\n"
            "Do not copy mission_design into mission_output.\n\n"
            "Quality requirements:\n"
            "- Write all user-facing mission text in natural Korean.\n"
            "- Make the scenario concrete and workplace-like, but use only synthetic organizations, products, customers, and data.\n"
            "- Reflect system_decisions.mission_design.mission_design_type and design_intent in the scenario, materials, tasks, and evaluation.\n"
            "- Make every material useful for solving at least one task. Avoid decorative or unrelated materials.\n"
            "- Make task instructions clear about what the learner must decide, compare, diagnose, or propose.\n"
            "- For normal difficulty, focus on one main issue, 2-3 provided materials, and one practical recommendation.\n"
            "- For hard difficulty, include trade-off judgment, priority comparison, or constraint handling when the available materials support it.\n"
            "- Keep the mission answerable only from the provided materials and mission facts.\n"
            "- Avoid generic textbook wording, vague business jargon, and repeated template-like sentences.\n"
            "- Do not copy mission_design into mission_output.\n\n"
            "Stability requirements:\n"
            "- Use mission_fact_refs as key names only, such as org_name, domain, period, trend_pattern, main_issue, feedback_themes, and decision_goal.\n"
            "- Do not use mission_facts.period, mission_fact_period, source_ref fields, XML fields, or invented fact labels as mission_fact_refs.\n"
            "- Make evaluation.rubric points sum exactly to 100.\n"
            "- Use exact job_profile evidence item names in evaluation.rubric.linked_evidence; do not use material ids such as mat_001, mat_002, or m1.\n"
            "- Respect material size limits: chart normal 4-6 x values and hard 6-8 x values; log normal 4-6 entries and hard 6-8 entries; checklist normal 4-5 items and hard 5-7 items.\n"
            "- Respect material size limits: memo normal 3-4 items and hard 4-6 items; email normal 1 thread item and hard 1-2 thread items; table max normal 5 rows and hard 7 rows.\n"
            "- Respect material size limits: schedule normal 3-4 items and hard 4-6 items; card normal 2-3 cards and hard 3-4 cards.\n"
            "- Keep chart series count at 1 or 2.\n\n"
            "Every material.evidence_source item must exactly match a job_profile evidence item name.\n"
            "Do not use source_ref file names, XML field names, or invented evidence labels as evidence_source.\n"
            "For table materials, data.columns keys must be option, strength, weakness, priority and rows must use the same keys.\n\n"
            "The detailed JSON shape is enforced by the API structured output configuration; "
            "use the package rules for mission intent and constraints.\n\n"
            f"{practice_requirements}\n"
            f"llm_input_package:\n{json.dumps(prompt_input_package, ensure_ascii=False)}"
        )
        return {"system": system_prompt, "user": user_prompt}

    @staticmethod
    def _prompt_input_package(llm_input_package: dict[str, Any]) -> dict[str, Any]:
        prompt_input_package = copy.deepcopy(llm_input_package)
        schema_constraints = prompt_input_package.get("schema_constraints")
        if isinstance(schema_constraints, dict):
            schema_constraints.pop("structured_output_schema", None)
        return prompt_input_package


class MockMissionDraftBuilder:
    def build(self, llm_input_package: dict[str, Any]) -> dict[str, Any]:
        profile = llm_input_package["job_profile"]
        decisions = llm_input_package["system_decisions"]
        seed = llm_input_package.get("mission_seed")
        difficulty = decisions["difficulty"]["level"]
        job_cd = profile["job_identity"]["job_cd"]
        context = self._context(job_cd, profile, seed)
        material_count = len(seed.get("material_blueprints") or []) if seed else (3 if difficulty == "normal" else 4)
        seed_material_types = [
            item.get("learner_visible_material_type")
            for item in (seed.get("material_blueprints") or [])
            if item.get("learner_visible_material_type") in decisions["allowed_material_types"]
        ] if seed else []
        material_types = seed_material_types[:material_count] or decisions["allowed_material_types"][:material_count]
        if len(material_types) < material_count:
            for candidate in ("chart", "table", "memo", "email", "schedule", "checklist", "log", "card"):
                if candidate in decisions["allowed_material_types"] and candidate not in material_types:
                    material_types.append(candidate)
                if len(material_types) == material_count:
                    break

        facts = self._mission_facts(context, difficulty)
        materials = [
            self._material(idx, material_type, facts, context, profile, difficulty)
            for idx, material_type in enumerate(material_types, start=1)
        ]
        tasks = self._tasks(materials, context, difficulty, seed)

        return {
            "schema_version": "mission_output.v1",
            "mission_id": "draft",
            "job_identity": copy.deepcopy(profile["job_identity"]),
            "target_exec_job": copy.deepcopy(decisions["selected_exec_job"]),
            "mission_facts": facts,
            "mission": {
                "title": f"{context['domain']} 자료 검토 미션",
                "task_type": decisions["primary_task_type"],
                "secondary_task_types": copy.deepcopy(decisions["secondary_task_types"]),
                "difficulty": copy.deepcopy(decisions["difficulty"]),
                "scenario": {
                    "role": context["role"],
                    "context": context["scenario_context"],
                    "goal": facts["decision_goal"],
                    "constraints": [
                        "제공된 자료만 사용한다.",
                        "최소 2개 이상의 자료를 근거로 연결한다.",
                        "외부 검색이나 전문 법률·투자·보험 지식 없이 판단한다.",
                    ],
                },
                "materials": materials,
                "tasks": tasks,
                "submission_format": self._submission_format(difficulty),
            },
            "evaluation": self._evaluation(profile, tasks),
            "evidence_chain_draft": {
                "source_exec_job": {
                    "id": decisions["selected_exec_job"]["exec_job_id"],
                    "text": decisions["selected_exec_job"]["text"],
                },
                "linked_evidence": {
                    "activities": [item["name"] for item in profile["evidence"]["work_activities"][:3]],
                    "knowledge": [item["name"] for item in profile["evidence"]["knowledge"][:2]],
                    "abilities": [item["name"] for item in profile["evidence"]["abilities"][:2]],
                },
                "material_evidence_map": [
                    {"material_id": material["material_id"], "supported_by": material["evidence_source"]}
                    for material in materials
                ],
            },
            "reliability": {"status": "pending_validation"},
        }

    def _context(self, job_cd: str, profile: dict[str, Any], seed: dict[str, Any] | None = None) -> dict[str, str]:
        defaults = {
            "K000000997": {
                "org_name": "B가게",
                "domain": "생활용품 상품",
                "role": "상품기획 담당자",
                "scenario_context": "온라인 생활용품 판매팀에서 다음 달 테스트 상품 방향을 검토하고 있다.",
            },
            "K000001080": {
                "org_name": "D서비스팀",
                "domain": "서비스 이용 데이터",
                "role": "데이터분석 담당자",
                "scenario_context": "온라인 서비스 운영팀에서 최근 이용 지표 변화와 고객 행동 로그를 검토하고 있다.",
            },
            "K000001179": {
                "org_name": "F투자팀",
                "domain": "투자 후보 검토",
                "role": "투자분석 담당자",
                "scenario_context": "투자 검토 회의 전 산업 지표와 후보 기업 요약 자료를 비교하고 있다.",
            },
            "K000007519": {
                "org_name": "H보험 기획팀",
                "domain": "보험상품 개선안",
                "role": "보험상품개발 담당자",
                "scenario_context": "보험상품 기획팀에서 고객 반응과 위험 점검 자료를 바탕으로 개선 방향을 정리하고 있다.",
            },
        }
        context = defaults.get(
            job_cd,
            {
                "org_name": "A팀",
                "domain": profile["job_identity"].get("job_smcl_nm", "업무"),
                "role": f"{profile['job_identity'].get('job_smcl_nm', '직무')} 담당자",
                "scenario_context": "팀 내부 검토 회의 전 제공 자료를 정리하고 있다.",
            },
        )
        if seed:
            basis = seed.get("scenario_basis") or {}
            context["role"] = basis.get("learner_role") or context["role"]
            context["scenario_context"] = basis.get("work_context") or context["scenario_context"]
            context["decision_goal"] = basis.get("goal") or f"{context['domain']}에 대해 다음 실행 방향 1가지를 근거와 함께 제안한다."
        return context

    def _mission_facts(self, context: dict[str, str], difficulty: str) -> dict[str, Any]:
        months = ["1월", "2월", "3월", "4월", "5월", "6월"] if difficulty == "normal" else ["1월", "2월", "3월", "4월", "5월", "6월", "7월"]
        return {
            "org_name": context["org_name"],
            "domain": context["domain"],
            "period": months,
            "trend_pattern": "중반까지 개선되다가 최근 두 기간에서 하락 또는 정체가 나타남",
            "main_issue": "핵심 지표가 최근 약해지고 부정 의견이 늘어남",
            "feedback_themes": ["가격 대비 만족도 약화", "대안 비교 필요", "실행 전 제약 확인 필요"],
            "decision_goal": context.get("decision_goal") or f"{context['domain']}에 대해 다음 실행 방향 1가지를 근거와 함께 제안한다.",
        }

    def _material(
        self,
        idx: int,
        material_type: str,
        facts: dict[str, Any],
        context: dict[str, str],
        profile: dict[str, Any],
        difficulty: str,
    ) -> dict[str, Any]:
        material_id = f"mat_{idx:03d}"
        evidence_source = self._evidence_sources(profile, material_type)
        base = {
            "material_id": material_id,
            "type": material_type,
            "subtype": self._subtype(material_type),
            "title": self._title(material_type, context),
            "description": f"{facts['domain']} 판단에 필요한 {material_type} 자료다.",
            "factual_status": "synthetic_mission_material",
            "used_for": "핵심 문제와 실행 방향 판단",
            "evidence_source": evidence_source,
            "mission_fact_refs": ["period", "trend_pattern", "main_issue", "decision_goal"],
            "data": self._material_data(material_type, facts, difficulty),
            "confidence": {"score": 0.86, "checks": {"synthetic_material": True}, "warnings": []},
        }
        if material_type in {"memo", "email", "checklist", "log"}:
            base["mission_fact_refs"] = ["main_issue", "feedback_themes", "decision_goal"]
        if material_type in {"schedule", "card"}:
            base["mission_fact_refs"] = ["decision_goal", "feedback_themes"]
        return base

    def _subtype(self, material_type: str) -> str:
        return {
            "chart": "monthly_trend",
            "table": "comparison_table",
            "memo": "feedback_summary",
            "email": "manager_request",
            "schedule": "work_schedule",
            "checklist": "risk_checklist",
            "log": "activity_log",
            "card": "option_card",
        }[material_type]

    def _title(self, material_type: str, context: dict[str, str]) -> str:
        labels = {
            "chart": "월별 핵심 지표 추이",
            "table": "대안 비교표",
            "memo": "고객 반응 요약 메모",
            "email": "팀장 요청 이메일",
            "schedule": "실행 일정표",
            "checklist": "실행 전 점검표",
            "log": "최근 처리 로그",
            "card": "대안 카드",
        }
        return f"{context['org_name']} {labels[material_type]}"

    def _material_data(self, material_type: str, facts: dict[str, Any], difficulty: str) -> dict[str, Any]:
        periods = facts["period"]
        hard = difficulty == "hard"
        if material_type == "chart":
            values = [72, 76, 81, 84, 73, 69, 68][: len(periods)]
            return {
                "chart_type": "line",
                "x_axis": {"label": "기간", "values": periods},
                "y_axis": {"label": "핵심 지표", "unit": "점"},
                "series": [{"name": "핵심 지표", "values": values}],
            }
        if material_type == "table":
            rows = [
                {"option": "A안", "strength": "기존 고객 반응 안정", "weakness": "차별성 약함", "priority": 2},
                {"option": "B안", "strength": "최근 이슈 직접 개선", "weakness": "일정 확인 필요", "priority": 1},
                {"option": "C안", "strength": "비용 부담 낮음", "weakness": "효과 검증 부족", "priority": 3},
            ]
            if hard:
                rows.append({"option": "D안", "strength": "장기 확장 가능", "weakness": "초기 조율 필요", "priority": 4})
            return {
                "columns": [
                    {"key": "option", "label": "대안"},
                    {"key": "strength", "label": "강점"},
                    {"key": "weakness", "label": "약점"},
                    {"key": "priority", "label": "우선순위"},
                ],
                "rows": rows,
            }
        if material_type == "memo":
            items = [
                "최근 두 기간에서 만족도 관련 부정 의견이 늘었다.",
                "가격 대비 효용을 더 명확히 보여달라는 의견이 반복되었다.",
                "기존 방식은 안정적이지만 새로움이 부족하다는 평가가 있었다.",
                "빠른 개선보다 핵심 불만을 먼저 줄이는 방향이 필요하다.",
            ]
            if hard:
                items.append("일정과 비용 제약 때문에 한 번에 모든 대안을 실행하기 어렵다.")
            return {"author": "고객지원 담당자", "items": items}
        if material_type == "email":
            body = "최근 지표와 고객 반응을 함께 보고 다음 회의 전 실행 방향을 정리해주세요. 제공 자료 안에서 근거를 연결하고, 실행 전 확인할 제약도 함께 적어주세요."
            return {"thread": [{"from": "팀장", "to": "담당자", "subject": "다음 실행 방향 검토 요청", "body": body}]}
        if material_type == "schedule":
            items = [
                {"period": "1주차", "task": "자료 재확인", "constraint": "기존 자료 범위 안에서 검토"},
                {"period": "2주차", "task": "대안 1차 선정", "constraint": "2개 이하로 압축"},
                {"period": "3주차", "task": "관련 부서 확인", "constraint": "일정 변경 1회만 가능"},
                {"period": "4주차", "task": "실행안 확정", "constraint": "핵심 지표 개선 목표 포함"},
            ]
            if hard:
                items.append({"period": "5주차", "task": "결과 점검 계획 수립", "constraint": "평가 기준 사전 합의"})
            return {"items": items}
        if material_type == "checklist":
            return {
                "items": [
                    {"label": "핵심 지표 하락 원인이 자료에서 확인되는가", "status": "unchecked", "importance": "high"},
                    {"label": "선택 대안이 고객 반응 이슈를 줄이는가", "status": "issue", "importance": "high"},
                    {"label": "실행 일정 안에 검토가 가능한가", "status": "unchecked", "importance": "medium"},
                    {"label": "선택하지 않은 대안의 이유가 설명되는가", "status": "unchecked", "importance": "medium"},
                    {"label": "추가 외부 조사가 없어도 판단 가능한가", "status": "checked", "importance": "high"},
                ]
            }
        if material_type == "log":
            entries = [
                {"time": "1주차", "actor": "고객", "event": "이용 불편 의견 접수", "note": "핵심 기능 설명 부족"},
                {"time": "2주차", "actor": "운영 담당자", "event": "반복 문의 확인", "note": "같은 유형 문의 증가"},
                {"time": "3주차", "actor": "고객", "event": "대안 비교 요청", "note": "가격과 효과 비교 필요"},
                {"time": "4주차", "actor": "팀장", "event": "개선 방향 검토 요청", "note": "자료 기반 판단 필요"},
            ]
            if hard:
                entries.extend(
                    [
                        {"time": "5주차", "actor": "담당자", "event": "우선순위 재검토", "note": "일정 제약 발생"},
                        {"time": "6주차", "actor": "고객", "event": "만족도 하락 의견", "note": "핵심 이슈 재확인"},
                    ]
                )
            return {"entries": entries}
        return {
            "cards": [
                {"title": "A안", "attributes": {"강점": "안정적", "약점": "차별성 낮음", "적합도": "보통"}},
                {"title": "B안", "attributes": {"강점": "이슈 직접 대응", "약점": "일정 확인", "적합도": "높음"}},
                {"title": "C안", "attributes": {"강점": "비용 낮음", "약점": "효과 불명확", "적합도": "낮음"}},
            ]
        }

    def _tasks(
        self,
        materials: list[dict[str, Any]],
        context: dict[str, str],
        difficulty: str,
        seed: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        material_ids = [material["material_id"] for material in materials]
        if seed and seed.get("task_plan"):
            tasks = []
            for index, plan in enumerate(seed["task_plan"][:3], start=1):
                instruction = plan.get("instruction") if isinstance(plan, dict) else str(plan)
                required = material_ids[:1] if index == 1 else material_ids
                tasks.append(
                    {
                        "task_id": f"task_{index:03d}",
                        "instruction": instruction,
                        "required_materials": required,
                        "expected_action": plan.get("expected_action", "practice_survey_guided_action") if isinstance(plan, dict) else "practice_survey_guided_action",
                    }
                )
            return tasks
        tasks = [
            {
                "task_id": "task_001",
                "instruction": "자료에서 최근 흐름상 가장 큰 문제를 1가지 찾고 근거 자료를 적어라.",
                "required_materials": material_ids[:2],
                "expected_action": "analyze_issue",
            },
            {
                "task_id": "task_002",
                "instruction": "문제 원인을 줄이기 위한 실행 방향 1가지를 선택하고 이유를 설명하라.",
                "required_materials": material_ids,
                "expected_action": "choose_action",
            },
            {
                "task_id": "task_003",
                "instruction": "선택한 방향을 실행하기 전에 확인해야 할 주의점 1가지를 제시하라.",
                "required_materials": material_ids[-2:] if len(material_ids) >= 2 else material_ids,
                "expected_action": "identify_risk",
            },
        ]
        if difficulty == "hard":
            tasks.append(
                {
                    "task_id": "task_004",
                    "instruction": "선택하지 않은 대안 1가지를 고르고 제외한 이유를 자료 근거와 함께 설명하라.",
                    "required_materials": material_ids,
                    "expected_action": "compare_tradeoff",
                }
            )
        return tasks

    def _submission_format(self, difficulty: str) -> dict[str, Any]:
        if difficulty == "normal":
            return {
                "type": "guided_short_report",
                "estimated_time_minutes": 15,
                "required_sections": ["핵심 발견 1가지", "근거 자료 2개", "제안 1가지", "주의할 점 1가지"],
                "length_hint": "400~700자",
            }
        return {
            "type": "decision_memo",
            "estimated_time_minutes": 20,
            "required_sections": ["핵심 문제", "선택한 방향", "선택 근거", "선택하지 않은 대안과 이유", "실행 전 확인할 리스크"],
            "length_hint": "700~1000자",
        }

    def _evaluation(self, profile: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Any]:
        linked = [item["name"] for item in profile["evidence"]["work_activities"][:3]]
        return {
            "expected_insights": [
                "수치 흐름과 정성 의견을 함께 연결해야 한다.",
                "제안은 제공 자료에서 확인되는 문제와 직접 연결되어야 한다.",
                "실행 전 제약이나 리스크를 함께 고려해야 한다.",
            ],
            "rubric": [
                {
                    "criterion": "자료 해석",
                    "description": "제공 자료에서 핵심 흐름과 문제를 정확히 찾았는가",
                    "points": 30,
                    "linked_evidence": linked[:2],
                },
                {
                    "criterion": "근거 기반 판단",
                    "description": "선택한 방향이 2개 이상의 자료 근거와 연결되는가",
                    "points": 40,
                    "linked_evidence": linked,
                },
                {
                    "criterion": "실행 가능성",
                    "description": "제안과 주의점이 시간 안에 수행 가능한 형식으로 정리되었는가",
                    "points": 30,
                    "linked_evidence": linked[-2:],
                },
            ],
        }

    def _evidence_sources(self, profile: dict[str, Any], material_type: str) -> list[str]:
        preferences = {
            "chart": ["정보, 자료 분석", "정보 수집", "사물, 행동, 사건 파악"],
            "table": ["기준에 따른 정보 평가", "의사 결정, 문제점 해결", "목표, 전략 수립", "정보 처리"],
            "memo": ["정보 수집", "사물, 행동, 사건 파악", "상사, 동료, 부하직원과 소통"],
            "email": ["상사, 동료, 부하직원과 소통", "조직 외부인과 소통", "이메일 이용하기"],
            "schedule": ["업무, 활동에 대한 일정관리", "업무 계획, 우선순위 결정", "마감시간"],
            "checklist": ["기준에 따른 정보 평가", "의사 결정, 문제점 해결", "업무 계획, 우선순위 결정"],
            "log": ["정보 처리", "컴퓨터 업무", "정보 수집"],
            "card": ["창조적 생각", "목표, 전략 수립", "의사 결정, 문제점 해결"],
        }
        all_items = [item for group in profile.get("evidence", {}).values() for item in group]
        names = {item["name"] for item in all_items}
        selected = [name for name in preferences[material_type] if name in names]
        if len(selected) >= 2:
            return selected[:2]
        for item in profile.get("evidence", {}).get("work_activities", []):
            if item["name"] not in selected:
                selected.append(item["name"])
            if len(selected) >= 2:
                break
        if not selected and all_items:
            selected.append(all_items[0]["name"])
        return selected[:2]
