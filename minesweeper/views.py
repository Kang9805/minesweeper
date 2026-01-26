from django.shortcuts import render, redirect
import random

def index(request):
    if 'board' not in request.session:
        return redirect('new_game')
    board = request.session['board']
    revealed = request.session['revealed']
    flagged = request.session['flagged']
    game_over = request.session.get('game_over', False)
    won = request.session.get('won', False)
    rows = request.session.get('rows', 10)
    cols = request.session.get('cols', 10)
    board_data = []
    for r in range(rows):
        row = []
        for c in range(cols):
            cell = {
                'row': r,
                'col': c,
                'is_revealed': revealed[r][c],
                'is_flagged': flagged[r][c],
                'is_mine': board[r][c] == -1,
                'value': board[r][c] if board[r][c] > 0 else '',
            }
            row.append(cell)
        board_data.append(row)
    return render(request, 'minesweeper/index.html', {
        'board_data': board_data,
        'game_over': game_over,
        'won': won,
        'rows': rows,
        'cols': cols,
    })

def new_game(request, rows=10, cols=10, mines=10):
    if request.method == 'POST':
        rows = int(request.POST.get('rows', 10))
        cols = int(request.POST.get('cols', 10))
        mines = int(request.POST.get('mines', 10))
        mines = min(mines, rows * cols - 1)  # 최대 지뢰 수 제한
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
    if request.session.get('game_over', False):
        return redirect('index')
    board = request.session['board']
    revealed = request.session['revealed']
    rows = request.session['rows']
    cols = request.session['cols']
    if revealed[row][col]:
        return redirect('index')
    if board[row][col] == -1:
        request.session['game_over'] = True
        # Reveal all mines
        for r in range(rows):
            for c in range(cols):
                if board[r][c] == -1:
                    revealed[r][c] = True
    else:
        reveal(board, revealed, row, col, rows, cols)
        # Check win
        total_cells = rows * cols
        mines = request.session['mines']
        revealed_count = sum(1 for r in range(rows) for c in range(cols) if revealed[r][c])
        if revealed_count == total_cells - mines:
            request.session['won'] = True
    request.session['revealed'] = revealed
    return redirect('index')

def flag(request, row, col):
    if request.session.get('game_over', False):
        return redirect('index')
    flagged = request.session['flagged']
    flagged[row][col] = not flagged[row][col]
    request.session['flagged'] = flagged
    return redirect('index')

def reset(request):
    # Clear all session data
    request.session.flush()
    return redirect('index')

def reveal(board, revealed, row, col, rows, cols):
    if revealed[row][col]:
        return
    revealed[row][col] = True
    if board[row][col] == 0:
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    reveal(board, revealed, nr, nc, rows, cols)
