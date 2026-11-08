import time
from .alphabeta import SortingHat
from .enum_chess import MoveType, PieceType
from .evaluator import Evaluator
from .hashentry import EntryType, HashEntry


class SearchTimeout(Exception):
    """Raised inside the search when the time budget is used up."""


_VALUE = {
    PieceType.PAWN: 100, PieceType.KNIGHT: 320, PieceType.BISHOP: 330,
    PieceType.ROOK: 500, PieceType.QUEEN: 900, PieceType.KING: 20000,
}
_INF = 10 ** 9


def _order_key(move):
    """MVV-LVA: take the most valuable victim with the cheapest attacker first."""
    attacker = _VALUE[move.getPiece().getPieceType()]
    captured = move.getAttackedPiece()
    if captured is not None:
        score = 10 * _VALUE[captured.getPieceType()] - attacker
    elif move.getType() == MoveType.ENPASSENT:
        score = 10 * _VALUE[PieceType.PAWN] - attacker
    else:
        score = 0
    if move.getType() in (MoveType.PAWN, MoveType.PAWN_ATTACK) and move.getEndPos() // 8 in (0, 7):
        score += 8000                                # promotion
    return score


def _move_id(move):
    return (move.getStartPos(), move.getEndPos(), move.getType())


class FastNegaMax:
    """Negamax + alpha-beta + transposition table, with move ordering and a time limit."""

    def __init__(self, board, transposition_table=None, best_moves=None):
        self.board = board
        self.tt = transposition_table if transposition_table is not None else {}
        self.best_moves = best_moves if best_moves is not None else {}
        self.node_count = 0
        self.deadline = None

    # ---------- public API ----------
    def search(self, max_depth, time_limit=None):
        """Iterative deepening. Returns (best_move, score, depth_completed)."""
        self.deadline = None if time_limit is None else time.time() + time_limit
        root_moves = SortingHat.sortMove(
            self.board.getAllLegalMove(self.board.turn), self.board
        )
        best_move, best_score, done = None, 0, 0
        if len(root_moves) == 1:                      # forced move: no need to think
            return root_moves[0], 0, 0

        for depth in range(1, max_depth + 1):
            try:
                move, score = self._search_root(root_moves, depth)
            except SearchTimeout:
                break
            best_move, best_score, done = move, score, depth
            # best move first in the next, deeper iteration
            root_moves.sort(key=lambda m: m is not move)
        if best_move is None and root_moves:          # time ran out before depth 1 finished
            best_move = root_moves[0]
        return best_move, best_score, done

    # ---------- internals ----------
    def _search_root(self, root_moves, depth):
        alpha, best_move = -_INF, None
        for move in root_moves:
            self.board.makeMove(move)
            score = -self._negamax(depth - 1, -_INF, -alpha)
            self.board.undoMove()
            if score > alpha:
                alpha, best_move = score, move
        return best_move, alpha

    def _check_time(self):
        if self.deadline is not None and (self.node_count & 255) == 0:
            if time.time() > self.deadline:
                raise SearchTimeout

    def _negamax(self, depth, alpha, beta):
        self.node_count += 1
        self._check_time()
        board = self.board
        alpha_orig = alpha
        key = board.getHash()

        entry = self.tt.get(key)
        if entry is not None and entry.getDepth() >= depth:
            if entry.getType() == EntryType.EXACT:
                return entry.getScore()
            if entry.getType() == EntryType.LOWER_BOUND:
                alpha = max(alpha, entry.getScore())
            else:
                beta = min(beta, entry.getScore())
            if alpha >= beta:
                return entry.getScore()

        if depth == 0:
            return Evaluator.evaluate(board)

        moves = board.getAllLegalMove(board.turn)
        if not moves:
            return Evaluator.evaluateEndGame(board)

        moves.sort(key=_order_key, reverse=True)
        remembered = self.best_moves.get(key)
        if remembered is not None:                    # TT move goes first
            for i, m in enumerate(moves):
                if _move_id(m) == remembered:
                    moves.insert(0, moves.pop(i))
                    break

        best_score, best_move = -_INF, None
        for move in moves:
            board.makeMove(move)
            score = -self._negamax(depth - 1, -beta, -alpha)
            board.undoMove()
            if score > best_score:
                best_score, best_move = score, move
            alpha = max(alpha, score)
            if alpha >= beta:
                break

        if best_score <= alpha_orig:
            entry_type = EntryType.UPPER_BOUND
        elif best_score >= beta:
            entry_type = EntryType.LOWER_BOUND
        else:
            entry_type = EntryType.EXACT
        self.tt[key] = HashEntry(best_score, depth, entry_type)
        if best_move is not None:
            self.best_moves[key] = _move_id(best_move)
        return best_score
