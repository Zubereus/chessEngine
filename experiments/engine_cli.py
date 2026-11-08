"""Line-protocol wrapper so any source tree (selected by ENGINE_ROOT) can be driven as a subprocess."""
import sys, json, time, os
from bridge import *
from src.chess_replicated.ai_thinking import AIThinkTank
from copy import deepcopy

def apply_moves(b, cb, ucis):
    hashes = [b.getHash()]
    for u in ucis:
        mv = chess.Move.from_uci(u)
        def matches(m):
            f, t, p = engine_move_key(m)
            promo_ok = (p == mv.promotion) if hasattr(m, "promotion") else (mv.promotion in (None, chess.QUEEN))
            return (f, t) == (mv.from_square, mv.to_square) and promo_ok
        em = next(filter(matches, b.getAllLegalMove(b.turn)))
        b.makeMove(em); cb.push(mv); hashes.append(b.getHash())
    return hashes

tank_cache = {}
for line in sys.stdin:
    req = json.loads(line)
    b, cb = board_from_fen(req["fen"])
    hist = apply_moves(b, cb, req.get("moves", []))
    t = time.time()
    tank = AIThinkTank(b)
    counts = {}
    for h in hist: counts[h] = counts.get(h, 0) + 1
    kwargs = {}
    if "history" in AIThinkTank.think_on.__code__.co_varnames:
        kwargs["history"] = counts
        off = set(filter(None, os.environ.get("CHESS_AB_OFF", "").split(",")))
        from src.chess_replicated.alphabeta_fast import ALL_FEATURES
        kwargs["features"] = ALL_FEATURES - off - ({"lmr"} if False else set())
    mid, score, done, nodes, secs = tank.think_on(deepcopy(b), req.get("depth", 64), req["ms"] / 1000, **kwargs)
    s, e, mtype = mid[:3]
    uci = chess.square_name(to_chess_sq(s)) + chess.square_name(to_chess_sq(e))
    if len(mid) > 3 and mid[3]: uci = uci + mid[3].lower()
    print(json.dumps({"move": uci, "score": score, "depth": done, "nodes": nodes, "secs": time.time() - t}), flush=True)
