---
name: plan-forecast
description: "Plan time-series forecasting BEFORE model execution. Choose and freeze TSCV periods and fold counts, horizons, stride, expanding or sliding windows, refit and preprocessing rules, baselines, metrics, seeds, tuning budgets and holdout policy. Use for 예측 전 계획, 검증 설계, TSCV Fold 수·기간 설정, expanding/sliding window 선택. Produce a protocol and planned fold schedule, not forecasts or performance verdicts. Existing forecast results belong to validation-forecast."
---

# 예측 전 계획

모델을 실행하기 전에 **무엇을 어떤 조건으로 비교할지** 정한다. TSCV를 몇 번, 어느 기간에 실행할지와 expanding/sliding window 선택은 이 스킬의 책임이다. 결과가 계획대로 나왔는지 확인하는 일은 [validation-forecast](../validation-forecast/SKILL.md)에 넘긴다.

## 범위와 실행 원칙

현재 요청과 프로젝트 설정을 먼저 읽는다. 이미 정해진 target·horizon·예산을 다시 묻지 않는다. 정보가 부족해도 가능한 설계와 자료 점검은 진행하고, 결과를 바꾸는 미결정 사항만 질문한다. 데이터가 없으면 `DRAFT`로 작성하고 관측값·날짜·hash를 만들어 채우지 않는다.

계획만 요청받았다면 모델 학습, baseline 예측 생성, HPO, 점수 계산이나 리더보드 작성을 시작하지 않는다. 실행과 검증까지 명시적으로 요청받았다면 계획 동결 → 별도 모델 실행 → validation-forecast 순서로 진행한다. 단계별 완료 상태를 구분한다.

시간순 분할과 학습·전처리 누수 방지 규칙은 유지한다.

## 1. 목표와 비교 조건

목표 변수, 단위, 예측 기준 시점과 시간대, horizon의 뜻, 입력 변수, 평가 기간을 정한다. 가격 수준·변화량·수익률을 같은 task로 취급하지 않는다. `h=4`가 관측치 네 개 뒤인지 달력상 4주 뒤인지 기록한다. 동봉 실행기는 관측 격자의 인덱스 차이를 사용한다.

[Protocol 예시](../validation-forecast/assets/protocol.example.json)와 [schema](../validation-forecast/assets/protocol.schema.json)를 사용한다. 예시는 합성 자료 설정이다. 실제 데이터에 날짜나 계절 주기를 그대로 적용하지 않는다.

## 2. TSCV와 학습 창

[단계별 계약](../validation-forecast/references/stage-contract.md)에 따라 아래 값을 예측 전에 고정한다.

| 설계 항목 | 결정하고 남길 내용 |
|---|---|
| TSCV 방식·기간 | rolling-origin 사용 여부, origin 시작·끝, 마지막 평가 target 시점 |
| Fold 수 | 시계열별 실제 rolling Fold 수, 각 Fold의 train/target 시작·끝과 관측 수 |
| 학습 창 | expanding 또는 sliding, 최소 학습 길이, sliding의 최대 길이 |
| 예측 간격 | stride, horizon 목록과 단위, 겹치는 target 처리 |
| 재학습 | 매 origin 학습 또는 주기적 재학습의 fit 주기 |
| 내부 튜닝 | 내부 시간순 split, trial 예산, early stopping 구간, 바깥 평가와 분리 |
| Gap·purge | label 끝이 학습 경계를 넘지 않도록 필요한 구간과 근거 |
| 최종 평가 | 개발 구간과 final holdout 경계, 최종 모델 명세와 승인 방식 |

이 저장소의 기본 rolling Fold는 **시계열 하나의 origin 하나**다. 후보마다 다시 학습한다는 뜻은 아니며 refit 정책은 따로 정한다. `metrics.fold_origins`는 연속 origin을 묶는 **보고 블록 크기**다. 이를 TSCV Fold 수 설정으로 사용하지 않는다.

사용자가 Fold 수를 지정하면 실제 달력, warm-up, stride와 최대 horizon을 반영해 맞는지 확인한다. 요청 수와 다르면 결과를 버려 맞추지 말고 기간·간격 선택의 차이를 설명한다. `--expected-folds`는 시계열별 계획 수를 검사할 뿐 설정을 자동 변경하지 않는다.

Expanding은 시작점을 유지하고 학습 관측을 늘린다. Sliding은 최대 길이 안에서 시작점을 이동한다. 여기서는 window slicing을 고정 길이 sliding window의 의미로 구분한다. 선택 근거는 업무 조건과 개발 자료에서 찾고, 최종 test 점수를 보고 고르지 않는다.

임의 K-fold 분할, 내부 튜닝 split, gap/purge, 주기적 refit 실행은 현재 JSON 계약이 모두 표현하지 못한다. [계획서 틀](assets/plan-template.md)에 추가 명세와 담당 adapter를 기록한다. schema에 없는 속성을 넣거나 동봉 실행기가 지원한다고 쓰지 않는다.

## 3. 전처리·모델·평가 규칙

Imputer, feature/lag 선택과 분해의 fit 범위를 학습 Fold로 제한한다. Multi-horizon label 경계와 외생변수의 실제 미래값 사용 금지 규칙을 정한다. 이 단계에서는 규칙을 설계하며 실제 준수 판정은 예측 후에 한다.

Calibration 잔차는 사용자 선택 항목으로 두지 않는다. Calibration을 사용하는 경우 residual pool은 **horizon별로 분리**하는 공통 고정 규칙을 따른다. 예를 들어 H1 오차는 H1 보정에만, H4 오차는 H4 보정에만 사용한다.

Naive를 필수 비교 기준선으로 등록하고 drift와 seasonal naive의 필요성·계절 주기를 정한다. 후보 모델, 모든 seed, 정보 집합, 재학습 조건, 예산, mean/median 목표와 quantile grid를 사전 등록한다. 모델 계열만 다르다는 이유로 track을 나누지 않는다. Zero-shot과 fine-tuning처럼 비교 조건이 다르면 나눈다.

주 지표, 동일 OOS naive 대비 개선율, 집계 가중치, horizon·국면·보고 블록별 진단, 누락·실패 처리 방식을 정한다. 통계검정 여부와 가정·HAC lag·다중비교 집합도 미리 정하되 p-value는 계산하지 않는다. 사전학습 중복 정책, 비용과 라이선스는 [기존 실행 계약](../validation-forecast/references/adapters.md)을 따른다.

## 4. 동결과 인계

[계획서 틀](assets/plan-template.md)의 결정 근거를 작성한다. 설정이 정해지고 target CSV가 있으면 아래 실행기로 실제 계획을 만든다. `$SKILL_DIR`는 이 파일이 있는 plan-forecast 디렉터리다. 두 스킬을 같은 checkout에서 함께 설치해야 한다.

```bash
python "$SKILL_DIR/scripts/plan_forecast.py" \
  --protocol ./protocol.json --data ./target.csv --out ./experiment-v1
```

계획기는 `protocol.json`, `fold_plan.csv`, `planning_summary.json`, `plan/lock.json`, `plan/origins.jsonl`, `plan/omitted_origins.jsonl`과 평가 전용 `plan/expected.jsonl`을 만든다. `--expected-folds K`로 요청한 시계열별 Fold 수도 검사할 수 있다. 결과 폴더는 덮어쓰지 않는다.

`expected.jsonl`에는 정답이 있으므로 모델 adapter에 전달하거나 계획 선택에 쓰지 않는다. 동봉 lock은 정답이 있는 오프라인 벤치마크용이다. 보호된 final 자료는 권한이 있는 평가 담당자가 잠그고, 정답이 아직 없는 미래 예측은 설계 초안으로 남긴다. 로컬 hash가 사전 동결이나 holdout 비공개를 증명하지는 않는다.

계획의 `LOCKED`는 설정·달력을 고정했다는 뜻이다. **TSCV 실행 완료나 검증 통과를 뜻하지 않는다.** 모델 실행자에게 protocol, origin 일정과 fit 규칙을 넘기고 run.json, forecasts.jsonl, 실제 Fold/fit 로그, 전처리·튜닝 증빙을 받도록 명시한다. 예측 결과가 생긴 뒤 validation-forecast가 계획과 대조한다.

## 참고 자료와 변경 점검

[Protocol 계약](../validation-forecast/references/protocol.md), [누수 감사 기준](../validation-forecast/references/leakage.md), [지표 정의](../validation-forecast/references/metrics-inference.md), [실행 방법](../validation-forecast/references/runtime.md), [논문 근거](../validation-forecast/references/sources.md)를 필요한 부분만 읽는다. 공통 실행기와 schema는 validation-forecast에 한 벌만 둔다.

변경 후 두 스킬의 metadata·링크·단계별 행동 사례와 실행 테스트를 확인한다. 실제 호스트의 스킬 호출 시험과 Python 테스트 통과를 구분한다.
