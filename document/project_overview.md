# Project Overview

이 프로젝트는 KNOW/고용24 직업 데이터를 바탕으로 직무형 학습 미션을 생성하는 Python 프로토타입입니다. 원천 XML에서 직업 정보를 읽고, 직무조사시트 Markdown을 배경지식으로 활용해 미션을 만든 뒤, validator로 검증하고 HTML 화면으로 내보냅니다.

처음 보는 사람은 이 문서를 먼저 읽고, 이어서 `mission_generation_flow.md`, `data_requirements.md`, `output_structure.md`, `json_field_reference.md`, `review_ui_guide.md` 순서로 보면 됩니다.

## What This Project Creates

| 결과물 | 위치 | 설명 |
|---|---|---|
| 최종 미션 JSON | `outputs/pilot/v1/runs/{run_id}/jobs/{job_cd}/{difficulty}/mission_output.json` | 실제 생성된 미션 원본 |
| 검토자용 HTML | `outputs/ui/v1/runs/{run_id}/mission_ui.html` | 내부 ID, evidence, reliability, repair 상태까지 보는 QA 화면 |
| 학습자용 HTML | `outputs/ui/v1/runs/{run_id}/mission_learner.html` | 내부 필드를 숨기고 실제 과제 화면처럼 정리한 학습자 화면 |

`mission_output.json`이 데이터 원본이고, HTML은 이 JSON들을 사람이 보기 쉽게 렌더링한 산출물입니다.

## Current Generation Defaults

현재 기본 실행은 `MissionDecisionSelector`와 직무조사시트 배경지식을 사용합니다.

| 항목 | 현재 동작 |
|---|---|
| 미션 틀 선택 | LLM selector가 수행직무, task 유형, 자료 유형을 먼저 고름 |
| 배경지식 | `data/additional_search/{job_cd}.md`를 `job_practice_sheet_background`로 입력 |
| legacy seed | 기본 미사용. `--mission-seed` 옵션을 줄 때만 사용 |
| 검증 | 구조, system_decisions 일치 여부, material/task 참조, evidence, glossary 검사 |
| 외부지식 키워드 | 단순 키워드만으로 차단하지 않음 |

## Pilot Jobs vs Reference Run

코드의 `default_pilot_config()`에 들어 있는 기본 pilot job은 4개입니다.

| job_cd | 직업명 |
|---|---|
| `K000000997` | 상품기획자 |
| `K000001080` | 데이터분석가(빅데이터분석가) |
| `K000001179` | 투자분석가 |
| `K000007519` | 보험상품개발자 |

현재 커밋된 기준 산출물 `pilot_v1_20260527_032732_complete`는 CLI에서 7개 job code를 직접 지정해 만든 complete run입니다.

| job_cd | 직업명 |
|---|---|
| `K000000872` | 광고·홍보·마케팅전문가 |
| `K000000997` | 상품기획자 |
| `K000001080` | 데이터분석가(빅데이터분석가) |
| `K000001179` | 투자분석가 |
| `K000001196` | 인사·교육·훈련사무원 |
| `K000001222` | 방송기자 |
| `K000007519` | 보험상품개발자 |

각 직무는 `easy`, `normal`, `hard` 3개 난이도로 생성되어 총 21개 미션을 이룹니다.

## Repository Map

| 위치 | 역할 |
|---|---|
| `src/mission_generation/` | 미션 생성 파이프라인 코드 |
| `tests/` | unittest 기반 테스트 |
| `document/` | 공개용 설명 문서 |
| `data/additional_search/*.md` | 커밋 가능한 직무별 조사시트 Markdown |
| `data/additional_search/raw/` | 조사 원천 파일. 커밋 제외 |
| `data/api_raw/` | KNOW 원천 XML. 로컬 전용 |
| `outputs/pilot/` | 공개 기준 run의 원본 실행 산출물 |
| `outputs/ui/` | 검토자용/학습자용 HTML |
| `docx/` | 내부 작업 문서. 커밋 제외 |
| `share/` | 로컬 전달용 파일 모음. 기본 커밋 제외 |

## Important Concepts

| 용어 | 의미 |
|---|---|
| `job_cd` | KNOW/고용24 직업 코드 |
| `difficulty` | 미션 난이도. `easy`, `normal`, `hard` 사용 |
| `run_id` | 한 번의 생성 실행을 구분하는 ID |
| `job_profile` | XML에서 추출한 직업 정보 |
| `system_decisions` | 미션 생성 전에 확정한 수행직무, task 유형, 자료 유형 |
| `job_practice_sheet_background` | 직무조사시트 Markdown을 배경지식으로 넣은 입력 필드 |
| `mission_seed` | legacy 생성 보조자료. 현재 기본 경로에서는 사용하지 않음 |
| `mission_output` | 검증을 통과한 최종 미션 JSON |
| `review UI` | 검토자용 QA HTML |
| `learner UI` | 학습자용 HTML |

## Public Repository Scope

이 저장소는 public GitHub에 올리는 것을 전제로 정리되어 있습니다. 실행 코드, 테스트, 공개 가능한 설명 문서, 직무별 조사시트 Markdown, 기준 run 산출물은 포함합니다. API key, 원천 XML, 조사 원본 파일, 내부 작업 문서, 임시 run은 포함하지 않습니다.

공개/비공개 기준은 `public_artifact_policy.md`를 참고하세요.
