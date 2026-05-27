# Data Requirements

이 프로젝트를 새 환경에서 실행하려면 공개 저장소에 포함되지 않는 로컬 데이터와 API key를 준비해야 합니다.

## Required Local XML

KNOW/고용24 원천 XML은 다음 위치에 둡니다.

```text
data/api_raw/{job_cd}/
  dtlGb_2.xml
  dtlGb_5.xml
  dtlGb_7.xml
  dtlGb_3.xml
```

예시:

```text
data/api_raw/
  K000001080/
    dtlGb_2.xml
    dtlGb_5.xml
    dtlGb_7.xml
    dtlGb_3.xml
```

필수 파일:

| 파일 | 용도 |
|---|---|
| `dtlGb_2.xml` | 직업 상세 정보와 직업명 |
| `dtlGb_5.xml` | 업무수행능력, 지식 등 생성 근거 |
| `dtlGb_7.xml` | 업무환경 등 생성 근거 |

선택 파일:

| 파일 | 용도 |
|---|---|
| `dtlGb_3.xml` | 추가 직업 정보가 있을 때 사용 |

`data/api_raw/`는 로컬 전용이며 public GitHub에 올리지 않습니다.

## Practice Sheet Markdown

현재 기본 생성 경로는 직무조사시트 Markdown을 배경지식으로 사용합니다.

```text
data/additional_search/{job_cd}.md
```

예시:

```text
data/additional_search/K000001080.md
```

이 파일은 `PracticeSheetBackgroundLoader`가 읽어 다음 구조로 `llm_input_package.json`에 넣습니다.

```json
{
  "schema_version": "job_practice_sheet_background.v1",
  "job_cd": "K000001080",
  "source_path": "data/additional_search/K000001080.md",
  "content_markdown": "...",
  "usage": "background_only"
}
```

현재 커밋된 직무별 Markdown은 공개 가능한 정리본입니다. 반면 `data/additional_search/raw/`는 조사 원천 파일이므로 커밋하지 않습니다.

## Current Reference Job Codes

최신 complete run을 재생성하려면 아래 7개 직무의 XML과 직무조사시트가 필요합니다.

| job_cd | 직업명 |
|---|---|
| `K000000872` | 광고·홍보·마케팅전문가 |
| `K000000997` | 상품기획자 |
| `K000001080` | 데이터분석가(빅데이터분석가) |
| `K000001179` | 투자분석가 |
| `K000001196` | 인사·교육·훈련사무원 |
| `K000001222` | 방송기자 |
| `K000007519` | 보험상품개발자 |

## API Key

실제 OpenAI API를 호출하려면 `OPENAI_API_KEY`가 필요합니다.

PowerShell 환경변수:

```powershell
$env:OPENAI_API_KEY="본인_API_KEY"
```

또는 프로젝트 루트의 `.env.local`:

```text
OPENAI_API_KEY=본인_API_KEY
```

`.env.local`, `.env`, `.env.*`는 GitHub에 올리지 않습니다.

## Python Import Path

`pyproject.toml`이나 `requirements.txt`는 아직 없으므로 실행 전에 `src`를 Python import 경로에 추가합니다.

```powershell
$env:PYTHONPATH="src"
```

## Sanity Check

데이터와 API key가 없어도 mock 실행으로 폴더 구조와 저장 흐름을 확인할 수 있습니다.

```powershell
python -m mission_generation.pilot_runner --mock --jobs K000000997 --difficulties normal --concurrency 1
```

실제 API 실행 전에는 테스트를 먼저 돌리는 것을 권장합니다.

```powershell
python -B -m unittest discover -s tests
```

## Recreate the Complete Reference Shape

최신 complete run과 같은 7개 직무 x 3개 난이도 구성을 실행하려면 다음처럼 지정합니다.

```powershell
python -m mission_generation.pilot_runner --jobs K000000872,K000000997,K000001080,K000001179,K000001196,K000001222,K000007519 --difficulties easy,normal,hard --concurrency 2
```

HTML까지 생성하려면:

```powershell
python -m mission_generation.ui_exporter --run-id pilot_v1_YYYYMMDD_HHMMSS --view both
```
