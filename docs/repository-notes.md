# 저장소 구성 근거

확인일: 2026-09-07. 아래는 저장소 구성에 참고한 내용입니다. 시계열 검증 방법론의 출처와 구분합니다.

| 참고 저장소 | 확인한 부분 | 반영한 내용 |
|---|---|---|
| [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | README의 기능·설치·언어별 안내 | 한국어/영어 README, 빠른 실행과 지원 범위 |
| [SEED Design](https://github.com/daangn/seed-design) | README의 소스·라이브러리·도구·문서 구분 | 스킬 본체와 저장소 관리 파일 분리, 단일 원본 유지 |
| [Diagram Design](https://github.com/cathrynlavery/diagram-design) | README, `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` | `skills/` 배치, Codex 플러그인과 마켓플레이스 메타데이터 |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | README, `AGENTS.md` | 기존 코드 재사용, 최소 의존성, 안전 검사와 작은 실행 테스트 |

SEED Design은 디자인 시스템 저장소입니다. 이번 작업은 프런트엔드나 도식을 만드는 작업이 아니므로 SEED 컴포넌트·스타일·이미지 자산을 종속성으로 추가하지 않았습니다. 네 저장소의 코드, 로고나 스크린샷도 복제하지 않았습니다.

한국어 문서는 [im-not-ai](https://github.com/epoko77-ai/im-not-ai)의 README에 제시된 의미 보존, 번역투·중복 표현·과도한 장식 회피 원칙을 참고했습니다.

## 공식 형식과 게시 명령

[OpenAI Build skills](https://learn.chatgpt.com/docs/build-skills)의 `SKILL.md`·참조 파일·실행 스크립트 분리와 사용자 설치 경로를 참고했습니다. [OpenAI Build plugins](https://learn.chatgpt.com/docs/build-plugins)의 최소 플러그인은 `.codex-plugin/plugin.json`과 `skills/`로 구성됩니다. 이번 패키지도 같은 구조입니다.

마켓플레이스는 Diagram Design에서 확인한 local source 형식을 사용합니다. 매니페스트 파일을 포함한 것과 실제 호스트에서 설치·호출을 검증한 것은 다릅니다. 이번 작업은 전자만 수행했습니다.

최초 게시 도구는 [GitHub CLI `gh repo create`](https://cli.github.com/manual/gh_repo_create)의 `--private`, `--source`, `--remote`, `--push`를 사용합니다. 로그인은 [gh auth login](https://cli.github.com/manual/gh_auth_login)을 따릅니다. 인증정보를 채팅에 입력하거나 저장소에 넣지 않습니다.

CI action은 확인 당시의 `actions/checkout` v4와 `actions/setup-python` v5 commit SHA로 고정했습니다. 이 선택은 최신 major 버전이라는 주장이 아닙니다.

## 최초 import의 보존 범위

입력은 `validate-time-series-v1.1.0-astra.zip`입니다. 최초 패키징에서는 기존 파일을 바꾸지 않고 경로만 `skills/` 아래로 옮겼습니다. 당시 hash는 import 기록이며 이후 변경본의 동일성을 보증하지 않습니다. 논문 PDF는 배포하지 않으며 기존 `references/sources.md`를 유지합니다.

기존 Astra 문서의 API 설정·가이드 접근 여부와 모델 동작을 이번 저장소 패키징에서 재검증하지 않았습니다. 모델 이름은 기존 프로파일 이름을 유지한 것이며, 설치 호환성이나 모델 성능 인증을 뜻하지 않습니다.

## 두 스킬로 분리한 구조 — 2026-09-08

[plan-forecast](../skills/plan-forecast/SKILL.md)는 실행 전 결정, [validation-forecast](../skills/validation-forecast/SKILL.md)는 예측 후 증빙 확인을 담당합니다. 공통 schema·evaluator·논문 reference는 후자에 한 벌만 유지합니다. 이 배포는 두 스킬을 함께 설치하는 묶음이며 plan-forecast 폴더만 복사하는 독립 배포는 지원하지 않습니다.

[Agent Skills 형식](https://agentskills.io/specification)의 이름·description·폴더 일치 규칙과 지침/참조/실행 파일 구분을 따릅니다. 통계적 기준을 새로 제안한 변경은 아닙니다. Plugin 식별자는 저장소 이름을 유지하고 두 SKILL.md를 발견하도록 `skills/`를 참조합니다.

원본 import와 초기 게시 allowlist의 경로·hash는 역사 기록으로 유지합니다. 현재 실행 경로는 README를 따르며 CI는 두 스킬, 공통 evaluator와 단계 경계를 검사합니다. 테스트된 소스 archive는 추적 파일만 포함하고 `.git`, 실행 데이터와 인증정보를 수집하지 않습니다.
