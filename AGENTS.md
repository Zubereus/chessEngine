# Project rules

- Work only on the current feature branch. Never switch to or make changes on `main`. Never commit or push unless the user asks.
- Do not edit the root `requirements.txt`; it must keep `pygame-ce` for the desktop version.
- Do not move or rename files that `main.py`, `src/`, or `tests/` import from.
- Do not change chess rules, evaluation, or search algorithms. Only wrap them.
- Write beginner-readable code with small pure functions, no global mutable state, and short comments.
- For small changes, show only the changed sections, not whole files.
- After each phase, run `python -m unittest discover tests` and `python main.py`. If either cannot be run, say so.
