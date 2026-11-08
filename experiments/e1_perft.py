import sys, time
from bridge import *

POSITIONS = {
    "startpos": ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 3),
    "kiwipete": ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 3),
    "promo_heavy": ("n1n5/PPPk4/8/8/8/8/4Kppp/5N1N b - - 0 1", 4),
    "pos3": ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 4),
    "pos4": ("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 3),
    "pos5": ("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 3),
    "pos6": ("r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", 3),
    "ep_pin": ("8/8/8/KPp4r/8/8/8/7k w - c6 0 1", 3),          # en-passant would expose king on the rank
    "castle_thru": ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", 3),
}

def perft_chess_queen_only(cb, d):
    return cb.legal_moves.count() if d == 1 else sum(
        (cb.push(m) or perft_chess_queen_only(cb, d - 1)) + (cb.pop() and 0) for m in list(cb.legal_moves))

def perft_engine(b, d):
    if d == 0: return 1
    n = 0
    for m in b.getAllLegalMove(b.turn):
        b.makeMove(m); n = n + perft_engine(b, d - 1); b.undoMove()
    return n

for name, (fen, depth) in POSITIONS.items():
    b, cb = board_from_fen(fen)
    for d in range(1, depth + 1):
        t = time.time()
        e = perft_engine(b, d); c = perft_chess_queen_only(cb, d)
        print(f"{name:12s} d{d}: engine={e:8d} python-chess={c:8d} {'OK' if e == c else 'MISMATCH'}  {time.time()-t:5.1f}s", flush=True)
