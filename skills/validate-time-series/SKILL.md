---
name: validate-time-series
description: "Design, audit, and execute time-series forecast validation with a locked protocol, point-in-time data checks, rolling-origin evaluation, matched naive baselines, multi-horizon metrics, and traceable leaderboards. Use for 시계열 예측 검증, 백테스트, 모델 비교, 리더보드, TSCV, forecast evaluation, leakage audits, or adding statistical, ML, deep-learning, and foundation models to a common benchmark. Optimized for GPT-6 Astra/Codex end-to-end execution; not causal-effect identification or an automatic trading system."
---

# 시계열 예측 검증

검증 규칙과 평가 대상을 먼저 고정하고 모델은 adapter로 연결한다. 결과를 바꿀 핵심 정보가 없으면 중간 승인 없이 가능한 작업을 끝까지 진행한다. 낮은 오차가 누수나 불공정한 비교를 정당화하지는 않는다.

## GPT-6 Astra 실행 원칙

- 현재 요청, 이전 대화, 프로젝트 파일에서 의도와 범위를 먼저 추론한다. 읽기·분석·로컬 산출물 작성처럼 이미 허용된 가역 작업은 바로 진행한다.
- 사용자가 “이거 검증 가능해?”, “비교 좀 도와줘”처럼 작업 의도를 표현하면 단순 능력 설명으로 끝내지 않는다. 정보만 묻는 요청이 아니라면 실제 작업 요청으로 해석한다.
- 질문은 답이 실험 결과나 비교 가능성을 실제로 바꿀 때만 한다. 질문이 필요해도 먼저 막히지 않은 조사·감사·초안 작성·기준선 준비를 끝내고, 한 번에 가장 중요한 질문만 한다.
- 사용자의 명시적 지시는 이 스킬의 일반 운영 지침보다 우선한다. 사용자가 protocol을 바꾸면 새 버전으로 반영한다. 다만 이미 본 test를 untouched holdout이라고 부르거나 누락 표본을 완전한 평가라고 부르는 등 사실관계와 검증 상태를 바꾸어 쓰지는 않는다.
- 사용자가 "검증해줘", "비교해줘", "리더보드 만들어줘"라고 요청하면 방법 설명에서 멈추지 말고, 접근 가능한 데이터와 도구로 실제 작업을 완료하고 결과 파일까지 만든다.
- 이 스킬 때문에 작업 일부를 멈추거나 사용자 의도와 다른 경로로 가야 한다면 `validate-time-series/SKILL.md`의 해당 절을 밝히고 필요한 문장만 짧게 인용한다. 명시된 규칙과 모델의 해석을 구분한다.
- 병렬 agent를 쓸 수 있고 독립적인 모델·데이터·코드 감사가 병렬화되면 위임한다. 최종 판단과 공통 protocol 적용은 한곳에서 합친다.
- 답변은 결론이나 현재 상태를 먼저 쓴다. 짧은 문단을 기본으로 하고, 순서·비교가 필요할 때만 목록과 표를 쓴다. 같은 말을 다른 표현으로 반복하지 않는다.
- 코드 변경 검증은 변경 위험에 맞춘다. 가장 작은 의미 있는 검사를 먼저 실행하고, 통과한 뒤에는 실패나 남은 위험이 있을 때만 범위를 넓힌다.

Astra용 prompt/API 설정을 바꾸거나 agent가 불필요하게 확인을 반복하면 [astra-prompting.md](references/astra-prompting.md)를 읽는다.

## 작업 경로

| 요청 | 수행할 작업 |
|---|---|
| 검증 체계 설계 | 데이터·업무 요구를 읽고 protocol, 후보 목록, 감사 항목을 작성한다. 실제 데이터가 없으면 초안으로 표시한다. |
| 모델 비교·실행 | 기존 실행기를 확인하고 기준선을 먼저 실행한다. 모델별 adapter가 만든 예측 원장을 같은 평가기로 채점한다. |
| 기존 결과 감사 | 점수표보다 split, 예측 원장, 전처리 코드, 튜닝 로그를 먼저 읽는다. 확인할 수 없는 항목은 통과 처리하지 않는다. |
| 리더보드 갱신 | protocol·데이터·평가 키가 같은지 확인한다. 조건을 바꾸면 새 버전이나 별도 track으로 분리한다. |
| 최종 평가 | 동결된 모델 명세를 확인한 뒤 최종 구간을 평가한다. 최종 구간을 보고 모델·가중치·임계값을 다시 고르지 않는다. |

## 필요할 때 읽을 자료

| 파일 | 읽는 시점 |
|---|---|
| [protocol.md](references/protocol.md) | 비교 조건, 개발/최종 평가, 데이터 계약을 정할 때 |
| [leakage.md](references/leakage.md) | 전처리, 외생변수, feature, 사전학습 모델을 감사할 때 |
| [adapters.md](references/adapters.md) | 기존 저장소를 연결하거나 후보 모델을 추가할 때 |
| [metrics-inference.md](references/metrics-inference.md) | 지표, 예측구간, 통계검정, 순위를 해석할 때 |
| [runtime.md](references/runtime.md) | 동봉 스크립트를 실행하거나 입출력 형식을 확인할 때 |
| [sources.md](references/sources.md) | 논문 근거와 운영 확장을 구분할 때 |
| [astra-prompting.md](references/astra-prompting.md) | GPT-6 Astra용 prompt, reasoning, tool workflow를 조정할 때 |

## 1. 목표와 이용 가능한 정보를 확정한다

프로젝트의 설정·스키마·기존 실행기를 먼저 읽는다. 이미 확인 가능한 값을 다시 묻지 않는다. 목표 변수와 단위, 예측을 내리는 시각과 시간대, horizon의 의미, 데이터 발표·수집 지연, 수정 이력, 검증 구간, 기본 지표, 튜닝 예산을 확인한다. `h=4`가 관측치 네 개 뒤인지 달력상 4주 뒤인지 구분한다.

관측 사실, 발표시각, 데이터 vintage, 논문 결과는 추정해 채우지 않는다. 반면 파일 구조나 명백한 기본 경로처럼 결과를 거의 바꾸지 않는 가역적 선택은 합리적으로 정하고 가정으로 기록한다.

목표와 연결되는 손실을 주 지표로 정한다. 가격 수준·변화량·수익률은 서로 다른 task다. 구매비용이나 수익을 평가하려면 거래·재고·실행비용 가정을 별도 명세로 둔다. 예측 정확도를 구매 성과나 인과 효과로 바꾸어 표현하지 않는다.

정보가 부족하면 전체 작업을 멈추지 않는다. 가능한 history-only 검증, schema 감사, baseline 준비, protocol 초안은 계속 진행하고 영향받는 주장만 `BLOCKED` 또는 `UNKNOWN`으로 표시한다. 빠진 값이 결과를 바꾸는 경우에만 집중 질문을 남긴다.

## 2. Protocol과 비교 대상을 동결한다

[설정 예시](assets/protocol.example.json)와 [schema](assets/protocol.schema.json)를 사용한다. 예시는 합성 주간 데이터용이며 실제 원자재에 검증된 설정이 아니다.

실험 전에 데이터 버전·truth vintage·forecast origins·horizons·전처리 학습 범위·재학습 주기, 주 지표·집계 가중치·seed·튜닝 예산·후보 목록·실패 처리·국면 정의를 고정한다. 개발 리더보드와 최종 holdout의 역할도 분리한다.

모델 계열 자체를 track 경계로 쓰지 않는다. 동일한 정보 집합, 학습 방식, 예산, 재학습 조건과 출력 목표를 쓰면 통계·ML·DL 모델도 같은 track에서 비교할 수 있다. zero-shot과 fine-tuning, target-history-only와 외생변수 사용처럼 조건이 다르면 track을 나눈다.

발표시점이나 vintage가 불명확한 데이터는 `UNKNOWN`으로 남긴다. 사용자가 명시적으로 protocol을 바꾸면 기존 결과를 덮어쓰지 말고 새 protocol/version으로 실행한다.

## 3. 누수와 평가 표본을 먼저 감사한다

| 검사 | 통과 조건 |
|---|---|
| 이용 가능 시각 | 각 입력과 수정본의 `available_at`이 forecast origin 이하이다. |
| 학습·전처리 | scaler, imputer, feature selection, 분해, 그래프 추정은 정해진 학습 구간에서만 fit한다. |
| 학습 label | 다중 horizon 학습 표본의 label 끝과 발표시점이 fit cutoff를 넘지 않는다. |
| 외생변수 | 알려진 미래 달력과 아직 모르는 미래 가격·수급을 구별한다. 후자의 실제 미래값은 넣지 않는다. |
| 교차 시계열 | 전역 모델이 다른 시계열의 미래 충격 정보를 먼저 보지 않는다. |
| 평가 표본 | 모든 후보가 같은 평가 키를 받는다. test `drop_last`, 성공 Fold만 남기기, 사후 horizon 삭제를 eligible 평가에 쓰지 않는다. |
| 모델 선택 | early stopping·튜닝·앙상블 가중치·구간 보정에 최종 test를 쓰지 않는다. |
| 사전학습 | checkpoint와 평가 데이터의 중복 근거를 기록한다. 미확인은 clean zero-shot이 아니다. |

Timestamp 검사만으로 전처리 코드의 누수까지 입증할 수는 없다. 실제 코드 경로와 로그를 조사한 뒤 `audit.status=reviewed`와 근거를 남긴다. 미래 데이터만 바꾼 재실행에서 과거 origin의 입력·전처리 상태·예측이 변하는지도 확인한다.

사용자가 누수나 표본 삭제가 있는 설정을 명시적으로 요청하면 가능한 경우 **diagnostic/sensitivity run**으로 실행할 수 있다. 해당 결과는 `INELIGIBLE`로 분리하고 공정한 leaderboard에 합치지 않는다.

## 4. 기준선부터 실행하고 후보를 확장한다

Naive를 필수 기준선으로 둔다. 계절성이 있으면 정당한 period의 seasonal naive를 추가하고 drift, 적절한 ARIMA/ETS, 선형 모델을 검토한다. 계절 모델을 비계절 ARIMA만으로 비교하지 않는다.

기존 TFB·fev·자체 실행기가 있으면 재사용한다. 모델 내부 평가 코드를 그대로 신뢰하지 말고 원시 예측을 공통 형식으로 내보내 다시 채점한다. 각 adapter에는 당시 이용 가능했던 학습/입력 데이터와 알려진 미래 변수, horizon만 전달한다.

작은 smoke run으로 shape, 시간 정렬, 평가 표본 수와 재학습 조건을 확인한다. 통과하면 사용자가 이미 정한 환경·예산 범위에서 다음 후보까지 계속 진행한다. 대규모 GPU/API 비용처럼 새 비용 결정이 필요한 경우에도 baseline·adapter 감사·실행 계획은 먼저 끝내고 비용에 관한 질문 하나만 남긴다.

지원하지 않거나 실패한 모델도 후보 목록에서 지우지 않는다. 설치하지 않은 모델을 실행했다고 보고하지 않는다.

## 5. 동일한 예측 원장을 채점한다

최소 키는 `series_id × origin × horizon × seed`다. target timestamp, 데이터/설정 hash, 모델/코드 버전, 사용 정보 cutoff와 실패 사유도 저장한다.

원래 단위의 MAE·MSE·RMSE·bias와 horizon별 OOS naive 대비 skill을 계산한다. MASE/RMSSE 분모는 각 origin의 학습 자료에서 구한다. 분모가 0이면 임의 epsilon으로 점수를 만들지 않는다. **MASE < 1만으로 동일 test의 naive를 이겼다고 결론내리지 않는다.** 같은 평가 키의 OOS naive 손실을 별도로 비교한다.

동봉 리더보드는 시계열×horizon별 `1 − model_metric / naive_metric`을 같은 가중으로 평균한다. 양수가 개선이다. 다른 단위의 원자재 raw RMSE를 그대로 평균하지 않는다. 전체 평균과 함께 horizon, 사전 정의한 국면, 연속 origin 블록, seed별 결과와 worst fold를 본다. 불완전한 후보의 성공 표본 점수는 진단용이며 순위에 넣지 않는다.

## 6. 불확실성과 통계적 차이를 분리한다

예측분포가 있으면 같은 quantile grid에서 pinball, coverage, width, interval score와 조건이 맞는 WIS를 계산한다. coverage만 높이고 구간이 과도하게 넓어진 결과를 개선으로 보고하지 않는다. 분위수만 있는데 정확한 CRPS를 계산했다고 쓰지 않는다.

Conformal 보정은 horizon별로 이미 실현된 calibration residual만 사용한다. 시간 의존성과 distribution shift가 있는 상황에 일반적인 교환가능성 기반 coverage 보장을 그대로 붙이지 않는다.

통계검정은 선택한 예측의 손실 차이를 대상으로 한다. overlapping origins와 seed를 독립 표본처럼 늘리지 않는다. 동봉 DM-HAC는 가정 검토 후 사용하는 대표본 진단이며 nested 비교·MCS·SPA를 대신하지 않는다. 비유의 결과도 동등성 증명은 아니다.

## 7. 개발 리더보드와 최종 평가를 분리한다

개발 결과로 후보를 고른 뒤 모델 명세·학습 정책·가중치·보정 절차를 동결한다. 그다음 최종 구간을 평가한다. rolling 평가에서 새로 실현된 값을 다음 origin 학습에 쓰는 규칙도 미리 고정한다.

최종 holdout을 보호하는 workflow에서만 `approval_reference`와 동결 hash를 요구한다. 개발용 분석·baseline·adapter 구현·리더보드 초안 때문에 별도 승인을 반복해서 묻지 않는다. 로컬 파일만으로 holdout 열람을 물리적으로 막을 수 없으므로 실제 비공개 최종 평가는 별도 권한의 평가 서비스나 담당자가 관리한다.

[보고서 틀](assets/report-template.md)을 사용한다. 첫 부분에 현재 판정과 핵심 근거를 둔다. 근거가 없으면 `미검증`, `표본 부족`, `미구현`으로 적는다. `ELIGIBLE`은 비교 조건을 충족했다는 뜻이지 배포 승인이나 미래 성능 보장이 아니다.

## 실행 자원

Python 3.11 이상과 `scripts/requirements.txt`의 패키지가 필요하다. `$SKILL_DIR`는 이 `SKILL.md`가 있는 실제 디렉터리다.

```bash
python "$SKILL_DIR/scripts/test_validation.py"
python "$SKILL_DIR/scripts/demo.py" --out ./ts-validation-demo
python "$SKILL_DIR/scripts/tsvalidate.py" --help
```

실제 자료는 demo와 분리하고 원본 자료와 이전 결과를 덮어쓰지 않는다. 동봉 실행기는 as-of baseline과 예측 원장 평가를 지원한다. 외생변수 모델 학습, full HPO, 분산 실행, CRPS, conformal 학습, MCS/SPA/Clark-West/Giacomini-White는 기본 구현에 포함하지 않는다. 필요한 경우 검증된 외부 라이브러리를 adapter로 연결하고 그 경계를 명시한다.

## 스킬 변경 후 확인

[행동 평가 사례](assets/behavior-evals.json)를 회귀 점검에 사용한다. 문서·prompt만 바꿨다면 링크·frontmatter·agent metadata 같은 구조 검사를 우선한다. 수치 로직이나 누수 판정을 바꿨다면 관련 단위 테스트를 실행하고, 통과 후에도 영향 범위가 넓을 때만 전체 테스트를 다시 돌린다. 테스트 통과와 실제 agent 작업 성공을 같은 것으로 보고하지 않는다.
