# Protocol과 데이터 계약

## 비교의 단위

`task = 목표 정의 × 단위 × 이용 가능한 정보 × origin 집합 × horizon 집합 × truth vintage`로 정한다. 모델만 바꾸고 나머지 조건을 유지한다. 서로 다른 입력 정보·예산·학습 방식의 결과는 별도 track으로 나누며 모델 계열은 설명용 태그로 보관한다. [P1 §3.1, §4.2; P2 §4.4]

현재 스크립트는 하나의 protocol에 동일한 목표 단위를 가진 시계열을 묶는다. 입력은 서로 같은 관측 timestamp 목록을 가져야 한다. 다른 주기, 서로 다른 달력, ragged panel은 별도 task나 외부 adapter로 처리한다. `frequency_label`은 설명이며 달력 주기를 자동 검증하는 필드가 아니다. 실제 horizon은 제공한 관측 격자의 인덱스 차이로 계산한다.

## 개발·최종 구간

개발 리더보드는 모델 선택 자료이다. 여기서 수백 개의 모델·설정을 반복 비교한 뒤 최고 점수를 최종 일반화 성능으로 제시하지 않는다. 검증 구간에서 튜닝하고 더 뒤의 미사용 구간을 최종 평가용으로 남긴다. 데이터가 작다면 외부 rolling 평가와 그 안의 시간순 튜닝을 설계하되 각 바깥 평가 구간을 다시 선택 자료로 쓰지 않는다. [P1 pp. 789–792; 운영 확장]

최종 구간에서는 모델 명세, 학습/업데이트 규칙, feature pipeline, calibration 방식과 가중치를 고정한다. 이미 실현된 test 관측을 후속 origin 학습에 쓰는 prequential 방식과 test 전체로 모델을 재선택하는 행위를 구분한다. [P1 §3.5, §4.1.2]

`final_selection.model_spec_hashes`는 미리 승인한 모델 명세의 SHA-256 목록이다. `locked_at`과 `approval_reference`도 남긴다. 새로운 모델·파라미터를 넣으면 scorer가 거부한다. 로컬 승인 문자열은 당사자의 선언이므로 조작 방지나 실제 사전 동결 증거를 대신하지 못한다. 최종 자료를 이미 본 경우에는 그 사실을 기록하고 새로운 미사용 기간이나 prospective 검증을 확보한다.

## Split과 재학습

충분한 표본과 비정상 시계열을 다루는 기본 경로는 chronological rolling-origin이다. `min_train_size`, expanding/sliding, `stride`, origin 시작/끝과 target 끝을 모두 지정한다. 특정 연도나 7:1:2 비율을 모든 데이터에 강제하지 않는다. TFB의 비율은 해당 실험의 설정이다. [P1 §4.1; P2 §4.1.1]

재학습은 `each_origin`, 정해진 주기, 최초 학습 후 입력만 갱신 등 실제 배포 방식에 맞춘다. 재학습 때 전처리도 정해진 자료에서 함께 fit한다. 모델은 고정해 놓고 scaler만 평가 자료에 다시 fit하는 식으로 조건을 섞지 않는다. 동봉 baseline 생성기는 `each_origin`만 지원하고 다른 정책은 외부 실행기가 담당한다. [P1 §4.1.2; P2 §4.3.1]

원시 시계열의 temporal split과 모델 훈련용 mini-batch shuffle을 혼동하지 않는다. 시간순으로 안전하게 만든 학습 표본을 훈련 내부에서 섞는 것까지 금지하는 규칙은 아니다.

P1은 충분히 적합된 정상 pure-AR 모델에서 randomized CV가 유효할 수 있는 조건도 다룬다. 이 스킬의 기본 경로가 chronological인 것은 보수적인 운영 선택이다. 예외를 쓰려면 정상성, 잔차 의존성, 외생변수와 상태 전달 여부를 검토하고 별도 protocol로 기록한다. [P1 §4.1.3–4.1.5]

## Target CSV

필수 컬럼은 `series_id,timestamp,available_at,value` 네 개이다. 시간은 UTC로 변환 가능한 timezone-aware ISO-8601이다. 행 하나는 특정 관측의 특정 공개/입수 버전이다.

- `timestamp`: 값이 가리키는 관측 시각. 발표 시각과 다르다.
- `available_at`: 그 버전이 실제 예측 시스템에서 사용 가능해진 시각. 발표와 수집 중 더 늦은 시점, 추가 지연이 있으면 그 지연까지 반영한다.
- `value`: 해당 버전의 값. 같은 관측의 수정본은 더 늦은 `available_at`을 가진 별도 행이다.

origin에서 `timestamp <= origin`이고 `available_at <= origin`인 행만 사용한다. 같은 관측에서는 그중 가장 늦게 이용 가능해진 버전을 선택한다. 역사적 수정본이 없고 현재의 최종 수정값만 있으면 real-time vintage 검증을 했다고 주장하지 않는다. 발표 지연만 반영한 검증과 수정 이력까지 재현한 검증을 분리한다. [U0 확장; P1 §3.5는 입수 가능성 원칙을 뒷받침]

동봉 planner는 학습 범위 안의 목표 관측이 하나라도 아직 이용 불가하면 멈춘다. 이를 행 삭제나 backward fill로 고쳐 달력·label을 바꾸지 않는다. 목표 자체가 지연 발표되는 nowcasting/ragged-edge 문제는 별도 실행기를 설계한다.

평가 정답은 모든 후보에 동일한 `truth_as_of` 기준으로 고정한다. 학습 시 사용한 당시 vintage와 평가 정답의 vintage는 다를 수 있으며 보고서에 명시한다. first-release truth가 필요하면 현재의 `latest available by truth_as_of` 정책을 조용히 바꾸지 말고 별도 adapter와 검사를 추가한다.

## 모델 후보·예산

`candidates`에는 실패 가능성이 있는 모델도 실험 전에 등록한다. 모든 등록 모델이 결과에 나타나며 미제출은 `MISSING_RUN`이다. 모델 설정을 여러 개 비교하면 별도의 model_id를 사용한다. seed별 운 좋은 실행만 골라 제출하지 않는다.

`budget` 문자열에는 wall time, HPO 횟수, CPU/GPU 종류·메모리, early stopping, 외부 API 비용 중 통제하는 항목을 구체적으로 적는다. 같은 trial 수가 같은 계산량을 뜻하지는 않는다. 동봉 scorer는 이 예산을 집행하지 않으므로 실제 로그와 profiler로 확인한다. [운영 확장]

## 동결 파일의 역할

`lock.json`에는 protocol, 데이터 hash와 평가 원장 hash를 남긴다. `origins.jsonl`에는 모델에 전달할 수 있는 일정만 들어간다. `expected.jsonl`에는 평가 정답이 있으므로 모델 개발자/adapter의 입력으로 전달하지 않는다.

`omitted_origins.jsonl`은 공통 warm-up이나 최대 horizon 경계 때문에 계획 단계에서 제외한 origin이다. 모든 모델에 동일하게 적용한다. 실행 후 실패한 예측을 이 파일로 옮겨 평가 대상을 줄이지 않는다.

Hash는 우발적 변경을 찾는 수단이다. 데이터 취득 시각, 승인 시각이나 비공개 유지 여부를 암호학적으로 증명하지 않는다.
