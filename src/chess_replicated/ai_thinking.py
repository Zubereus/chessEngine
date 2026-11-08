import time
from .alphabeta_fast import FastNegaMax, _move_id


class AIThinkTank:
    """
    Alpha-beta "think tank" used by the UI.

    - It always searches a COPY of the board, so the board on screen is never
      touched while the AI is thinking.
    - Iterative deepening + an optional time limit: the AI returns the best
      move of the deepest depth it finished, so it can never freeze the game.
    """

    MAX_TABLE_SIZE = 400000          # keep memory bounded over a long game

    def __init__(self, board):
        self.board = board
        self.transposition_table = {}
        self.best_moves = {}
        self._last_score = None
        self._nodes = 0
        self._depth_done = 0

    def think_on(self, work_board, depth, time_limit=None):
        """
        Search `work_board` (a private copy; safe to call from a worker thread).
        Returns (move_id, score, depth_completed, nodes, seconds), where
        move_id = (start_pos, end_pos, move_type) or None.
        """
        if len(self.transposition_table) > self.MAX_TABLE_SIZE:
            self.transposition_table.clear()
            self.best_moves.clear()
        started = time.time()
        engine = FastNegaMax(work_board, self.transposition_table, self.best_moves)
        move, score, done = engine.search(depth, time_limit)
        self._nodes, self._last_score, self._depth_done = engine.node_count, score, done
        move_id = None if move is None else _move_id(move)
        return move_id, score, done, engine.node_count, time.time() - started

    def find_real_move(self, move_id):
        """Turn a move_id into the matching legal Move object of the real board."""
        if move_id is None:
            return None
        return next(
            (m for m in self.board.getAllLegalMove(self.board.turn) if _move_id(m) == move_id),
            None,
        )

    def think(self, depth, time_limit=None):
        """Synchronous version. Returns (best_move, best_score) like before."""
        from copy import deepcopy
        move_id, score, _, _, _ = self.think_on(deepcopy(self.board), depth, time_limit)
        return self.find_real_move(move_id), score

    def get_node_count(self):
        return self._nodes

    def get_last_score(self):
        return self._last_score if self._last_score is not None else 0

    def get_depth_completed(self):
        return self._depth_done