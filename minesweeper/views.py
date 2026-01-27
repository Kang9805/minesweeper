from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.urls import reverse
import random

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
        'remaining_flags': mines - current_flags,
    }

# HTMX 전용 응답 처리 함수
def render_game_response(request):
    context = get_game_context(request)
    if not context:
        return redirect('new_game')
        
    # HTMX 요청이면 조각(partial)만 리턴, 아니면 전체 페이지(index) 리턴
    if request.headers.get('HX-Request'):
        board_html = render_to_string('minesweeper/partials/board.html', context)
        status_text = (
            "💥 게임 오버!" if context['game_over'] else
            "🎉 승리!" if context['won'] else
            f"🚩 남은 깃발: {context['remaining_flags']}"
        )
        new_game_url = reverse('new_game')
        status_html = f'''
        <div id="status-bar" hx-swap-oob="innerHTML">
            <span>{status_text}</span>
            <a href="{new_game_url}" style="text-decoration:none; color:var(--link-color);">새 게임</a>
        </div>
        '''
        return HttpResponse(board_html + status_html)
    return render(request, 'minesweeper/index.html', context)


def index(request):
    context = get_game_context(request)
    if not context:
        return redirect('new_game')
    return render(request, 'minesweeper/index.html', context)

def new_game(request, rows=10, cols=10, mines=10):
    if request.method == 'POST':
        rows = int(request.POST.get('rows', 10))
        cols = int(request.POST.get('cols', 10))
        mines = int(request.POST.get('mines', 10))
        mines = min(mines, rows * cols - 1)

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
    
    return redirect('index')

def click(request, row, col):
    if request.session.get('game_over', False) or request.session.get('won', False):
        return render_game_response(request)

    board = request.session['board']
    revealed = request.session['revealed']
    flagged = request.session['flagged']
    rows, cols = request.session['rows'], request.session['cols']

    # 깃발이 있는 곳은 클릭 무시
    if revealed[row][col] or flagged[row][col]:
        return render_game_response(request)

    if board[row][col] == -1:
        request.session['game_over'] = True
        for r in range(rows):
            for c in range(cols):
                if board[r][c] == -1:
                    revealed[r][c] = True
    else:
        reveal_logic(board, revealed, row, col, rows, cols)
        
        # 승리 조건 체크
        revealed_count = sum(row.count(True) for row in revealed)
        if revealed_count == (rows * cols) - request.session['mines']:
            request.session['won'] = True

    request.session['revealed'] = revealed
    return render_game_response(request)

def flag(request, row, col):
    if request.session.get('game_over', False) or request.session.get('won', False):
        return render_game_response(request)

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
    return render_game_response(request)

def reset(request):
    request.session.flush()
    return redirect('index')

# 재귀적으로 빈 칸을 열어주는 로직 (함수명 중복 방지를 위해 _logic 추가)
def reveal_logic(board, revealed, row, col, rows, cols):
    if revealed[row][col]:
        return
    revealed[row][col] = True
    if board[row][col] == 0:
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    reveal_logic(board, revealed, nr, nc, rows, cols)