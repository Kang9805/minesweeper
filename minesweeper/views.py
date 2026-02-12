from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
import random
import time

# 난이도별 설정
DIFFICULTY_SETTINGS = {
    'easy': {'rows': 8, 'cols': 8, 'mines': 10},
    'medium': {'rows': 12, 'cols': 12, 'mines': 30},
    'hard': {'rows': 16, 'cols': 16, 'mines': 40},
}

# 공통 데이터 포맷팅 헬퍼 함수
def get_game_context(request):
    if 'board' not in request.session:
        return None
        
    rows = request.session.get('rows', 10)
    cols = request.session.get('cols', 10)
    board = request.session['board']
    revealed = request.session['revealed']
    flagged = request.session['flagged']
    mines = request.session.get('mines', 10)
    start_time = request.session.get('start_time')
    end_time = request.session.get('end_time')

    if end_time is not None and end_time < start_time:
        end_time = None
        request.session['end_time'] = None
        request.session.modified = True

    now_ts = time.time()
    elapsed_seconds = 0
    if start_time is not None:
        elapsed_seconds = int((end_time or now_ts) - start_time)
    
    # 현재 꽂힌 깃발 수 계산
    current_flags = sum(row.count(True) for row in flagged)
    
    board_data = []
    for r in range(rows):
        row = []
        for c in range(cols):
            row.append({
                'row': r,
                'col': c,
                'is_revealed': revealed[r][c],
                'is_flagged': flagged[r][c],
                'is_mine': board[r][c] == -1,
                'value': board[r][c] if board[r][c] > 0 else '',
            })
        board_data.append(row)
        
    return {
        'board_data': board_data,
        'game_over': request.session.get('game_over', False),
        'won': request.session.get('won', False),
        'rows': rows,
        'cols': cols,
        'mines': mines,
        'remaining_flags': mines - current_flags,
        'difficulty': request.session.get('difficulty', 'custom'),
        'start_time': start_time,
        'end_time': end_time,
        'elapsed_seconds': elapsed_seconds,
    }

# HTMX 전용 응답 처리 함수
def render_game_response(request):
    context = get_game_context(request)
    if not context:
        return redirect('new_game')
        
    # 게임 보드 렌더링
    board_html = render_to_string('minesweeper/partials/board.html', context)
    
    # 상태 바를 OOB로 업데이트 (outerHTML 교체로 hidden/aria/data 속성까지 갱신)
    status_bar = render_to_string('minesweeper/partials/status-bar.html', context)
    if '<div' in status_bar:
        status_bar_oob = status_bar.replace('<div', '<div hx-swap-oob="outerHTML"', 1)
    else:
        status_bar_oob = status_bar

    return HttpResponse(board_html + status_bar_oob)


def index(request):
    context = get_game_context(request)
    if not context:
        # 세션이 없으면 세션에 저장된 난이도 값 또는 기본값으로 초기화
        context = {
            'board_data': [],
            'rows': request.session.get('rows', 10),
            'cols': request.session.get('cols', 10),
            'mines': request.session.get('mines', 10),
            'remaining_flags': request.session.get('mines', 10),
            'game_over': False,
            'won': False,
        }
    return render(request, 'minesweeper/index.html', context)

def new_game(request, difficulty=None, rows=10, cols=10, mines=10):
    # 난이도로부터 설정 로드
    if difficulty and difficulty in DIFFICULTY_SETTINGS:
        settings = DIFFICULTY_SETTINGS[difficulty]
        rows = settings['rows']
        cols = settings['cols']
        mines = settings['mines']
    # POST 요청으로부터 커스텀 설정 로드 (폼 제출)
    elif request.method == 'POST':
        rows = int(request.POST.get('rows', 10))
        cols = int(request.POST.get('cols', 10))
        mines = int(request.POST.get('mines', 10))
        max_mines = rows * cols - 1
        if mines > max_mines:
            return HttpResponse(
                f'폭탄 수는 최대 {max_mines}개까지 설정할 수 있습니다.',
                status=400
            )
        mines = min(mines, max_mines)

    # 지뢰판 생성 로직
    board = [[0 for _ in range(cols)] for _ in range(rows)]
    mine_positions = set()
    while len(mine_positions) < mines:
        r, c = random.randint(0, rows-1), random.randint(0, cols-1)
        mine_positions.add((r, c))
        
    for r, c in mine_positions:
        board[r][c] = -1
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != -1:
                    board[nr][nc] += 1
                    
    # 세션 초기화
    request.session['board'] = board
    request.session['revealed'] = [[False for _ in range(cols)] for _ in range(rows)]
    request.session['flagged'] = [[False for _ in range(cols)] for _ in range(rows)]
    request.session['game_over'] = False
    request.session['won'] = False
    request.session['rows'] = rows
    request.session['cols'] = cols
    request.session['mines'] = mines
    request.session['difficulty'] = difficulty or 'custom'
    request.session['start_time'] = None
    request.session['end_time'] = None
    request.session['first_click_done'] = False
    
    # HTMX 요청이면 전체 in-game 컨테이너를 반환하여 화면 전환합니다
    if request.headers.get('HX-Request'):
        context = get_game_context(request)
        # render full in-game partial (status bar + board area)
        play_html = render_to_string('minesweeper/partials/game-play.html', context)
        return HttpResponse(play_html)
    
    return redirect('index')

def click(request, row, col):
    if request.session.get('game_over', False) or request.session.get('won', False):
        return HttpResponse(status=204)

    if request.session.get('start_time') is None:
        request.session['start_time'] = time.time()
        request.session['end_time'] = None

    board = request.session['board']
    revealed = request.session['revealed']
    flagged = request.session['flagged']
    rows, cols = request.session['rows'], request.session['cols']
    
    # 첫 클릭 안전 보장: 첫 클릭 위치와 주변 3x3 영역에 지뢰가 없도록 재배치
    if not request.session.get('first_click_done', False):
        request.session['first_click_done'] = True
        
        # 클릭한 위치와 주변 칸 좌표 수집
        safe_positions = set()
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    safe_positions.add((nr, nc))
        
        # 현재 지뢰 위치 수집
        mine_positions = set()
        for r in range(rows):
            for c in range(cols):
                if board[r][c] == -1:
                    mine_positions.add((r, c))
        
        # 안전 영역에 있는 지뢰를 다른 곳으로 이동
        mines_to_move = mine_positions & safe_positions
        if mines_to_move:
            # 가능한 빈 칸 찾기
            all_positions = {(r, c) for r in range(rows) for c in range(cols)}
            available_positions = list(all_positions - mine_positions - safe_positions)
            
            for old_pos in mines_to_move:
                if available_positions:
                    new_pos = available_positions.pop(0)
                    mine_positions.remove(old_pos)
                    mine_positions.add(new_pos)
            
            # 보드 재생성
            board = [[0 for _ in range(cols)] for _ in range(rows)]
            for r, c in mine_positions:
                board[r][c] = -1
                # 주변 숫자 업데이트
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != -1:
                            board[nr][nc] += 1
            
            request.session['board'] = board

    # 이미 공개된 칸은 클릭 무시
    if revealed[row][col]:
        return HttpResponse(status=204)
    
    # 깃발이 있는 칸을 클릭하면 깃발 자동 해제 후 공개
    if flagged[row][col]:
        flagged[row][col] = False
        request.session['flagged'] = flagged

    if board[row][col] == -1:
        request.session['game_over'] = True
        for r in range(rows):
            for c in range(cols):
                if board[r][c] == -1:
                    revealed[r][c] = True
    else:
        reveal_logic(board, revealed, flagged, row, col, rows, cols)
        
        # 승리 조건 체크: 모든 안전한 칸을 공개하면 승리
        revealed_count = sum(row.count(True) for row in revealed)
        if revealed_count == (rows * cols) - request.session['mines']:
            request.session['won'] = True

    if (request.session.get('game_over') or request.session.get('won')) and not request.session.get('end_time'):
        request.session['end_time'] = time.time()

    request.session['revealed'] = revealed
    request.session.modified = True
    return HttpResponse(status=204)

def flag(request, row, col):
    if request.session.get('game_over', False) or request.session.get('won', False):
        return HttpResponse(status=204)

    if request.session.get('start_time') is None:
        request.session['start_time'] = time.time()
        request.session['end_time'] = None

    flagged = request.session['flagged']
    revealed = request.session['revealed']
    mines = request.session['mines']
    current_flags = sum(row.count(True) for row in flagged)

    if not revealed[row][col]:
        if flagged[row][col]: # 이미 깃발이 있으면 해제
            flagged[row][col] = False
        elif current_flags < mines: # 깃발이 없고 갯수 여유가 있으면 설치
            flagged[row][col] = True

    request.session['flagged'] = flagged

    # 승리 체크: 모든 안전한 칸을 공개하면 승리
    rows = request.session.get('rows')
    cols = request.session.get('cols')
    board = request.session.get('board')
    revealed_count = sum(r.count(True) for r in request.session['revealed'])
    if revealed_count == (rows * cols) - mines:
        request.session['won'] = True

    if request.session.get('won') and not request.session.get('end_time'):
        request.session['end_time'] = time.time()

    request.session.modified = True
    return HttpResponse(status=204)

def reset(request):
    rows = request.session.get('rows', 10)
    cols = request.session.get('cols', 10)
    mines = request.session.get('mines', 10)
    difficulty = request.session.get('difficulty', 'custom')

    request.session.flush()
    request.session['rows'] = rows
    request.session['cols'] = cols
    request.session['mines'] = mines
    request.session['difficulty'] = difficulty
    return redirect('index')

def game_state(request):
    """게임 상태를 JSON으로 반환 (204 응답 후 상태 폴링용)"""
    context = get_game_context(request)
    if not context:
        return JsonResponse({'error': 'no_game'}, status=400)
    
    return JsonResponse({
        'board_data': context['board_data'],
        'game_over': context['game_over'],
        'won': context['won'],
        'remaining_flags': context['remaining_flags'],
        'start_time': context['start_time'],
        'end_time': context['end_time'],
        'elapsed_seconds': context['elapsed_seconds'],
    })

# 재귀적으로 빈 칸을 열어주는 로직 (함수명 중복 방지를 위해 _logic 추가)
def reveal_logic(board, revealed, flagged, row, col, rows, cols):
    # 이미 공개되었거나 깃발이 꽂혀있으면 무시
    if revealed[row][col] or flagged[row][col]:
        return
    revealed[row][col] = True
    if board[row][col] == 0:
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    reveal_logic(board, revealed, flagged, nr, nc, rows, cols)