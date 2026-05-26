# Project Overview

이 프로젝트는 KNOW/고용24 직업 데이터를 바탕으로 직무 미션을 생성하는 Python 프로토타입입니다. 원천 XML에서 직업 정보를 읽고, 직업별 업무 맥락과 난이도에 맞는 미션 JSON을 만든 뒤, 사람이 검수하기 쉬운 HTML 화면으로 내보냅니다.

처음 보는 사람은 이 문서를 먼저 읽고, 이어서 `mission_generation_flow.md`, `data_requirements.md`, `output_structure.md`, `review_ui_guide.md` 순서로 보면 됩니다.

## What This Project Creates

프로젝트가 최종적으로 만드는 핵심 결과물은 두 가지입니다.

| 결과물 | 위치 | 설명 |
|---|---|---|
| 최종 미션 JSON | `outputs/pilot/v1/runs/{run_id}/jobs/{job_cd}/{difficulty}/mission_output.json` | 실제 생성된 미션 데이터 |
| 검수용 HTML | `outputs/ui/v1/runs/{run_id}/mission_ui.html` | 브라우저에서 미션을 확인하는 화면 |

`mission_output.json`은 시스템이 사용하는 원본 데이터이고, `mission_ui.html`은 사람이 보기 위한 검수 화면입니다.

## Pilot Jobs

현재 기본 파일럿 대상은 다음 4개 직업입니다.

| job_cd | 직업명 |
|---|---|
| `K000000997` | 상품기획자 |
| `K000001080` | 데이터분석가(빅데이터분석가) |
| `K000001179` | 투자분석가 |
| `K000007519` | 보험상품개발자 |

기본 난이도는 `easy`, `normal`, `hard`입니다. 쉬움은 1자료/1 task, 보통은 2자료/2 task, 어려움은 3자료/2 task를 사용하며, 모든 task는 하나의 서술형 답변 행동만 갖도록 생성·검증합니다. 일부 `normal` 미션은 `resources/practice_profiles/`에 있는 구조화 실무 profile을 참고해 더 현실적인 업무 맥락을 반영합니다.

## Repository Map

| 위치 | 역할 |
|---|---|
| `src/mission_generation/` | 미션 생성 파이프라인 코드 |
| `tests/` | unittest 기반 테스트 |
| `document/` | 공개용 설명 문서 |
| `resources/practice_profiles/` | 공개 가능한 구조화 실무 profile |
| `outputs/profiles/` | 검수 UI 해석에 필요한 기준 job profile |
| `outputs/pilot/` | 공개 검수 UI와 매칭되는 원본 실행 산출물 |
| `outputs/ui/` | 브라우저 검수용 HTML |
| `data/` | 로컬 원천 데이터 위치이며 GitHub에는 올리지 않음 |
| `docx/` | 내부 작업 문서 위치이며 GitHub에는 올리지 않음 |

## Important Concepts

| 용어 | 의미 |
|---|---|
| `job_cd` | KNOW/고용24 직업 코드 |
| `difficulty` | 미션 난이도. 현재 `easy`, `normal`, `hard` 사용 |
| `run_id` | 한 번의 생성 실행을 구분하는 ID. 예: `pilot_v1_20260524_224708` |
| `job_profile` | XML에서 추출한 직업 정보 |
| `mission_seed` | 실무 profile을 바탕으로 만든 생성 보조자료 |
| `mission_output` | 검증을 통과한 최종 미션 JSON |
| `review UI` | 생성 미션을 브라우저에서 확인하는 HTML |

## Public Repository Scope

이 저장소는 public GitHub에 올리는 것을 전제로 정리되어 있습니다. 그래서 실행 코드와 공개 가능한 샘플 산출물은 포함하지만, API key, 원천 XML, 내부 개발 기록, 임시 산출물은 포함하지 않습니다.

공개/비공개 기준은 `public_artifact_policy.md`를 참고하세요.
