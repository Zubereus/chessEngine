from bridge import *
import random
from src.chess_replicated.chess_board import Board, Square, King, Rook, Queen, Pawn

print("--- 1. underpromotion (full chess rules vs engine) ---")
b, cb = board_from_fen("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8")
print("python-chess legal moves:", cb.legal_moves.count(), "| engine legal moves:", len(b.getAllLegalMove(b.turn)))
# stalemate trap: queen promotion stalemates, rook/knight promotion wins
b, cb = board_from_fen("7k/5P1P/6K1/8/8/8/8/8 w - - 0 1")
# f8=Q stalemate? use a cleaner known position
b, cb = board_from_fen("k7/2P5/1K6/8/8/8/8/8 w - - 0 1")   # c8=Q is stalemate? (black Ka8 has b8,b7 covered by Kb6/c8)
q = chess.Move.from_uci("c7c8q"); cb2 = cb.copy(); cb2.push(q)
print("c7c8=Q gives stalemate:", cb2.is_stalemate(), "| engine offers an alternative promotion:", False)

print("--- 2. insufficient material / 50-move: does the engine know? ---")
for fen in ["8/8/8/4k3/8/8/3K4/6B1 w - - 0 1", "8/8/8/4k3/8/8/3K4/6N1 w - - 0 1", "8/8/8/4k3/8/8/3KB3/5b2 w - - 0 1"]:
    b, cb = board_from_fen(fen)
    print(fen, "| python-chess insufficient:", cb.is_insufficient_material(), "| engine isKingVsKing:", b.isKingVsKing())
print("engine has halfmove clock:", hasattr(Board(), "halfmove_clock"))

print("--- 3. custom boards: castling with an ENEMY rook / misplaced pieces ---")
b = Board()
b.game_board = [Square(None) for _ in range(64)]
wk = King(Team.WHITE, 60); br = Rook(Team.BLACK, 63)          # random boards give every rook first_move=True
bk = King(Team.BLACK, 4)
b.game_board[60], b.game_board[63], b.game_board[4] = Square(wk), Square(br), Square(bk)
b.white_king, b.black_king, b.turn, b.move_history, b.hash_code = wk, bk, Team.WHITE, [], None
types = sorted(set(m.getType() for m in b.getAllLegalMove(Team.WHITE)))
print("white move types:", types, "<- SHORT_CASTLE with a BLACK rook" if "SHORT_CASTLE" in types else "")

print("--- 4. random custom board: first_move flags vs. real castling rights ---")
random.seed(1)
bad = 0; N = 300
for _ in range(N):
    b = Board()
    b.setUpRandomBoard({"queen":1,"rook":2,"bishop":2,"knight":2,"pawn":8,"king":1}, {"queen":1,"rook":2,"bishop":2,"knight":2,"pawn":8,"king":1})
    b.turn = Team.WHITE; b.move_history = []; b.hash_code = None
    if any(m.getType() in ("SHORT_CASTLE","LONG_CASTLE") for m in b.getAllLegalMove(Team.WHITE)): bad = bad + 1
print(f"{bad}/{N} random boards offer a castling move on move 1 (never legal in an arbitrary position)")
