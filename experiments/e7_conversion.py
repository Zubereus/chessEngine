import sys, os, json, random, subprocess, chess
from pathlib import Path

if len(sys.argv) not in (2, 3):
    raise SystemExit("usage: e7_conversion.py OLD_ENGINE_ROOT [NEW_ENGINE_ROOT]")

roots = [
    ("old", os.path.abspath(sys.argv[1])),
    ("new", os.path.abspath(sys.argv[2] if len(sys.argv) == 3 else Path(__file__).resolve().parent.parent)),
]

def spawn(root): return subprocess.Popen([sys.executable, "engine_cli.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=dict(os.environ, ENGINE_ROOT=root))
rng = random.Random(4)
starts = []
for piece in (chess.QUEEN, chess.ROOK):
    while len([s for s in starts if s[1] == piece]) < 5:
        sq = rng.sample(range(64), 3)
        cb = chess.Board(None); cb.set_piece_at(sq[0], chess.Piece(chess.KING, True)); cb.set_piece_at(sq[1], chess.Piece(chess.KING, False))
        cb.set_piece_at(sq[2], chess.Piece(piece, True)); cb.turn = True
        if cb.is_valid() and not cb.is_game_over() and not cb.is_check(): starts.append((cb.fen(), piece))
for name, root in roots:
    p = spawn(root); res = []
    for fen, piece in starts:
        cb = chess.Board(fen); moves = []
        while not cb.is_game_over(claim_draw=True) and len(moves) < 140:
            if cb.turn:
                p.stdin.write(json.dumps({"fen": fen, "moves": moves, "ms": 150}) + "\n"); p.stdin.flush()
                mv = chess.Move.from_uci(json.loads(p.stdout.readline())["move"])
            else: mv = rng.choice(list(cb.legal_moves))
            cb.push(mv); moves.append(mv.uci())
        res.append("mate in %d" % (len(moves) // 2 + 1) if cb.is_checkmate() else "no mate (%s)" % ("draw" if cb.is_game_over(claim_draw=True) else "70 moves"))
    print(name, "KQ:", res[:5], "\n    KR:", res[5:], flush=True)
