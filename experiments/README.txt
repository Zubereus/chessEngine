Setup: pip install python-chess ; install stockfish (apt install stockfish -> /usr/games/stockfish; edit the path in the scripts if yours differs)
Run from inside this folder. Set ENGINE_ROOT=<path to project root> to pick which source tree to test (default: parent folder).

e1_perft.py       perft vs python-chess (8 positions)
e1c_lockstep.py   walks the tree in the engine's own order; catches make/undo state corruption
e2_fuzz.py N P    N random games of P plies: legal moves, hash, undo, halfmove clock vs python-chess
e3_rules.py       underpromotion / insufficient material / custom-board castling checks
e4_profile.py     nodes/sec, profile, root-ordering check
e5_material.py    insufficient-material rule vs python-chess
e6_symmetry.py    evaluator colour symmetry
e7_conversion.py OLD_ROOT [NEW_ROOT]  KQ-vs-K / KR-vs-K conversion
bench_acpl.py ROOT MS N   Stockfish-judged centipawn loss (needs positions.json)
match.py MS PAIRS OLD_ROOT [NEW_ROOT]  old vs new engine match (NEW_ROOT defaults to the parent folder)
sf_anchor.py ROOT MS GAMES   games vs Stockfish UCI_Elo 1320
