import sys, os, json, subprocess, statistics, chess, chess.engine
root, ms, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
fens = json.load(open("positions.json"))[:n]
env = dict(os.environ, ENGINE_ROOT=root)
eng = subprocess.Popen([sys.executable, "engine_cli.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
sf = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish"); sf.configure({"Threads": 1, "Hash": 64})
LIM = chess.engine.Limit(depth=11)
def ev(cb, color): return max(-1000, min(1000, sf.analyse(cb, LIM)["score"].pov(color).score(mate_score=1000)))
losses, depths, illegal = [], [], 0
for fen in fens:
    cb = chess.Board(fen)
    best = ev(cb, cb.turn)
    eng.stdin.write(json.dumps({"fen": fen, "moves": [], "ms": ms}) + "\n"); eng.stdin.flush()
    r = json.loads(eng.stdout.readline())
    mv = chess.Move.from_uci(r["move"])
    if mv not in cb.legal_moves:
        illegal = illegal + 1; losses.append(1000); continue
    cb.push(mv)
    after = -sf.analyse(cb, LIM)["score"].pov(cb.turn).score(mate_score=1000)
    after = max(-1000, min(1000, after))
    losses.append(max(0, best - after)); depths.append(r["depth"])
eng.stdin.close(); sf.quit()
print(f"{root.split('/')[-1]:8s} ms={ms} n={len(losses)} ACPL={statistics.mean(losses):6.1f} median={statistics.median(losses):5.1f} "
      f"blunders(>=200)={sum(1 for l in losses if l >= 200)} best-ish(<=10)={sum(1 for l in losses if l <= 10)} "
      f"avg_depth={statistics.mean(depths):.1f} illegal={illegal}")
json.dump(losses, open(f"losses_{os.path.basename(root)}_{ms}.json", "w"))
