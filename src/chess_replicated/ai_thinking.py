import threading
from .alphabeta import NegaMaxAlphaBetaTransposition


class AIThinkTank:
    def __init__(self, board):
        self.board = board
        self.transposition_table = {}
        self._last_task = None
        self._last_score = None             # ← lưu điểm cuối cùng

    def think(self, depth):
        """
        Chạy AI đồng bộ (không thread).
        Trả về (best_move, best_score).
        """
        task = NegaMaxAlphaBetaTransposition(
            board=self.board,
            max_depth=depth,
            transposition_table=self.transposition_table
        )

        best_move, best_score = task.negamaxRoot(-(10**9), 10**9)   # ← unpack tuple
        self._last_task  = task
        self._last_score = best_score
        return best_move, best_score        # ← trả về cả hai

    def get_node_count(self):
        if self._last_task is not None:
            return self._last_task.node_count
        return 0

    def get_last_score(self):
        return self._last_score if self._last_score is not None else 0