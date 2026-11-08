import random, itertools, collections
from bridge import *
rng = random.Random(5)
sets = collections.Counter(); diffs = collections.Counter(); N = 0
for _ in range(6000):
    cb = chess.Board(None)
    occupied = rng.sample(range(64), 8)
    cb.set_piece_at(occupied[0], chess.Piece(chess.KING, True)); cb.set_piece_at(occupied[1], chess.Piece(chess.KING, False))
    extras = rng.choice([[], [chess.BISHOP], [chess.KNIGHT], [chess.BISHOP]*2, [chess.KNIGHT]*2, [chess.BISHOP, chess.KNIGHT], [chess.PAWN], [chess.ROOK]])
    for i, pt in enumerate(extras):
        cb.set_piece_at(occupied[2 + i], chess.Piece(pt, rng.random() < 0.5))
    cb.turn = True
    if not cb.is_valid(): continue
    b, _ = board_from_fen(cb.fen())
    N = N + 1
    mine, ref = b.isInsufficientMaterial(), cb.is_insufficient_material()
    if mine != ref:
        key = tuple(sorted((chess.piece_name(p.piece_type), p.color) for p in cb.piece_map().values() if p.piece_type != chess.KING))
        diffs[(key, mine, ref)] = diffs[(key, mine, ref)] + 1
print(N, "positions; disagreements with python-chess:", sum(diffs.values()))
for k, v in diffs.items(): print("  ", v, k)
