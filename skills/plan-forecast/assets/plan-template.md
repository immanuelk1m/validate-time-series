# 예측 실행 계획

상태: [DRAFT / LOCKED]

## 목표와 자료

[목표 변수·단위·horizon의 의미·입력 정보·시간대·데이터 파일과 hash를 적는다. 자료가 없으면 미확인으로 남긴다.]

## TSCV와 학습 창

| 항목 | 결정값 | 선택 근거 |
|---|---|---|
| Origin 시작·끝 / 마지막 target | | |
| 시계열별 rolling Fold 수 | | |
| 각 Fold의 train/target 기간·관측 수 | fold_plan.csv | |
| Expanding / Sliding, 최소·최대 학습 길이 | | |
| Stride / horizon 목록·단위 | | |
| Refit 주기 | | |
| 내부 튜닝 split / gap·purge / label 끝 | | |
| 성능 보고 블록 크기·개수 | | |
| 개발 / 최종 holdout 경계 | | |

[요청 Fold 수와 실제 달력에서 나온 수를 비교한다. 보고 블록 수와 재학습 횟수는 별도다. 실행기가 지원하지 않는 분할·refit 정책은 담당 adapter와 구현 상태를 적는다.]

## 모델과 평가 정책

[전처리·feature/lag 선택 범위, 사전학습 중복 정책, 후보·seed·track·예산, 필수 naive와 계절 기준선, 주 지표·집계 가중치, 확률출력·통계검정·국면·실패 처리 기준을 정한다.]

Calibration residual pool은 별도 계획값을 받지 않는다. 사용 시 horizon별로 분리하며 H1 오차와 H4 오차를 같은 pool에 섞지 않는다.

## 실행자 인계

[protocol·origin 일정·fit 규칙·코드 명세와 비용 한도를 전달한다. expected.jsonl은 평가 담당자만 사용한다. run.json·forecasts.jsonl·Fold/fit·전처리·튜닝 로그를 반환받는다.]

## 미결정 사항과 완료 범위

[설계 결정과 구현 지원 여부를 구분한다. LOCKED라도 모델 학습·TSCV 실행·결과 검증은 미실행이다. 사전 holdout 비공개를 로컬 hash만으로 보장하지 않는다.]
