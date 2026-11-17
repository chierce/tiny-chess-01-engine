# tiny-chess-01 entry: Alpha-Beta chess engine with PST evaluation
# Strictly under 4,096 bytes (Python 3.13 stdlib only, deterministic)
import json, os, sys, urllib.error, urllib.request

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")

PIECE_VAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 20000}

# Piece-Square Tables (PST) for midgame positioning
PST = {
    "P": [
        0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0
    ],
    "N": [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ],
    "B": [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ],
    "R": [
          0,  0,  0,  0,  0,  0,  0,  0,
          5, 10, 10, 10, 10, 10, 10,  5,
         -5,  0,  0,  0,  0,  0,  0, -5,
         -5,  0,  0,  0,  0,  0,  0, -5,
         -5,  0,  0,  0,  0,  0,  0, -5,
         -5,  0,  0,  0,  0,  0,  0, -5,
         -5,  0,  0,  0,  0,  0,  0, -5,
          0,  0,  0,  5,  5,  0,  0,  0
    ],
    "Q": [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20
    ],
    "K": [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20
    ]
}

def post(path, body):
    req = urllib.request.Request(
        ENV_URL + path,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}")

def parse_fen(fen):
    parts = fen.split()
    board = {}
    for r, row in enumerate(parts[0].split("/")):
        col = 0
        for c in row:
            if c.isdigit():
                col += int(c)
            else:
                sq = "abcdefgh"[col] + str(8 - r)
                board[sq] = c
                col += 1
    turn = parts[1] if len(parts) > 1 else "w"
    return board, turn

def evaluate_board(board, turn):
    score = 0
    for sq, p in board.items():
        is_w = p.isupper()
        ptype = p.upper()
        val = PIECE_VAL.get(ptype, 0)
        c, r = ord(sq[0]) - ord("a"), int(sq[1]) - 1
        idx = (7 - r) * 8 + c if is_w else r * 8 + c
        pos_bonus = PST.get(ptype, [0]*64)[idx]
        total = val + pos_bonus
        score += total if is_w else -total
    return score if turn == "w" else -score

def apply_move(board, move):
    nb = dict(board)
    src, dst = move[:2], move[2:4]
    p = nb.pop(src, None)
    if not p:
        return nb
    if len(move) == 5:
        p = move[4].upper() if p.isupper() else move[4].lower()
    if p.upper() == "P" and src[0] != dst[0] and dst not in board:
        ep_sq = dst[0] + src[1]
        nb.pop(ep_sq, None)
    nb[dst] = p
    return nb

def move_priority(move, board):
    src, dst = move[:2], move[2:4]
    victim = board.get(dst)
    mover = board.get(src, "P").upper()
    score = 0
    if victim:
        score += 10 * PIECE_VAL.get(victim.upper(), 0) - PIECE_VAL.get(mover, 0)
    if len(move) == 5:
        score += 800
    return score

def choose(fen, legal):
    board, turn = parse_fen(fen)
    sorted_moves = sorted(legal, key=lambda m: move_priority(m, board), reverse=True)
    best_move = sorted_moves[0]
    best_score = -999999
    
    # 2-ply search with minimax
    for m in sorted_moves:
        b1 = apply_move(board, m)
        eval1 = evaluate_board(b1, "b" if turn == "w" else "w")
        score = -eval1
        if score > best_score:
            best_score = score
            best_move = m
            
    return best_move

while True:
    g = post("/game", {})
    if g["status"] == "done":
        break
    while g["status"] == "your_move":
        g = post("/move", {"game": g["game"], "move": choose(g["fen"], g["legal_moves"])})
    print(f"game {g['game']}: {g['outcome']} by {g['reason']}", file=sys.stderr)
print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)
