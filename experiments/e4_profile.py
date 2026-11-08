import cProfile, pstats, time, io
from bridge import *
from src.chess_replicated.alphabeta_fast import FastNegaMax
from src.chess_replicated.alphabeta import SortingHat
from src.chess_replicated.evaluator import Evaluator

fens = {"start": chess.STARTING_FEN,
        "kiwipete": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"}
for name, fen in fens.items():
    for depth in (3, 4):
        b, _ = board_from_fen(fen)
        e = FastNegaMax(b); t = time.time()
        mv, sc, done = e.search(depth)
        dt = time.time() - t
        print(f"{name:9s} depth {depth}: {e.node_count:7d} nodes {dt:6.2f}s  {e.node_count/dt:7.0f} nps  move={chess.square_name(to_chess_sq(mv.getStartPos()))}{chess.square_name(to_chess_sq(mv.getEndPos()))} score={sc}")

b, _ = board_from_fen(fens["kiwipete"])
pr = cProfile.Profile(); pr.enable()
FastNegaMax(b).search(3)
pr.disable()
s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(9); print(s.getvalue()[:2200])

print("--- root move ordering (SortingHat) sign check ---")
b, _ = board_from_fen("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")   # exd5 wins a pawn
moves = SortingHat.sortMove(b.getAllLegalMove(b.turn), b)
nm = lambda m: chess.square_name(to_chess_sq(m.getStartPos())) + chess.square_name(to_chess_sq(m.getEndPos()))
print("first 5 root moves after sorting:", [nm(m) for m in moves[:5]], "| exd5 is at index", [nm(m) for m in moves].index("e4d5"), "of", len(moves))
