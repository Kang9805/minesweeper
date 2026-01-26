# 지뢰찾기

Django를 사용한 간단한 지뢰찾기 웹 게임.

## 설치 및 실행

1. 가상환경 활성화:
   ```bash
   source .venv/bin/activate
   ```

2. 의존성 설치:
   ```bash
   pip install -e .
   ```

3. 마이그레이션:
   ```bash
   python manage.py migrate
   ```

4. 서버 실행:
   ```bash
   python manage.py runserver
   ```

5. 브라우저에서 http://127.0.0.1:8000 접속.

## 게임 방법

- 왼쪽 클릭: 셀 열기
- 오른쪽 클릭: 플래그 토글
- 지뢰를 피해서 모든 안전한 셀을 열거나, 모든 지뢰에 플래그를 달면 승리.