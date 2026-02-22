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
        'game_id': request.session.get('game_id', ''),
    }

def render_game_response(request):
    context = get_game_context(request)
    if not context:
        return redirect('new_game')
        
    board_html = render_to_string('minesweeper/partials/board.html', context)
    
    # OOB로 상태바 outerHTML 교체
    status_bar = render_to_string('minesweeper/partials/status-bar.html', context)
    if '<div' in status_bar:
        status_bar_oob = status_bar.replace('<div', '<div hx-swap-oob="outerHTML"', 1)
    else:
        status_bar_oob = status_bar

    return HttpResponse(board_html + status_bar_oob)


def index(request):
    context = get_game_context(request)
    if not context:
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
    if difficulty and difficulty in DIFFICULTY_SETTINGS:
        settings = DIFFICULTY_SETTINGS[difficulty]
        rows = settings['rows']
        cols = settings['cols']
        mines = settings['mines']
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
                    
    import uuid
    game_id = str(uuid.uuid4())
    
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
    request.session['game_id'] = game_id
    
    if request.headers.get('HX-Request'):
        context = get_game_context(request)
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
    
    # 첫 클릭 안전 보장: 클릭 위치 및 주변 3x3 영역 지뢰 재배치
    if not request.session.get('first_click_done', False):
        request.session['first_click_done'] = True
        
        safe_positions = set()
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    safe_positions.add((nr, nc))
        
        mine_positions = set()
        for r in range(rows):
            for c in range(cols):
                if board[r][c] == -1:
                    mine_positions.add((r, c))
        
        mines_to_move = mine_positions & safe_positions
        if mines_to_move:
            all_positions = {(r, c) for r in range(rows) for c in range(cols)}
            available_positions = list(all_positions - mine_positions - safe_positions)
            
            for old_pos in mines_to_move:
                if available_positions:
                    new_pos = available_positions.pop(0)
                    mine_positions.remove(old_pos)
                    mine_positions.add(new_pos)
            
            board = [[0 for _ in range(cols)] for _ in range(rows)]
            for r, c in mine_positions:
                board[r][c] = -1
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != -1:
                            board[nr][nc] += 1
            
            request.session['board'] = board

    if revealed[row][col]:
        return HttpResponse(status=204)
    
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
        if flagged[row][col]:
            flagged[row][col] = False
        elif current_flags < mines:
            flagged[row][col] = True

    request.session['flagged'] = flagged

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

def reveal_logic(board, revealed, flagged, row, col, rows, cols):
    if revealed[row][col] or flagged[row][col]:
        return
    revealed[row][col] = True
    if board[row][col] == 0:
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    reveal_logic(board, revealed, flagged, nr, nc, rows, cols)

def hint(request):
    """힌트 기능: 공개되지 않은 안전한 칸 1개 자동 공개"""
    from django.http import JsonResponse
    
    if request.session.get('game_over', False) or request.session.get('won', False):
        return JsonResponse({'success': False}, status=400)

    if request.session.get('start_time') is None:
        request.session['start_time'] = time.time()
        request.session['end_time'] = None

    board = request.session.get('board')
    revealed = request.session.get('revealed')
    flagged = request.session.get('flagged')
    rows = request.session.get('rows', 10)
    cols = request.session.get('cols', 10)

    if not board or not revealed:
        return JsonResponse({'success': False}, status=400)

    safe_cells = []
    for r in range(rows):
        for c in range(cols):
            if not revealed[r][c] and not flagged[r][c] and board[r][c] != -1:
                safe_cells.append((r, c))

    if not safe_cells:
        return JsonResponse({'success': False}, status=400)

    import random
    hint_row, hint_col = random.choice(safe_cells)
    reveal_logic(board, revealed, flagged, hint_row, hint_col, rows, cols)

    request.session['board'] = board
    request.session['revealed'] = revealed
    request.session.modified = True

    revealed_count = sum(r.count(True) for r in revealed)
    won = False
    if revealed_count == (rows * cols) - request.session['mines']:
        request.session['won'] = True
        won = True

    if request.session.get('won') and not request.session.get('end_time'):
        request.session['end_time'] = time.time()

    mine_count = 0
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            nr, nc = hint_row + dr, hint_col + dc
            if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] == -1:
                mine_count += 1

    return JsonResponse({
        'success': True,
        'row': hint_row,
        'col': hint_col,
        'value': mine_count,
        'won': won
    })