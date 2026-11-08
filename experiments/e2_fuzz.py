import random, sys, collections
from bridge import *

FENS = [chess.STARTING_FEN,
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"]
GAMES, PLIES = int(sys.argv[1]), int(sys.argv[2])
rng = random.Random(7)
stats = collections.Counter()
hash_of_key, key_of_hash = {}, {}
first_fail = {}

for g in range(GAMES):
    b, cb = board_from_fen(FENS[g % len(FENS)])
    for ply in range(PLIES):
        mine = b.getAllLegalMove(b.turn)
        mk, rk = set(map(engine_move_key, mine)), chess_move_keys(cb)
        stats["positions"] = stats["positions"] + 1
        if mk != rk:
            stats["move_set_mismatch"] = stats["move_set_mismatch"] + 1
            first_fail.setdefault("moves", (cb.fen(), sorted(rk - mk), sorted(mk - rk)))
        if len(mine) != len(mk):
            stats["duplicate_moves"] = stats["duplicate_moves"] + 1
        if b.halfmove_clock != cb.halfmove_clock:
            stats["halfmove_clock_mismatch"] = stats["halfmove_clock_mismatch"] + 1
            first_fail.setdefault("clock", (cb.fen(), b.halfmove_clock, cb.halfmove_clock))
        # hash canonicity (python-chess key = pieces, turn, castling rights, legal-ep)
        key = cb._transposition_key()
        h = b.getHash()
        if hash_of_key.setdefault(key, h) != h:
            stats["same_position_different_hash"] = stats["same_position_different_hash"] + 1
            first_fail.setdefault("hash_split", cb.fen())
        if key_of_hash.setdefault(h, key) != key:
            stats["different_position_same_hash"] = stats["different_position_same_hash"] + 1
            first_fail.setdefault("hash_collision", (cb.fen(), key_of_hash[h][0]))
        # make/undo round trip on every legal move
        before = snapshot(b)
        for m in mine:
            b.makeMove(m); b.undoMove()
            if snapshot(b) != before:
                stats["undo_not_restoring_state"] = stats["undo_not_restoring_state"] + 1
                first_fail.setdefault("undo", (cb.fen(), engine_move_key(m)))
                break
        if cb.is_game_over() or not rk: break
        choice = rng.choice(sorted(rk, key=str))
        cb.push(chess.Move(*choice))
        b.makeMove(find_engine_move(b, choice))
print(dict(stats)); print(first_fail)
