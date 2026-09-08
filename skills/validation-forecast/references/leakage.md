# 누수 감사

## 실행 순서

데이터 수집 → split → 학습 전처리 → 학습 label → 입력 생성 → 예측 → 평가 경로를 실제 코드에서 추적한다. 각 단계에 사용하는 데이터 범위와 fit 상태의 버전을 남긴다. 전체 시계열을 먼저 분해·정규화한 뒤 나누는 경로는 거부한다. [P1 §3.5]

## 확인할 경계

| 경계 | 확인할 내용 | 통과시킬 수 없는 예 |
|---|---|---|
| 시간 | 입력 timestamp와 forecast origin의 선후 관계 | origin 이후 관측값을 학습 입력에 포함 |
| 학습 표본 | 입력 cutoff와 label의 마지막 관측 시각 | t에서 H8 학습 label에 t 이후 값을 포함 |
| 전처리 | fit 구간, 역변환, 인덱스 유지 | 전체 구간 평균으로 scaler fit, 양방향 보간, centered rolling |
| Feature | feature 선택·lag 선택·분해의 fit 범위 | test 상관계수로 외생변수 선택 |
| Calibration | calibration 예측이 OOS인지와 오차 실현 시각 | H8 결과가 아직 나오지 않았는데 잔차 pool에 포함 |
| 튜닝 | early stopping과 trial 선택에 쓰인 구간 | trial별 test RMSE를 보고 최적 설정 선택 |
| 평가 loader | 예상 키 전체, 마지막 batch 포함 | test `drop_last=True`, 실패 origin 삭제 |

필요한 purge/gap 길이는 학습 label 구간과 horizon 구조로 정한다. 모든 작업에 `gap=max_horizon`을 무조건 적용하거나 무조건 0으로 두지 않는다. [운영 정책]

## 외생변수

과거 관측값, origin에 이미 알려진 미래 변수, 아직 모르는 미래 변수를 구분한다. 달력·사전에 확정한 행사 일정은 알려진 미래 입력일 수 있다. 공급량·재고·환율의 실제 미래값은 일반적으로 그렇지 않다. 미래 외생변수가 필요하면 origin 이전 데이터로 별도 예측하고 그 예측 과정도 검증한다.

참고가격, 만기, 계약 롤오버, 뉴스 timestamp, 달력 집계의 기준을 남긴다. 동봉 스크립트는 외생변수 panel을 자동 생성하지 않는다.

## 사전학습 모델

checkpoint ID, release/version, 사전학습 데이터 범위와 사용 조건을 기록한다. fine-tuning, local context 입력, 단순 zero-shot을 구별한다. 사전학습 자료를 모르면 `unknown`이다. 알려진 중복이 있으면 clean track에 넣지 않는다.

모델 출시 전 과거 기간을 평가하는 retrospective 비교와 그 당시 배포 가능한 모델만 쓰는 historical-deployment 검증을 구분한다. “평가 데이터를 사전학습에 넣지 않았다”는 조건 하나로 이 두 실험이 같아지는 것은 아니다. 동봉 검사에서 pretraining audit은 증빙을 검토한 선언값이며 학습 corpus를 자동 검색하지 않는다. [U0 확장]

## 자동 검사와 코드 감사

동봉 검사는 중복/예상 밖 키, 누락, quantile 오류, 미래 fit·preprocess cutoff, hash 불일치를 찾는다. `fit_cutoff`와 `preprocess_cutoff`는 학습과 전처리에 사용한 시간 범위의 상한이다.

출력에 안전한 cutoff를 적어 놓고 내부에서 미래 자료를 사용한 프로그램은 이 검사만으로 찾을 수 없다. `reviewed`에는 실제 코드 경로, 데이터 범위 로그, fit 상태 hash, 테스트 결과를 근거로 남긴다. 평가 정답은 분리된 권한의 프로세스에서만 연다.

## 추가 회귀 실험

미래 값만 크게 바꿨을 때 이전 origin의 입력과 예측이 변하지 않는지 확인한다. 마지막 평가 batch를 제거하면 비교 부적합으로 판정되어야 한다. zero-shot과 fine-tuning을 같은 track에 넣었을 때도 검사한다.

통과 결과를 “누수 없음 보장”으로 쓰지 않고, 검사 범위·실행한 케이스와 미확인 경로를 함께 보고한다.
