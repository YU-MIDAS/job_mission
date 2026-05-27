# JSON Field Reference

이 문서는 미션 생성 과정에서 만들어지는 주요 JSON 파일과 필드의 의미를 설명합니다.

처음 확인할 때는 `mission_output.json`을 먼저 보고, 문제가 있으면 같은 폴더의 `validator_result_attempt_N.json`, `repair_request_attempt_1.json`, `llm_input_package.json`, `system_decisions.json`을 함께 보면 됩니다.

## Main JSON Files

| 파일 | 위치 | 역할 |
|---|---|---|
| `mission_output.json` | `outputs/pilot/v1/runs/{run_id}/jobs/{job_cd}/{difficulty}/` | 검증을 통과한 최종 미션 |
| `llm_input_package.json` | 같은 미션 폴더 | LLM에 전달하는 입력 패키지 |
| `system_decisions.json` | 같은 미션 폴더 | 미션 생성 전 확정한 수행직무/task/material 결정값 |
| `schema_constraints.json` | 같은 미션 폴더 | LLM structured output schema와 검증 규칙 |
| `decision_selector_input.json` | 같은 미션 폴더 | selector LLM에 보낸 입력 |
| `decision_selector_result.json` | 같은 미션 폴더 | selector LLM이 고른 미션 틀 |
| `decision_selector_validation.json` | 같은 미션 폴더 | selector 결과 검증 |
| `job_practice_sheet_background.json` | 같은 미션 폴더 | 직무조사시트 Markdown 배경지식 |
| `llm_call_result_attempt_N.json` | 같은 미션 폴더 | N번째 draft/repair LLM 호출 결과 |
| `mission_draft_attempt_N.json` | 같은 미션 폴더 | N번째 LLM 미션 초안 |
| `validator_result_attempt_N.json` | 같은 미션 폴더 | N번째 초안 검증 결과 |
| `repair_request_attempt_1.json` | 같은 미션 폴더 | repair 호출에 들어간 실패 이유와 수정 지침 |
| `run_status.json` | 같은 미션 폴더 | 해당 job/difficulty의 최종 상태 |
| `pilot_summary.json` | run 루트 | 전체 실행 요약 |
| `artifact_index.json` | run 루트 | 각 target의 주요 산출물 경로 |

`attempt_0`은 최초 생성입니다. validator가 `repair_required`를 반환하면 `attempt_1` 파일들이 생깁니다. 현재 기본 repair는 최대 1회입니다.

## `mission_output.json`

`mission_output.json`은 최종 미션 원본입니다. HTML은 이 JSON을 화면용으로 가공해 보여줍니다.

### Top-Level Fields

| 필드 | 타입 | 설명 |
|---|---|---|
| `schema_version` | string | 출력 스키마 버전. 현재 `mission_output.v1` |
| `mission_id` | string | 최종 미션 ID |
| `job_identity` | object | 대상 직업 정보 |
| `target_exec_job` | object | 이번 미션에서 사용한 수행직무 |
| `mission_facts` | object | 미션 자료와 task가 공유하는 합성 사실 |
| `mission` | object | 학습자에게 제시할 실제 미션 내용 |
| `evaluation` | object | 기대 통찰과 rubric |
| `reliability` | object | validator가 계산한 통과 여부와 점수 |
| `evidence_chain` | object | 자료가 어떤 job profile evidence와 연결되는지 추적 |

LLM 초안 단계의 `mission_draft_attempt_N.json`에는 `evidence_chain_draft`가 있을 수 있습니다. 최종 저장 단계에서는 이 임시 값을 제거하고, validator가 실제 `job_profile.evidence`를 대조해 만든 `evidence_chain`을 넣습니다.

## `mission`

| 필드 | 타입 | 설명 |
|---|---|---|
| `title` | string | 미션 제목 |
| `task_type` | string | 주 과업 유형. `system_decisions.primary_task_type`과 같아야 함 |
| `secondary_task_types` | array | 보조 과업 유형 |
| `difficulty` | object | 난이도 정책 |
| `scenario` | object | 학습자에게 주어지는 업무 상황 |
| `materials` | array | 제공 자료 |
| `tasks` | array | 수행 과제 |
| `submission_format` | object | 답변 형식과 분량 |

## `mission.scenario`

| 필드 | 타입 | 설명 |
|---|---|---|
| `role` | string | 학습자의 역할 |
| `context` | string | 업무 상황 |
| `goal` | string | 달성해야 할 목표 |
| `constraints` | array | 답변 시 지켜야 할 조건 |
| `glossary` | array | 용어 정리. 필수 필드이며 빈 배열 허용 |

`glossary` 항목은 반드시 다음 구조를 가집니다.

```json
{"term": "데이터 자원", "definition": "분석에 쓰려고 모아 둔 데이터의 위치와 형태입니다."}
```

용어 설명은 `context`, `goal`, `constraints`, `tasks` 본문 끝에 `용어 설명:`으로 붙이지 않고 `glossary`에 분리하는 것이 현재 기준입니다.

## `mission.materials[]`

| 필드 | 타입 | 설명 |
|---|---|---|
| `material_id` | string | 자료 ID. `tasks[].required_materials`에서 참조 |
| `type` | string | 자료 유형. `chart`, `table`, `memo`, `email`, `schedule`, `checklist`, `log`, `card` 등 |
| `subtype` | string | 세부 유형 |
| `title` | string | 자료 제목 |
| `description` | string | 자료 설명 |
| `factual_status` | string | 현재는 합성 미션 자료임을 나타내는 값 |
| `used_for` | string | 자료가 미션에서 쓰이는 목적 |
| `evidence_source` | array | 실제 `job_profile.evidence.*[].name`에 존재해야 하는 evidence 이름 |
| `mission_fact_refs` | array | `mission_facts`에서 참조하는 필드명 |
| `data` | object | 자료 유형별 실제 내용 |
| `confidence` | object | 자료 생성 근거에 대한 자체 confidence |

`evidence_source`는 XML 파일명이나 URL이 아닙니다. `job_profile.evidence` 안에 있는 evidence 이름입니다. validator는 이 이름이 실제 profile evidence에 있는지 확인한 뒤, 해당 evidence의 `source_ref`를 찾아 `evidence_chain`에 다시 구성합니다.

## `materials[].data`

자료 유형에 따라 주로 보는 필드는 다음입니다.

| `material.type` | 주요 `data` 필드 | 설명 |
|---|---|---|
| `chart` | `chart_type`, `x_axis`, `y_axis`, `series` | 차트 데이터 |
| `table` | `columns`, `rows` | 표 데이터 |
| `memo` | `author`, `items` | 메모 항목 |
| `email` | `thread` | 이메일 스레드 |
| `schedule` | `columns`, `rows`, `items` | 일정표. 표 데이터와 timeline 항목을 모두 표시 가능 |
| `checklist` | `items` | 점검 항목 |
| `log` | `entries` | 시간순 로그 |
| `card` | `cards` | 카드형 정보 |

UI exporter는 `material.type`에 맞는 renderer를 먼저 사용합니다. 학습자용 화면에서는 `source_ref`, `confidence`, `evidence_source` 같은 내부 메타데이터를 제거합니다.

## `mission.tasks[]`

| 필드 | 타입 | 설명 |
|---|---|---|
| `task_id` | string | 내부 task ID |
| `instruction` | string | 학습자에게 보이는 지시문 |
| `required_materials` | array | 이 task가 참조해야 하는 material id 목록 |
| `expected_action` | string | 내부 기대 행동. 학습자용 HTML에서는 숨김 |

`required_materials` 값은 반드시 `materials[].material_id` 중 하나여야 합니다.

## `mission.submission_format`

| 필드 | 타입 | 설명 |
|---|---|---|
| `type` | string | 제출 형식. 예: `short_text` |
| `estimated_time_minutes` | integer | 답변 작성 예상 시간 |
| `required_sections` | array | 답변에 포함해야 하는 섹션 |
| `length_hint` | string | 답변 길이 힌트 |

## `evaluation`

| 필드 | 타입 | 설명 |
|---|---|---|
| `expected_insights` | array | 좋은 답변에서 기대하는 통찰 |
| `rubric` | array | 채점 기준 |

`evaluation.rubric[]`의 주요 필드:

| 필드 | 타입 | 설명 |
|---|---|---|
| `criterion` | string | 평가 기준명 |
| `description` | string | 평가 기준 설명 |
| `points` | integer | 배점 |
| `linked_evidence` | array | 연결된 evidence 이름 |

학습자용 HTML에서는 기준명 정도만 간단히 보여주고, 배점과 linked evidence는 숨깁니다.

## `reliability`

| 필드 | 타입 | 설명 |
|---|---|---|
| `score` | number | 0~1 범위의 신뢰도 점수 |
| `raw_score` | integer | 100점 만점 환산 점수 |
| `passed` | boolean | validator 통과 여부 |
| `calculated_by` | string | 계산 주체. 현재 `validator.v1` |
| `human_review_required` | boolean | 사람 검토 필요 여부 |
| `warning_count` | integer | warning 개수 |
| `fail_count` | integer | fail 개수 |
| `repair_count` | integer | repair 횟수 |
| `score_breakdown` | object | 영역별 점수 |

## `evidence_chain`

| 필드 | 타입 | 설명 |
|---|---|---|
| `created_by` | string | evidence chain 생성 주체 |
| `source_exec_job` | object | 근거가 되는 수행직무 |
| `linked_evidence` | object | 관련 ability/knowledge/work activity evidence |
| `material_evidence_map` | array | 각 material과 evidence 이름의 매핑 |
| `items` | array | material별 source reference 추적 정보 |

`evidence_chain.items[].source_refs[]`에는 어떤 XML 파일/필드/index에서 온 정보인지가 들어갑니다.

## `system_decisions.json`

`system_decisions.json`은 LLM draft가 반드시 따라야 하는 기준값입니다.

| 필드 | 설명 |
|---|---|
| `schema_version` | 현재 `system_decisions.v1` |
| `job_cd`, `job_name` | 직업 코드와 이름 |
| `difficulty` | 난이도 정책 |
| `selected_exec_job` | 이번 미션에서 사용할 수행직무 |
| `primary_task_type` | 주 task 유형 |
| `secondary_task_types` | 보조 task 유형 |
| `allowed_material_types` | 사용할 수 있는 자료 유형 |
| `mission_design` | 미션 설계 방향 |
| `excluded_material_types` | 사용할 수 없는 자료 유형 |
| `generation_constraints` | 생성 시 지켜야 할 제한 |
| `decision_trace` | 결정 과정 로그 |
| `decision_warnings` | 결정 과정 경고 |

## `llm_input_package.json`

현재 기본 모드의 주요 필드:

| 필드 | 설명 |
|---|---|
| `schema_version` | 현재 `llm_input_package.v1` |
| `job_profile` | KNOW XML에서 만든 직업 profile |
| `system_decisions` | 생성 전 확정한 기준값 |
| `schema_constraints` | 출력 구조와 검증 제약 |
| `job_practice_sheet_background` | 직무조사시트 Markdown 배경지식 |

legacy `--mission-seed` 모드에서는 다음 필드가 들어갈 수 있습니다.

| 필드 | 설명 |
|---|---|
| `job_practice_profile_excerpt` | 구조화 실무 profile 일부 |
| `mission_seed` | normal 미션 설계 seed |

저장된 `llm_input_package.json`에는 `schema_constraints.structured_output_schema`가 포함됩니다. 실제 prompt 구성 시에는 이 큰 schema만 제거하고, 같은 schema를 OpenAI Responses API structured output 설정으로 전달합니다.

## `job_practice_sheet_background.json`

```json
{
  "schema_version": "job_practice_sheet_background.v1",
  "job_cd": "K000001080",
  "source_path": "data/additional_search/K000001080.md",
  "content_markdown": "...",
  "usage": "background_only"
}
```

역할:

- 미션의 현실감을 높이는 배경지식입니다.
- 학습자용 미션에 조사 출처, URL, raw memo를 직접 노출하면 안 됩니다.
- `schema_constraints`와 `system_decisions`가 항상 더 높은 우선순위입니다.
- 미션은 생성된 제공 자료만으로 풀 수 있어야 합니다.

## `validator_result_attempt_N.json`

| 필드 | 설명 |
|---|---|
| `schema_version` | 현재 `validator_result.v1` |
| `attempt` | 검사한 attempt 번호 |
| `status` | `pass`, `repair_required`, `discard` |
| `passed` | 통과 여부 |
| `repairable` | repair 가능 여부 |
| `discarded` | 폐기 여부 |
| `reliability` | validator가 계산한 점수 |
| `errors` | 실패 항목 |
| `warnings` | 경고 항목 |
| `checks` | 영역별 검사 결과 |
| `final_evidence_chain` | 최종 `mission_output.json`에 들어갈 evidence chain |

`errors[]`와 `warnings[]`는 보통 다음 필드를 가집니다.

| 필드 | 설명 |
|---|---|
| `path` | 문제가 발생한 JSON 경로 |
| `severity` | `fail` 또는 `warning` |
| `code` | 오류/경고 코드 |
| `message` | 문제 설명 |
| `required_fix` | 수정 방향 |
| `repairable` | 자동 repair 대상으로 볼 수 있는지 |

## Validation Rules to Remember

- `target_exec_job`, `mission.task_type`, `mission.secondary_task_types`, `mission.difficulty`는 `system_decisions`와 맞아야 합니다.
- `mission.materials[].type`은 `system_decisions.allowed_material_types` 안에 있어야 합니다.
- `image`, `screenshot`은 현재 제외된 자료 유형입니다.
- 모든 material은 `factual_status`, `evidence_source`, `mission_fact_refs`, `data`를 가져야 합니다.
- 모든 task의 `required_materials`는 실제 material id를 참조해야 합니다.
- `mission.scenario.glossary`는 필수이며, 항목이 있으면 `term`, `definition`을 모두 가져야 합니다.
- validator는 단순히 `인터넷`, `검색`, `외부 자료` 같은 표현이 있다는 이유만으로 막지 않습니다.
- validator가 통과해야만 최종 `mission_output.json`이 저장됩니다.
