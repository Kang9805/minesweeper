# Minesweeper (지뢰찾기)

Django + HTMX 기반 웹 지뢰찾기 서비스입니다.  
브라우저에서 바로 플레이할 수 있으며, 기록/통계/힌트/일시정지 기능을 제공합니다.

## 주요 기능

- 난이도 선택: 초급 / 중급 / 고급 / 커스텀
- 첫 클릭 안전 보장 (주변 3x3 안전 영역)
- 깃발 모드 및 남은 깃발 수 표시
- 힌트 시스템 (난이도별 제한)
   - 초급 5회 / 중급 3회 / 고급 1회 / 커스텀 0회
- 타이머 + 일시정지/재개
- 게임 종료 모달 (승리/패배)
- 로컬 기록 관리 (최고 기록, 평균 시간, 최근 게임, 연승 등)
- 룰북 패널(인게임 도움말)

## 기술 스택

- Backend: Django
- Frontend: Django Template, HTMX, Vanilla JavaScript
- Storage:
   - 서버 세션: 보드/게임 상태
   - localStorage: 개인 기록/통계/힌트 카운트

## 로컬 실행

1) 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2) 의존성 설치

```bash
pip install -r requirements.txt
```

3) 개발 서버 실행

```bash
python manage.py runserver
```

4) 브라우저에서 접속

```
http://127.0.0.1:8000/
```

## 조작 방법

- 좌클릭: 셀 열기
- 우클릭(PC): 깃발 설치/해제
- 롱프레스(모바일): 깃발 설치/해제
- ⏸ 버튼: 일시정지/재개
- 💡 버튼: 힌트 사용 (안전한 칸 자동 공개)

## 승리 / 패배 조건

- 승리: 지뢰가 아닌 모든 칸을 공개
- 패배: 지뢰 칸 클릭

## 프로젝트 구조

```text
config/                  # Django 설정
minesweeper/             # 게임 앱
   templates/minesweeper/
      index.html           # 메인 UI + 클라이언트 로직
      partials/            # 보드/상태바/폼 파셜
   views.py               # 게임 상태/클릭/깃발/힌트 로직
   urls.py                # 게임 라우팅
manage.py
```

## 향후 개선 아이디어

- 업적/배지 시스템
- 사운드 효과
- 애니메이션 강화
- 글로벌 랭킹(DB 기반)