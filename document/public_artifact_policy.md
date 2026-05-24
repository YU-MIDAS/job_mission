# Public Artifact Policy

이 저장소는 public GitHub에 올리는 것을 전제로 정리되어 있습니다. 공개해도 되는 파일과 로컬에만 남겨야 하는 파일을 구분해 관리합니다.

## Commit Targets

| 대상 | 포함 이유 |
|---|---|
| `src/` | 미션 생성 코드 |
| `tests/` | 동작 검증 테스트 |
| `document/` | 공개용 프로젝트 설명 문서 |
| `resources/practice_profiles/` | 공개 가능한 구조화 실무 profile |
| `outputs/ui/v1/runs/**/mission_ui.html` | 검수용 HTML |
| `outputs/profiles/v1/*.json` | 검수 UI 해석에 필요한 기준 profile |
| `outputs/pilot/v1/runs/{UI와_같은_run_id}/` | 공개 HTML과 매칭되는 원본 산출물 |

## Local Only

| 대상 | 제외 이유 |
|---|---|
| `.env`, `.env.*`, `.env.local` | API key 등 민감 정보 |
| `data/` | 원천 XML 및 로컬 데이터 |
| `docx/` | 내부 작업 기록, 원본 문서, 메타데이터 가능성 |
| `outputs/_test_tmp/` | 테스트 임시 산출물 |
| UI와 매칭되지 않는 `outputs/pilot` run | 공개 검수 대상이 아닌 로컬 실행 결과 |
| `*.tmp`, `*.bak`, 로그 파일 | 임시/편집기/실행 부산물 |

## Why `docx/` Is Excluded

`docx/`에는 개발 과정에서 만든 내부 분석 문서, 진행 기록, 원본 문서, HWP 파일 등이 들어갈 수 있습니다. 이런 파일은 프로젝트 이해에는 도움이 될 수 있지만 public GitHub에는 과한 정보가 될 수 있고, 문서 메타데이터가 남아 있을 가능성도 있습니다.

그래서 public repo에는 정리된 설명 문서만 `document/`에 올리고, 내부 작업 기록은 로컬에만 보관합니다.

## Output Safety Rules

- API key를 코드, 문서, 커밋, 산출물에 남기지 않습니다.
- raw OpenAI request/response, Authorization header, prompt dump는 기본 저장하지 않습니다.
- 공개 HTML과 매칭되는 run만 선별해 올립니다.
- 내부 개발 과정 문서는 `docx/`에 로컬 보관하고 public repo에는 정제된 `document/`만 올립니다.

## If a Sensitive File Was Committed

실제 secret이 커밋되었다면 key를 즉시 폐기하고 새 key를 발급해야 합니다. 단순 경로나 내부 메모처럼 낮은 위험의 정보라도 public history에서 제거하고 싶다면 커밋을 amend하거나 history rewrite 후 force push가 필요합니다.

force push 이후에도 이미 clone한 사람이 있다면 그 사람의 로컬 저장소에는 이전 커밋이 남아 있을 수 있습니다. public repo에 올리기 전 선별 기준을 먼저 확인하는 것이 가장 안전합니다.

