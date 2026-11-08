import sys, os, json, random, subprocess, chess
from pathlib import Path

if len(sys.argv) not in (4, 5):
    raise SystemExit("usage: match.py MS PAIRS OLD_ENGINE_ROOT [NEW_ENGINE_ROOT]")

ms, pairs = int(sys.argv[1]), int(sys.argv[2])
old_root = os.path.abspath(sys.argv[3])
new_root = os.path.abspath(sys.argv[4] if len(sys.argv) == 5 else Path(__file__).resolve().parent.parent)
def spawn(root): return subprocess.Popen([sys.executable, "engine_cli.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=dict(os.environ, ENGINE_ROOT=root))
E = {"old": spawn(old_root), "new": spawn(new_root)}
def ask(name, moves):
    p = E[name]; p.stdin.write(json.dumps({"fen": chess.STARTING_FEN, "moves": moves, "ms": ms}) + "\n"); p.stdin.flush()
    return json.loads(p.stdout.readline())["move"]
def material(cb):
    v = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}
    return sum(v[p.piece_type] * (1 if p.color else -1) for p in cb.piece_map().values())
rng = random.Random(11); score = {"old": 0.0, "new": 0.0}; log = []
for k in range(pairs):
    cb0 = chess.Board(); opening = []
    for _ in range(6):
        m = rng.choice(list(cb0.legal_moves)); opening.append(m.uci()); cb0.push(m)
    for white in ("new", "old"):
        cb = chess.Board(); moves = []
        for u in opening: cb.push_uci(u); moves.append(u)
        while not (cb.is_game_over(claim_draw=True) or len(moves) >= 160):
            who = white if cb.turn else ("old" if white == "new" else "new")
            u = ask(who, moves)
            mv = chess.Move.from_uci(u)
            if mv not in cb.legal_moves: print("ILLEGAL from", who, u); break
            cb.push(mv); moves.append(u)
        if cb.is_game_over(claim_draw=True):
            r = cb.result(claim_draw=True); w = {"1-0": 1, "0-1": 0, "1/2-1/2": .5}[r]
        else:
            d = material(cb); w = 1 if d >= 3 else 0 if d <= -3 else .5
        other = "old" if white == "new" else "new"
        score[white] = score[white] + w; score[other] = score[other] + 1 - w
        log.append((white, w, len(moves)))
        print(f"game {len(log):2d}: white={white} result={w} plies={len(moves)}  running new={score['new']} old={score['old']}", flush=True)
print("FINAL", score)
