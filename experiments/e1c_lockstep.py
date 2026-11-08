from bridge import *

def walk(b, cb, path, d, snap0=None):
    mine = b.getAllLegalMove(b.turn)
    mk = sorted(map(engine_move_key, mine)); rk = sorted(chess_move_keys(cb))
    if mk != rk:
        names = lambda ks: [chess.square_name(a) + chess.square_name(c) for a, c in ks]
        return path, cb.fen(), "missing", names(set(rk) - set(mk)), "extra", names(set(mk) - set(rk)), "dups", len(mk) - len(set(mk))
    if d == 0: return None
    for m in mine:
        before = snapshot(b)
        b.makeMove(m); cb.push(chess.Move(*engine_move_key(m)))
        r = walk(b, cb, path + [chess.Move(*engine_move_key(m)).uci()], d - 1)
        b.undoMove(); cb.pop()
        if snapshot(b) != before:
            return path + [chess.Move(*engine_move_key(m)).uci()], "STATE NOT RESTORED after undo", \
                   sorted(set(snapshot(b)) ^ set(before), key=str)
        if r: return r
    return None

b, cb = board_from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
print(walk(b, cb, [], 3))
