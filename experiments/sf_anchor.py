import sys, os, json, random, subprocess, math, chess, chess.engine
root, ms, games = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
eng = subprocess.Popen([sys.executable, "engine_cli.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=dict(os.environ, ENGINE_ROOT=root))
sf = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")
sf.configure({"Threads": 1, "UCI_LimitStrength": True, "UCI_Elo": 1320})
rng = random.Random(21); pts = 0.0
def material(cb):
    v = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}
    return sum(v[p.piece_type] * (1 if p.color else -1) for p in cb.piece_map().values())
for g in range(games):
    cb = chess.Board(); moves = []
    for _ in range(4):
        m = rng.choice(list(cb.legal_moves)); cb.push(m); moves.append(m.uci())
    mine_white = g % 2 == 0
    if g % 2 == 1: pass
    else: pass
    if g % 2 == 0 and g > 0: pass
    while not (cb.is_game_over(claim_draw=True) or len(moves) >= 200):
        if cb.turn == mine_white:
            eng.stdin.write(json.dumps({"fen": chess.STARTING_FEN, "moves": moves, "ms": ms}) + "\n"); eng.stdin.flush()
            mv = chess.Move.from_uci(json.loads(eng.stdout.readline())["move"])
            if mv not in cb.legal_moves:
                mv = chess.Move(mv.from_square, mv.to_square, chess.QUEEN)   # old engine ids carry no promotion piece
        else:
            mv = sf.play(cb, chess.engine.Limit(time=0.1)).move
        cb.push(mv); moves.append(mv.uci())
    if cb.is_game_over(claim_draw=True):
        r = cb.result(claim_draw=True); w_white = {"1-0": 1, "0-1": 0, "1/2-1/2": .5}[r]
    else:
        d = material(cb); w_white = 1 if d >= 3 else 0 if d <= -3 else .5
    pts = pts + (w_white if mine_white else 1 - w_white)
    print(f"{os.path.basename(root)} game {g+1}: mine={'W' if mine_white else 'B'} white_score={w_white} plies={len(moves)} total={pts}/{g+1}", flush=True)
s = min(max(pts / games, 0.5 / games), 1 - 0.5 / games)
print(f"RESULT {os.path.basename(root)}: {pts}/{games}  implied rating vs SF1320 = {1320 + 400 * math.log10(s / (1 - s)):.0f}")
eng.stdin.close(); sf.quit()
