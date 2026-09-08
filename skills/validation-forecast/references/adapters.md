# 모델 연결과 실행

## 기존 실행기를 먼저 확인한다

TFB는 data, method, evaluation, reporting 계층을 분리하고 universal interface로 외부 구현을 연결한다. 새로운 모델 때문에 공통 평가 코드를 모델 저장소 안에 복제하지 않는다. 기존 TFB·fev·자체 backtester가 있다면 입력 데이터와 예측 원장 형식을 맞춘다. [P2 §4.4, Fig. 7]

이 패키지는 TFB/fev를 내장하거나 해당 라이브러리의 특정 버전 API를 구현하지 않는다. 설치된 버전의 공식 API를 읽고 adapter를 작성한다. 평가 split, 표본 수, 역변환과 점수는 이 스킬의 잠긴 명세에 맞는지 다시 확인한다.

## Adapter 계약

학습 요청에는 origin까지의 학습 입력·label·fit cutoff와 model config/seed를 전달한다. 예측 요청에는 origin, horizon/target timestamp, context, 명시적으로 알려진 미래 변수만 전달한다. `expected.jsonl`, test 정답과 아직 알 수 없는 미래 외생변수는 전달하지 않는다.

반환값은 원래 목표 단위의 point 예측과, 지원하는 경우 명세에 맞는 quantile dict이다. 별도 mean/median 출력을 지원하는 모델은 track의 point functional에 맞춰 선택한다. 지원하지 않는 예측구간을 임의로 생성하지 않는다.

모델은 fit/predict를 담당한다. 데이터 분할, 기준선 비교, 최종 점수 집계와 실패 처리의 기준은 공통 평가기가 담당한다. 전처리가 모델 전용이면 adapter가 소유하되 fit 범위·버전·역변환을 감사할 수 있게 기록한다. [P2 §4.4에서 확장한 실행 계약]

## 입출력 점검

| 항목 | Adapter 통과 조건 |
|---|---|
| Shape | 요청한 모든 series/origin/horizon/seed에 한 행씩 대응한다. |
| 정렬 | horizon과 target timestamp가 명세의 달력 격자와 맞는다. |
| 단위 | 정규화나 차분을 사용했으면 원래 목표 단위로 역변환한다. |
| Cutoff | 학습·전처리 cutoff가 forecast origin을 넘지 않는다. |
| Seed | 미리 지정한 seed를 모두 실행한다. 불가능하면 제한을 남긴다. |
| 학습 상태 | 최초 fit, 정기 재학습, state update를 구분한다. |
| 확률 출력 | 요청한 quantile grid, 유한값과 단조성이 맞는다. |
| 실패 | OOM, timeout, 비수렴, 미지원 horizon을 숨기지 않는다. |

순수 함수가 아닌 상태 보유 모델은 Fold/series 경계에서 상태가 잘못 재사용되는지 검사한다. 재귀 다중 단계와 direct multi-step은 구현 방식으로 명시한다. 평가 시점·정답은 같게 유지하되 한 방법을 다른 방법으로 바꾸었다고 가장하지 않는다. [P1 §3.1.2; P2 §4.4]

## 모델 실행 범위

동봉 baseline은 naive, drift, seasonal-naive 세 개이다. 결정적 모델이라 여러 seed에서 예측이 같아도 정상이다. seed를 복제해 통계검정 표본 수를 늘리지 않는다.

첨부 TFB에 등장하는 ARIMA, ETS, VAR, LR, Random Forest, XGBoost, N-BEATS, N-HiTS, DLinear, NLinear, TiDE, PatchTST 등을 후보로 검토할 수 있다. 현재 데이터 길이, horizon, 외생변수 지원, 라이선스와 자원 조건으로 실행 가능 여부를 확인한다. 이 패키지에 이들 adapter가 구현되어 있다는 뜻은 아니다. [P2 §4.2]

사전학습 모델도 정확한 checkpoint와 이용 조건을 확인한 뒤 별도 등록한다. 모델 이름만 나열한 목록을 “가능한 모델을 전부 실행한 결과”로 보고하지 않는다.

## 넓은 탐색의 실행 단계

초기에는 작은 task와 짧은 구간으로 adapter를 검사한다. 공통 평가 키를 지키고 naive 결과를 재현하면 승인된 개발 데이터에서 탐색한다. 비용이 큰 실험 전에는 task×origin×seed×trial의 대략적인 실행량과 중단 조건을 제시한다.

새 모델을 후보 목록에 추가할 때는 protocol을 갱신하고 새 cohort로 보관한다. 데이터·지표를 그대로 유지했더라도 통계검정의 비교 집합이 달라진 사실을 남긴다. 예산이 소진된 후보를 삭제하지 말고 미완료 상태로 기록한다.

앙상블 가중치와 모델 선택기도 하나의 학습 절차이다. 개발 자료에서 선택하고 최종 평가 전에 고정한다. test에서 가장 좋았던 모델을 시점별로 고른 oracle 결과는 참고 상한으로만 구분한다.
