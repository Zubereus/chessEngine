"""Sample varied middlegame positions (side to move = anyone) from noisy Stockfish self-play."""
import chess, chess.engine, random, json
rng = random.Random(2026)
sf = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")
sf.configure({"Threads": 1, "Hash": 64})
out = []
while len(out) < 140:
    cb = chess.Board()
    for _ in range(rng.randint(4, 8)):                       # random opening
        cb.push(rng.choice(list(cb.legal_moves)))
    for ply in range(70):
        if cb.is_game_over(): break
        info = sf.analyse(cb, chess.engine.Limit(nodes=3000), multipv=3)
        if ply >= 6 and ply % 5 == 0 and cb.legal_moves.count() > 1:
            sc = info[0]["score"].pov(cb.turn).score(mate_score=2000)
            if abs(sc) < 900:
                out.append(cb.fen())
        pick = info[0]["pv"][0] if rng.random() < 0.7 or len(info) < 2 else rng.choice(info)["pv"][0]
        cb.push(pick)
rng.shuffle(out)
json.dump(out[:140], open("positions.json", "w"))
print(len(out[:140]), "positions saved")
sf.quit()
