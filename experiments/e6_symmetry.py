"""Colour symmetry: a position and its colour-swapped vertical mirror must get the same score for the side to move."""
import random
from bridge import *
from src.chess_replicated.evaluator import Evaluator
rng = random.Random(3)
bad = 0; N = 0; worst = 0
for g in range(120):
    cb = chess.Board()
    for ply in range(rng.randint(10, 90)):
        if cb.is_game_over(): break
        cb.push(rng.choice(list(cb.legal_moves)))
    if cb.is_game_over(): continue
    b1, _ = board_from_fen(cb.fen()); b2, _ = board_from_fen(cb.mirror().fen())
    e1, e2 = Evaluator.evaluate(b1), Evaluator.evaluate(b2)
    N = N + 1; d = abs(e1 - e2); worst = max(worst, d)
    if d: bad = bad + 1
print(f"{bad}/{N} positions score differently after mirroring the colours; worst difference {worst} cp")
