# JSON Field Reference

이 문서는 미션 생성 과정에서 만들어지는 주요 JSON 파일의 필드가 무엇을 의미하는지 설명합니다. 처음 보는 사람은 `mission_output.json`을 먼저 보고, 문제가 생겼을 때 `validator_result_attempt_N.json`, `llm_call_result_attempt_N.json`, `system_decisions.json`을 함께 확인하면 됩니다.

JSON에서 `title`, `task_type`, `difficulty` 같은 이름은 보통 필드, 키, 속성이라고 부릅니다. 이 문서에서는 가장 일반적인 표현인 필드라는 말을 사용합니다.

## Main JSON Files

| 파일 | 위치 | 역할 |
|---|---|---|
| `mission_output.json` | `outputs/pilot/v1/runs/{run_id}/jobs/{job_cd}/{difficulty}/` | 검증을 통과한 최종 미션 |
| `llm_input_package.json` | 같은 미션 폴더 | LLM에 전달한 입력 패키지 |
| `system_decisions.json` | 같은 미션 폴더 | 시스템이 먼저 정한 직무, 난이도, 자료 유형 결정값 |
| `schema_constraints.json` | 같은 미션 폴더 | LLM 출력 JSON이 따라야 할 구조와 제약 |
| `llm_call_result_attempt_N.json` | 같은 미션 폴더 | N번째 LLM 호출 결과 |
| `mission_draft_attempt_N.json` | 같은 미션 폴더 | N번째 LLM 초안 |
| `validator_result_attempt_N.json` | 같은 미션 폴더 | N번째 초안 검증 결과 |
| `repair_request_attempt_N.json` | 같은 미션 폴더 | 검증 실패 후 수정 생성을 요청할 때의 입력 |
| `run_status.json` | 같은 미션 폴더 | 해당 직업/난이도 미션의 최종 상태 요약 |
| `artifact_index.json` | `outputs/pilot/v1/runs/{run_id}/` | run 안에 있는 각 미션 산출물 경로 색인 |

`attempt_N`의 `N`은 생성 시도 번호입니다. `attempt_0`은 최초 생성이고, 검증 후 수정이 필요하면 `attempt_1`이 만들어집니다. 현재 설정은 최대 1회 repair를 기준으로 합니다.

## `mission_output.json`

`mission_output.json`은 최종 결과 원본입니다. HTML 검수 화면은 이 JSON을 사람이 보기 쉽게 보여주는 용도입니다.

### Top-Level Fields

| 필드 | 타입 | 설명 |
|---|---|---|
| `schema_version` | string | 출력 스키마 버전. 현재 `mission_output.v1` |
| `mission_id` | string | 최종 미션 ID. 예: `mission_K000000997_normal_001` |
| `job_identity` | object | 미션이 대상으로 삼는 직업 정보 |
| `target_exec_job` | object | 직업 설명 중 이번 미션에 사용할 수행직무 |
| `mission_facts` | object | 미션 자료와 문항이 공통으로 참조하는 합성 사실 |
| `mission` | object | 학습자에게 제시될 실제 미션 내용 |
| `evaluation` | object | 기대 통찰과 채점 기준 |
| `reliability` | object | validator가 계산한 신뢰도와 검증 결과 |
| `evidence_chain` | object | 최종 미션 자료가 직업 profile evidence와 어떻게 연결되는지의 추적 정보 |

LLM 초안 단계의 `mission_draft_attempt_N.json`에는 `evidence_chain_draft`가 있고, `reliability`는 `{ "status": "pending_validation" }` 상태입니다. 최종 조립 단계에서는 `evidence_chain_draft`가 제거되고 validator가 만든 `evidence_chain`과 계산된 `reliability`가 들어갑니다.

### `job_identity`

| 필드 | 타입 | 설명 |
|---|---|---|
| `job_cd` | string | KNOW 직업 코드 |
| `job_lrcl_nm` | string | 직업 대분류명 |
| `job_mdcl_nm` | string | 직업 중분류명 |
| `job_smcl_nm` | string | 직업 소분류명, 실제 직업명 |
| `source_ref` | object | 이 직업 정보가 나온 원천 XML 위치 |

### `source_ref`

| 필드 | 타입 | 설명 |
|---|---|---|
| `file` | string | `data/api_raw` 아래의 상대 파일 경로 |
| `field` | string | XML에서 참조한 필드 이름 |
| `index` | integer 또는 null | 여러 항목 중 몇 번째 항목인지 나타내는 번호 |

### `target_exec_job`

| 필드 | 타입 | 설명 |
|---|---|---|
| `exec_job_id` | string | 수행직무 ID. 예: `exec_004` |
| `text` | string | 실제 수행직무 문장 |
| `source_ref` | object | 수행직무가 나온 원천 XML 위치 |
| `selection_reason` | string | 이 수행직무를 선택한 이유 |

`target_exec_job`은 `system_decisions.selected_exec_job`과 같아야 합니다.

### `mission_facts`

| 필드 | 타입 | 설명 |
|---|---|---|
| `org_name` | string | 미션 안에서 사용하는 가상의 조직명 |
| `domain` | string | 미션의 업무/상품/데이터 영역 |
| `period` | array | 자료에서 사용하는 기간 목록 |
| `trend_pattern` | string | 자료에 반영되는 핵심 흐름 |
| `main_issue` | string | 학습자가 판단해야 하는 중심 문제 |
| `feedback_themes` | array | 고객 반응, 이슈, 제약 등 정성적 단서 |
| `decision_goal` | string | 미션에서 최종적으로 내려야 하는 판단 목표 |

`mission.materials[].mission_fact_refs`는 이 `mission_facts`의 필드명만 참조해야 합니다.

### `mission`

| 필드 | 타입 | 설명 |
|---|---|---|
| `title` | string | 미션 제목 |
| `task_type` | string | 주 과업 유형. `system_decisions.primary_task_type`에서 복사 |
| `secondary_task_types` | array | 보조 과업 유형 목록 |
| `difficulty` | object | 난이도 정책 |
| `scenario` | object | 학습자에게 주어지는 업무 상황 |
| `materials` | array | 학습자가 검토할 자료 묶음 |
| `tasks` | array | 학습자가 수행해야 할 문항/지시 |
| `submission_format` | object | 제출물 형식과 분량 안내 |

### `difficulty`

| 필드 | 타입 | 설명 |
|---|---|---|
| `level` | string | 난이도 코드. 현재 `easy`, `normal`, `hard` |
| `label` | string | 화면 표시용 난이도명 |
| `estimated_time_minutes` | integer | 예상 소요 시간 |
| `material_bundle_style` | string | 자료 묶음 스타일 |
| `material_count_range` | array | 자료 개수 범위. 현재 easy `[1,1]`, normal `[2,2]`, hard `[3,3]` |
| `task_count_range` | array | 문항 개수 범위. 현재 easy `[1,1]`, normal `[2,2]`, hard `[2,2]` |
| `answer_length_hint` | string | 답안 분량 힌트 |
| `requires_cross_material_reasoning` | boolean | 여러 자료를 연결해야 하는지 여부 |
| `requires_tradeoff_judgment` | boolean | 대안 간 trade-off 판단이 필요한지 여부 |
| `requires_domain_expertise` | boolean | 별도 전문지식이 필요한지 여부. 현재 미션은 false를 지향 |

### `scenario`

| 필드 | 타입 | 설명 |
|---|---|---|
| `role` | string | 학습자가 맡는 역할 |
| `context` | string | 업무 상황 설명 |
| `goal` | string | 달성해야 할 목표 |
| `constraints` | array | 풀이 시 지켜야 할 제약 |

### `materials[]`

| 필드 | 타입 | 설명 |
|---|---|---|
| `material_id` | string | 자료 ID. `tasks[].required_materials`에서 참조 |
| `type` | string | 자료 유형. 예: `chart`, `table`, `memo`, `email`, `schedule`, `checklist`, `log`, `card` |
| `subtype` | string | 자료의 세부 유형 |
| `title` | string | 자료 제목 |
| `description` | string | 자료 설명 |
| `factual_status` | string | 현재 `synthetic_mission_material`이어야 함 |
| `used_for` | string | 이 자료가 미션 풀이에 쓰이는 목적 |
| `evidence_source` | array | 직업 profile의 evidence 이름 목록 |
| `mission_fact_refs` | array | `mission_facts`에서 참조한 필드명 목록 |
| `data` | object | 자료 유형별 실제 내용 |
| `confidence` | object | 자료 생성 자체에 대한 내부 점검 정보 |

`evidence_source`에는 XML 파일명이나 임의 라벨이 아니라 `job_profile.evidence` 안의 `name` 값이 들어가야 합니다.

### `materials[].data`

현재 구조화 출력 스키마는 자료 유형별 필드를 하나의 고정 객체 안에 담습니다. 그래서 실제 산출물에는 `material.type`과 직접 관련 없는 하위 필드가 빈 배열 또는 빈 문자열로 함께 들어갈 수 있습니다. 해석할 때는 먼저 `material.type`을 확인한 뒤 해당 유형에 맞는 필드를 보면 됩니다.

| `material.type` | 주로 보는 `data` 필드 | 설명 |
|---|---|---|
| `chart` | `chart_type`, `x_axis`, `y_axis`, `series` | 선/막대/원형 차트 데이터 |
| `table` | `columns`, `rows` | 비교표 데이터. 현재 표는 `option`, `strength`, `weakness`, `priority` 키를 사용 |
| `memo` | `author`, `items` | 메모형 항목 목록 |
| `email` | `thread` | 발신자, 수신자, 제목, 본문이 있는 이메일 흐름 |
| `schedule` | `items` | 기간, 할 일, 제약으로 구성된 일정 |
| `checklist` | `items` | 점검 항목, 상태, 중요도 |
| `log` | `entries` | 시간, 행위자, 이벤트, 메모로 구성된 로그 |
| `card` | `cards` | 후보안 카드와 속성 |

### `tasks[]`

| 필드 | 타입 | 설명 |
|---|---|---|
| `task_id` | string | 문항 ID |
| `instruction` | string | 학습자에게 제시할 지시문 |
| `required_materials` | array | 이 문항을 풀 때 사용해야 하는 `material_id` 목록 |
| `expected_action` | string | 기대 행동. 예: `observe`, `compare`, `recommend` |

`required_materials`에 들어간 값은 반드시 `materials[].material_id`에 존재해야 합니다.

### `submission_format`

| 필드 | 타입 | 설명 |
|---|---|---|
| `type` | string | 제출물 형식 |
| `estimated_time_minutes` | integer | 제출물 작성 예상 시간 |
| `required_sections` | array | 답안에 포함해야 하는 섹션 |
| `length_hint` | string | 권장 답안 길이 |

### `evaluation`

| 필드 | 타입 | 설명 |
|---|---|---|
| `expected_insights` | array | 좋은 답안에서 기대하는 핵심 통찰 |
| `rubric` | array | 채점 기준 목록 |

`evaluation.rubric[]`의 주요 필드는 다음입니다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `criterion` | string | 평가 기준명 |
| `description` | string | 평가 기준 설명 |
| `points` | integer | 배점. 전체 합계는 100점을 권장 |
| `linked_evidence` | array | 기준과 연결되는 직업 profile evidence 이름 |

### `reliability`

| 필드 | 타입 | 설명 |
|---|---|---|
| `score` | number | 0~1 범위의 신뢰도 점수 |
| `raw_score` | integer | 100점 만점 원점수 |
| `passed` | boolean | validator 통과 여부 |
| `calculated_by` | string | 신뢰도 계산 주체. 현재 `validator.v1` |
| `human_review_required` | boolean | 사람 검수가 필요한지 여부 |
| `warning_count` | integer | warning 개수 |
| `fail_count` | integer | fail 개수 |
| `repair_count` | integer | repair를 거친 횟수 |
| `score_breakdown` | object | 영역별 점수 |

### `evidence_chain`

| 필드 | 타입 | 설명 |
|---|---|---|
| `created_by` | string | evidence chain 생성 주체 |
| `source_exec_job` | object | 근거가 되는 수행직무 |
| `linked_evidence` | object | 관련 활동, 능력, 지식, 업무환경 evidence |
| `material_evidence_map` | array | 각 자료가 어떤 evidence 이름으로 뒷받침되는지 |
| `items` | array | 자료별 source reference와 추적성 정보 |

`evidence_chain.items[].source_refs[]`의 `source_root`는 현재 `data/api_raw` 상대경로를 사용합니다.

## `system_decisions.json`

`system_decisions.json`은 LLM이 미션을 만들기 전에 시스템이 먼저 결정한 기준값입니다. LLM은 이 값을 바꾸면 안 됩니다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `schema_version` | string | 현재 `system_decisions.v1` |
| `job_cd` | string | 직업 코드 |
| `job_name` | string | 직업명 |
| `difficulty` | object | 난이도 정책. 최종 `mission.difficulty`에 복사됨 |
| `selected_exec_job` | object | 이번 미션에 사용할 수행직무. 최종 `target_exec_job`에 복사됨 |
| `primary_task_type` | string | 주 과업 유형. 최종 `mission.task_type`에 복사됨 |
| `secondary_task_types` | array | 보조 과업 유형. 최종 `mission.secondary_task_types`에 복사됨 |
| `allowed_material_types` | array | 이번 미션에서 사용할 수 있는 자료 유형 |
| `mission_design` | object | 미션 설계 방향 |
| `excluded_material_types` | array | 사용 금지 자료 유형 |
| `generation_constraints` | object | 생성 시 지켜야 할 언어, 보안, 외부검색 금지 등 제약 |
| `decision_trace` | array | 각 결정이 어떤 규칙으로 내려졌는지의 로그 |
| `decision_warnings` | array | 결정 과정의 경고 |

## `schema_constraints.json`

`schema_constraints.json`은 LLM 구조화 출력에 전달되는 JSON 스키마와 검증 규칙을 담습니다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `schema_version` | string | 현재 `schema_constraints.v1` |
| `output_schema` | string | LLM이 만들어야 하는 출력 스키마명 |
| `material_detail_schema` | string | 자료 상세 구조 버전 |
| `task_material_taxonomy` | string | task/material 분류 버전 |
| `difficulty_policy` | string | 난이도 정책 버전 |
| `json_only` | boolean | JSON만 출력해야 하는지 여부 |
| `required_top_level_fields` | array | 최종 JSON에 필요한 최상위 필드 목록 |
| `forbidden_fields` | array | LLM 초안에서 만들면 안 되는 필드 |
| `must_copy_from_system_decisions` | array | `system_decisions`에서 그대로 복사해야 하는 필드 |
| `material_rules` | object | 허용 자료 유형, evidence, synthetic material 규칙 |
| `mission_fact_rules` | object | `mission_facts` 참조 규칙 |
| `repair_policy` | object | repair 가능 횟수와 repair 범위 |
| `structured_output_schema` | object | OpenAI Responses API에 전달되는 strict JSON schema. 저장 산출물에는 남지만 draft prompt 본문에서는 제외됨 |

## `llm_input_package.json`

`llm_input_package.json`은 LLM에게 전달되는 전체 입력 묶음입니다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `schema_version` | string | 현재 `llm_input_package.v1` |
| `job_profile` | object | KNOW XML에서 만든 직업 profile |
| `system_decisions` | object | 시스템 결정값 |
| `schema_constraints` | object | LLM 출력 제약 |
| `job_practice_profile_excerpt` | object | 구조화 실무 profile 일부. 있을 때만 포함 |
| `mission_seed` | object | normal 난이도 미션 설계 seed. 있을 때만 포함 |

`job_profile`은 직업 원천 데이터에서 온 정보이고, `mission_seed`는 실무조사 profile을 바탕으로 미션 상황, 자료, task 방향을 더 구체화하기 위한 보조 설계안입니다.

저장된 `llm_input_package.json`은 디버깅과 산출물 추적을 위해 전체 `schema_constraints`를 보존합니다. 다만 실제 draft prompt를 만들 때는 prompt 전용 사본에서 `schema_constraints.structured_output_schema`만 제거합니다. 출력 형식은 prompt 본문이 아니라 OpenAI Responses API의 structured output 설정으로 강제됩니다.

## Attempt Files

### `llm_call_result_attempt_N.json`

| 필드 | 타입 | 설명 |
|---|---|---|
| `schema_version` | string | 현재 `llm_call_result.v1` |
| `provider` | string | `openai` 또는 `mock` |
| `api` | string | 호출 API. 현재 `responses` |
| `model` | string | 사용 모델명 |
| `call_type` | string | `draft_generation` 또는 repair 관련 호출 유형 |
| `reasoning_effort` | string | 모델 reasoning effort 설정 |
| `configured_temperature` | number | 코드상 설정된 temperature |
| `temperature_applied` | boolean | 실제 요청에 temperature가 적용되었는지 여부 |
| `temperature_omitted_reason` | string | temperature를 생략한 이유 |
| `attempt_count` | integer | API 호출 시도 횟수 |
| `retry_count` | integer | retry 횟수 |
| `retry_errors` | array | retry 중 발생한 오류 |
| `status` | string | 호출 상태 |
| `output_json` | object | LLM이 반환한 JSON 초안 |
| `usage` | object | token 사용량 |
| `errors` | array | 호출 오류 |

### `mission_draft_attempt_N.json`

`mission_draft_attempt_N.json`은 `llm_call_result_attempt_N.json`의 `output_json`만 따로 저장한 파일입니다. 구조는 `mission_output.json`과 거의 같지만, 초안 단계이므로 `mission_id`는 `draft`이고 `reliability`는 아직 계산되지 않습니다.

### `validator_result_attempt_N.json`

| 필드 | 타입 | 설명 |
|---|---|---|
| `schema_version` | string | 현재 `validator_result.v1` |
| `attempt` | integer | 검증한 attempt 번호 |
| `status` | string | `pass`, `repair_required`, `discard` 중 하나 |
| `passed` | boolean | 통과 여부 |
| `repairable` | boolean | repair 가능한지 여부 |
| `discarded` | boolean | 폐기 여부 |
| `reliability` | object | validator가 계산한 점수 |
| `errors` | array | 실패 항목 |
| `warnings` | array | 경고 항목 |
| `checks` | object | schema, materials, tasks 등 영역별 점검 결과 |
| `final_evidence_chain` | object | 최종 `mission_output.json`에 들어갈 evidence chain |

`errors[]`와 `warnings[]`의 항목은 보통 다음 필드를 가집니다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `path` | string | 문제가 발생한 JSON 경로 |
| `severity` | string | `fail` 또는 `warning` |
| `code` | string | 오류/경고 코드 |
| `message` | string | 문제 설명 |
| `required_fix` | string | 수정 방향 |
| `repairable` | boolean | 자동 repair 대상으로 볼 수 있는지 여부 |

### `repair_request_attempt_N.json`

검증 실패 후 repair를 요청할 때 저장되는 입력입니다. 보통 `system_decisions`, 기존 `mission_output_draft`, validator의 `errors`, `warnings`, 그리고 repair 지침을 포함합니다.

## Run Summary Files

### `run_status.json`

| 필드 | 타입 | 설명 |
|---|---|---|
| `schema_version` | string | 현재 `mission_run_status.v1` |
| `run_id` | string | 전체 실행 ID |
| `job_cd` | string | 직업 코드 |
| `job_name` | string | 직업명 |
| `difficulty` | object | 난이도 코드와 라벨 |
| `status` | string | `saved`, `failed`, `discarded` 등 처리 상태 |
| `repair_count` | integer | repair 횟수 |
| `reliability_score` | number 또는 null | 최종 신뢰도 점수 |
| `warning_count` | integer | warning 개수 |
| `fail_count` | integer | fail 개수 |
| `artifacts` | object | 같은 폴더 안의 주요 산출물 파일명 |
| `error` | object 또는 null | 실패 시 오류 정보 |

### `artifact_index.json`

| 필드 | 타입 | 설명 |
|---|---|---|
| `schema_version` | string | 현재 `artifact_index.v1` |
| `run_id` | string | 전체 실행 ID |
| `items` | array | run 안에서 생성된 직업/난이도별 결과 목록 |

`items[]`에는 `job_cd`, `difficulty_code`, `status`, `mission_output_path`, `validator_result_path`, `run_status_path`가 들어갑니다.

## Validation Rules to Remember

- `target_exec_job`, `mission.task_type`, `mission.secondary_task_types`, `mission.difficulty`는 `system_decisions`에서 그대로 복사되어야 합니다.
- `mission.materials[].type`은 `system_decisions.allowed_material_types` 안에 있어야 합니다.
- `image`, `screenshot`은 현재 제외된 자료 유형입니다.
- 모든 material은 `factual_status`, `evidence_source`, `mission_fact_refs`, `data`를 가져야 합니다.
- 모든 task의 `required_materials`는 실제 존재하는 `material_id`를 참조해야 합니다.
- task 문항은 외부 검색이나 실제 법령, 실제 투자 판단 같은 외부 지식을 요구하지 않아야 합니다.
- `evaluation.rubric[].points`의 합계는 100점을 권장합니다.
- validator가 통과해야만 최종 `mission_output.json`이 저장됩니다.
