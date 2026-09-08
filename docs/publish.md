# GitHub 최초 게시

이 문서는 초기 비공개 게시 계획의 기록입니다. 현재 저장소 갱신과 2.0.0 배포에는 사용하지 않습니다. 최초 allowlist는 당시 파일 경로·hash를 보존하므로 새 구조의 게시 명세로 재사용하지 않습니다. 현재 설치·실행은 [README](../README.ko.md)를 따릅니다.

대상은 `immanuelk1m/validate-time-series`, 공개 범위는 비공개입니다. 패키지 작성 환경에서는 GitHub 계정 조회만 수행했으며 저장소 생성이나 푸시는 수행하지 않았습니다.

## 준비

Python 3.11 이상, Git, [GitHub CLI](https://cli.github.com/)가 필요합니다. GitHub CLI를 설치한 뒤 브라우저로 로그인합니다.

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git --hostname github.com
```

Git 커밋에 사용할 `user.name`과 `user.email`도 설정되어 있어야 합니다. 게시 도구는 이름이나 이메일을 임의로 만들지 않습니다. 이메일을 공개하고 싶지 않다면 GitHub에서 본인의 noreply 주소를 확인해 설정하세요.

## 실행

압축을 푼 저장소 루트에서 실행합니다.

```bash
python3 tools/publish_github.py
python3 tools/publish_github.py --execute
```

첫 명령은 파일 검증과 계획 출력만 합니다. 두 번째 명령은 로그인 계정이 `immanuelk1m`인지 확인하고, 새 로컬 Git 저장소와 첫 커밋을 만든 뒤 비공개 원격 저장소를 생성하여 푸시합니다. 성공하면 조회로 확인한 URL과 공개 범위를 출력합니다.

`repository-files.json`에 기록된 파일만 첫 커밋에 넣습니다. 원본 PDF, API 키, 추가 데이터 폴더를 자동으로 추가하지 않습니다. 최초 게시 전에 패키지 파일을 수정하면 hash 검사가 중단합니다. 의도적으로 수정한 작업물을 게시할 때는 diff를 검토하고 직접 Git 명령으로 진행하세요.

기존 `.git`이 있거나 원격 저장소가 이미 조회되면 도구는 중단합니다. 기존 저장소의 수정, 삭제, 강제 푸시, 공개 전환은 하지 않습니다. GitHub 인증이 없거나 권한이 부족해도 중단합니다.

## 실패 후 상태 확인

첫 커밋 뒤 네트워크 오류가 발생하면 로컬 `.git`은 남을 수 있고 원격 저장소가 생성되었을 수도 있습니다. 자동 재시도 대신 다음으로 상태를 확인합니다.

```bash
git status
git remote -v
gh repo view immanuelk1m/validate-time-series --json url,isPrivate,nameWithOwner
```

원격 주소와 비공개 상태가 맞고 첫 커밋만 푸시되지 않았다면 일반 `git push -u origin main`으로 재시도합니다. 원격이 없으면 `gh repo create immanuelk1m/validate-time-series --private --source=. --remote=origin --push`로 생성합니다. 조회의 404만으로 저장소가 없다고 단정하지 말고, 해당 계정의 접근 권한도 확인하세요.

GitHub 저장소 생성은 ChatGPT/Codex 플러그인 디렉터리 공개 심사나 설치 완료를 뜻하지 않습니다. 플러그인 설치와 실제 작업 성공은 별도 확인이 필요합니다.
