# GPT-6 Astra prompt 운영

이 문서는 `validate-time-series`를 GPT-6 Astra 중심으로 실행하거나 API/harness에 연결할 때만 읽는다. 시계열 검증의 과학적 규칙은 다른 reference에 있고, 여기서는 agent의 행동 방식과 모델 설정만 다룬다.

## 실행 목표

Astra에는 역할 설명보다 **완료할 일, 지켜야 할 경계, 성공 조건**을 분명히 준다. routine gap은 현재 문맥에서 추론하도록 하고, 결과를 바꿀 정보만 질문하게 한다. 질문 때문에 전체 workflow가 멈추지 않도록 질문 전까지 가능한 일을 먼저 끝내게 한다.

선택된 스킬의 완료 범위부터 고정한다.

- plan-forecast: 목표·TSCV·Fold·window·평가 규칙 결정 → 계획서·protocol·Fold 일정 동결. 결과 채점과 모델 학습은 수행하지 않는다.
- validation-forecast: 기존 계획·예측·로그 확보 → 실제 계획 준수 감사 → 고정 조건 채점·보고. split·window·지표를 결과에 맞춰 바꾸지 않는다.
- 전체 실행을 명시적으로 요청한 경우: plan-forecast → 별도 모델 실행 → validation-forecast. 한 단계의 완료를 다른 단계의 완료로 보고하지 않는다.

요청한 모드의 산출물까지 완성한다. 계획만 요청했는데 baseline 학습으로 확장하거나, 결과 검증 중 새 protocol을 만들어 사전 계획으로 쓰지 않는다. 사전 계획이 없으면 RETROSPECTIVE, 실행 증빙이 없으면 UNKNOWN으로 남긴다.

## 질문 정책

질문은 다음 중 하나에 해당할 때만 한다.

- 목표 변수나 horizon이 여러 후보 사이에서 갈리고 선택에 따라 결과가 달라진다.
- 새로운 유료 API/GPU 사용처럼 사용자가 정하지 않은 비용 결정이 필요하다.
- 비가역적 외부 변경이나 보호된 final holdout 접근처럼 별도 권한이 필요하다.

질문이 필요해도 선택한 모드에서 읽을 schema·파일·코드·기존 원장을 먼저 조사한다. 질문은 가장 큰 불확실성 하나에 집중한다. 답을 기다리는 동안 할 수 있는 다른 작업이 남아 있다면 멈추지 않는다.

## 지시 우선순위와 검증 불변식

사용자의 명시적 지시는 스킬의 일반적인 선택보다 우선한다. 예를 들어 sliding window로 바꾸라는 요청은 plan-forecast에서 새 protocol에 반영한다. validation-forecast가 기존 실행을 새 window로 수행한 것처럼 재해석하지 않는다.

반면 사실 상태를 바꾸지는 않는다. 다음은 prompt로 덮어쓸 수 있는 취향이 아니라 결과의 provenance다.

- 실제 미래 데이터를 썼다면 `no leakage`라고 쓰지 않는다.
- test를 보고 튜닝했다면 `untouched final`이라고 쓰지 않는다.
- 평가 행을 누락했다면 `complete`라고 쓰지 않는다.
- 실행하지 않은 모델에 점수나 로그를 만들지 않는다.
- 사전학습 중복을 확인하지 못했다면 `clean zero-shot`이라고 단정하지 않는다.

사용자가 이런 실험 자체를 원하면 가능한 경우 diagnostic run으로 수행하고, eligible benchmark와 분리한다. 사용자의 작업 의도는 최대한 수행하되 검증 상태는 정확하게 기록한다.

## 출력 방식

첫 문단에 현재 결과를 쓴다. 계획 모드에서는 동결 여부·Fold 수·미결정 사항, 검증 모드에서는 계획 준수·후보 판정·미확인 증빙을 제시한다.

설명은 짧은 문단을 기본으로 한다. 모델·horizon·track 비교처럼 행과 열이 실제로 필요한 경우에만 표를 쓴다. 목록은 단계나 서로 독립적인 항목에만 쓴다. 전문용어는 필요한 만큼 사용하되 새 약어와 인위적인 이름을 만들지 않는다.

실패는 마지막 각주로 숨기지 않는다. 리더보드와 같은 수준에서 `FAILED`, `INCOMPLETE`, `INELIGIBLE`, `UNKNOWN`을 보여준다.

## 병렬 작업

harness가 subagent를 지원하고 서로 독립적인 작업이 있으면 병렬화한다. 예를 들면 모델 adapter 조사, split 감사, 기존 benchmark 코드 확인은 나눌 수 있다. protocol 정의, 공통 metric과 최종 eligibility 판정은 한 기준으로 합친다.

작은 작업을 억지로 나누거나 동일 파일을 여러 agent가 동시에 수정하게 하지 않는다.

## 테스트와 검증

변경 위험에 비례해 검사한다.

- Markdown·prompt 변경: frontmatter, 상대 링크, agent metadata, JSON/YAML parse 같은 구조 검사부터 한다.
- metric·split·leakage 코드 변경: 직접 영향받는 단위 테스트와 작은 end-to-end fixture를 실행한다.
- 공통 evaluator 변경: 관련 검사가 통과한 뒤 전체 회귀 테스트를 실행한다.
- 실제 모델 adapter 변경: 작은 데이터/horizon으로 shape·timestamp·coverage를 확인한 뒤 전체 실행으로 넓힌다.

이미 통과한 검사를 이유 없이 반복하지 않는다. 실패, 새 변경, 미해결 위험이 생겼을 때만 범위를 넓힌다.

## API 또는 custom harness에서 Astra를 쓸 때

OpenAI 공식 모델 ID는 `gpt-6-astra`다. Tool calling을 쓰는 새 integration은 Responses API를 기본으로 한다. `reasoning.effort`는 `low`, `medium`, `high`, `xhigh`, `max`를 지원하며 `none`은 지원하지 않는다.

이 스킬의 권장 시작점은 다음과 같다.

| 작업 | 권장 시작 effort |
|---|---|
| schema 읽기, protocol 초안, 단순 adapter 연결 | `low` 또는 `medium` |
| 여러 모델 결과 감사, leakage 추적, 통계 검정 해석 | `medium` 또는 `high` |
| 복잡한 final audit, 다수 저장소/자료를 함께 검토 | `high` 또는 `xhigh` |
| 매우 어려운 장기 end-to-end 감사 | 필요할 때만 `max` |

이는 품질 보장이 아니라 비용·지연을 고려한 시작점이다. 실제 workload로 비교해서 조정한다.

Astra migration에서는 `temperature`, `top_p`, `top_logprobs` 같은 지원되지 않는 샘플링 파라미터를 억지로 유지하지 않는다. 장시간 tool workflow에서는 harness가 지원할 때 async tool calling, mid-turn steering, reasoning configuration update를 활용할 수 있다. 이 기능을 쓰지 않아도 시계열 검증 protocol은 달라지지 않는다.

## 출처

- OpenAI, *Model guidance — Using GPT-6 Astra*: initiative, instruction following, writing style, delegation, testing, migration guidance.
- OpenAI, *GPT-6 Astra model*: model ID, reasoning effort, context/output limits와 tool 지원.

세부 링크는 [sources.md](sources.md)에 기록한다.
