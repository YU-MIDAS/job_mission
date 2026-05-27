# Public Artifact Policy

이 저장소는 public GitHub에 올리는 것을 전제로 정리되어 있습니다. 공개해도 되는 파일과 로컬에만 남겨야 하는 파일을 구분해 관리합니다.

## Commit Targets

| 대상 | 포함 이유 |
|---|---|
| `src/` | 미션 생성 코드 |
| `tests/` | 동작 검증 테스트 |
| `document/` | 공개용 프로젝트 설명 문서 |
| `data/additional_search/*.md` | 정리된 직무별 Markdown 조사시트 |
| `outputs/ui/v1/runs/{run_id}/mission_ui.html` | 검토자용 HTML |
| `outputs/ui/v1/runs/{run_id}/mission_learner.html` | 학습자용 HTML |
| `outputs/pilot/v1/runs/{run_id}/` | 공개 HTML과 매칭되는 원본 산출물 |

현재 공개 기준 run은 다음입니다.

```text
pilot_v1_20260527_032732_complete
```

## Local Only

| 대상 | 제외 이유 |
|---|---|
| `.env`, `.env.*`, `.env.local` | API key 등 민감 정보 |
| `data/api_raw/` | KNOW 원천 XML |
| `data/additional_search/raw/` | 조사 원본 파일과 양식 |
| `docx/` | 내부 작업 문서, 원본 문서, 메타데이터 가능성 |
| `share/` | 로컬 전달용 복사본 |
| `outputs/_test_tmp/` | 테스트 임시 산출물 |
| 공개 기준이 아닌 `outputs/pilot` run | 검토/시연 기준이 아닌 로컬 실행 결과 |
| 공개 기준이 아닌 `outputs/ui` run | 임시 HTML export |
| `*.tmp`, `*.bak`, 로그 파일 | 임시/편집기/실행 부산물 |

## Practice Sheet Rule

`data/`는 기본적으로 로컬 데이터 영역입니다. 다만 `data/additional_search/*.md`는 직무별로 정리된 공개 가능한 Markdown 조사시트이므로 커밋할 수 있습니다.

반대로 `data/additional_search/raw/`에는 원천 조사 파일, 양식, 합쳐진 원본 메모가 들어갈 수 있으므로 커밋하지 않습니다.

## Output Safety Rules

- API key를 코드, 문서, 커밋, 산출물에 남기지 않습니다.
- raw OpenAI request/response, Authorization header, raw prompt dump는 기본 저장하지 않습니다.
- 공개 HTML과 매칭되는 run만 선별해 올립니다.
- `mission_learner.html`은 학습자용으로 내부 ID, evidence, reliability, repair 정보를 숨기지만, 그래도 공개 전 secret scan을 통과해야 합니다.
- 내부 개발 과정 문서는 `docx/`에 로컬 보관하고 public repo에는 정제된 `document/`만 올립니다.

## If a Sensitive File Was Committed

실제 secret이 커밋되었다면 key를 즉시 폐기하고 새 key를 발급해야 합니다.

단순 경로나 내부 메모처럼 낮은 위험의 정보라도 public history에서 제거하고 싶다면 커밋을 amend하거나 history rewrite 후 force push가 필요합니다. force push 이후에도 이미 clone한 사람의 로컬 저장소에는 이전 커밋이 남아 있을 수 있으므로, public repo에 올리기 전 선별 기준을 먼저 확인하는 것이 가장 안전합니다.
