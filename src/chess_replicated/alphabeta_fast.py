import time
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
MATE = 100000
MATE_BOUND = MATE - 1000          # any |score| above this is "mate in N plies"
MAX_PLY = 64
QSEARCH_LIMIT = 6                 # extra capture-only plies after the nominal depth
ALL_FEATURES = frozenset({"qsearch", "mateply", "draws", "killers", "pvs", "checkext"})


def _is_promotion(move):
    return move.getPromotion() is not None


def _tactical_key(move):
    """MVV-LVA: most valuable victim first, cheapest attacker first; promotions on top."""
    attacker = _VALUE[move.getPiece().getPieceType()]
    captured = move.getAttackedPiece()
    victim = (
        _VALUE[captured.getPieceType()] if captured is not None
        else _VALUE[PieceType.PAWN] if move.getType() == MoveType.ENPASSENT
        else 0
    )
    promotion = _VALUE.get(move.getPromotion(), 0)
    return 10 * victim - attacker + 10 * promotion


def _order_key(move):
    return _tactical_key(move)


def _move_id(move):
    return move.getId()


def _mate_to_tt(score, ply):
    """Mate scores are relative to the root; in the table they must be relative to the node."""
    if score > MATE_BOUND:
        return score + ply
    if score < -MATE_BOUND:
        return score - ply
    return score


def _mate_from_tt(score, ply):
    if score > MATE_BOUND:
        return score - ply
    if score < -MATE_BOUND:
        return score + ply
    return score


class FastNegaMax:
    """
    Negamax + alpha-beta + transposition table, iterative deepening and a time limit.

    Features (each can be switched off through `features` for ablation experiments):
      qsearch   capture/promotion/check-evasion search at the horizon instead of a static eval
      mateply   mate scores carry the distance to mate, so the shortest mate is preferred
      draws     repetition, fifty-move rule and dead-position draws are scored 0 inside the search
      killers   killer + history heuristics for quiet-move ordering
      pvs       principal-variation search (null-window re-searches after the first move)
      checkext  search one ply deeper when in check
    """

    def __init__(self, board, transposition_table=None, best_moves=None, history=None, features=ALL_FEATURES):
        self.board = board
        self.tt = transposition_table if transposition_table is not None else {}
        self.best_moves = best_moves if best_moves is not None else {}
        self.features = frozenset(features)
        self.seen = dict(history or {})           # position hash -> times seen in the game / current path
        self.killers = [[None, None] for _ in range(MAX_PLY + 8)]
        self.history_scores = {}
        self.node_count = 0
        self.deadline = None

    # ---------- public API ----------
    def search(self, max_depth, time_limit=None):
        """Iterative deepening. Returns (best_move, score, depth_completed)."""
        self.deadline = None if time_limit is None else time.time() + time_limit
        board = self.board
        root_key = board.getHash()
        self.seen[root_key] = max(self.seen.get(root_key, 0), 1)
        root_moves = board.getAllLegalMove(board.turn)
        if not root_moves:
            return None, 0, 0
        if len(root_moves) == 1:                      # forced move: no need to think
            return root_moves[0], 0, 0
        root_moves.sort(key=self._root_key(root_key), reverse=True)

        best_move, best_score, done = None, 0, 0
        for depth in range(1, max_depth + 1):
            try:
                move, score = self._search_root(root_moves, depth)
            except SearchTimeout:
                break
            best_move, best_score, done = move, score, depth
            root_moves.sort(key=lambda m: m is not move)    # best move first in the next iteration
            if abs(score) > MATE_BOUND:                      # forced mate found: deeper search adds nothing
                break
        if best_move is None:
            best_move = root_moves[0]
        return best_move, best_score, done

    # ---------- internals ----------
    def _root_key(self, key):
        remembered = self.best_moves.get(key)
        return lambda m: (m.getId() == remembered, _tactical_key(m))

    def _search_root(self, root_moves, depth):
        board = self.board
        alpha, best_move = -_INF, None
        for index, move in enumerate(root_moves):
            board.makeMove(move)
            if index == 0 or "pvs" not in self.features:
                score = -self._negamax(depth - 1, 1, -_INF, -alpha)
            else:
                score = -self._negamax(depth - 1, 1, -alpha - 1, -alpha)
                if score > alpha:
                    score = -self._negamax(depth - 1, 1, -_INF, -alpha)
            board.undoMove()
            if score > alpha:
                alpha, best_move = score, move
        self.best_moves[board.getHash()] = best_move.getId()
        return best_move, alpha

    def _check_time(self):
        if self.deadline is not None and (self.node_count & 255) == 0:
            if time.time() > self.deadline:
                raise SearchTimeout

    def _mated_score(self, ply):
        return -(MATE - ply) if "mateply" in self.features else -MATE

    def _is_draw_by_rule(self, key):
        """Repetition, fifty-move rule, dead position. (Checkmate on the 100th ply is handled by the caller.)"""
        board = self.board
        if self.seen.get(key, 0) >= 1:
            return True
        last = board.move_history[-1] if board.move_history else None
        if last is not None and last.isAttackingMove() and board.isInsufficientMaterial():
            return True
        return False

    def _quiet_score(self, move):
        return self.history_scores.get((move.getStartPos(), move.getEndPos()), 0)

    def _ordered(self, moves, ply, tt_id):
        killers = self.killers[ply]

        def key(move):
            move_id = move.getId()
            if move_id == tt_id:
                return 10 ** 7
            tactical = _tactical_key(move)
            if move.isAttackingMove() or _is_promotion(move) or move.getType() == MoveType.ENPASSENT:
                return 10 ** 6 + tactical
            if move_id == killers[0]:
                return 10 ** 5 + 2
            if move_id == killers[1]:
                return 10 ** 5 + 1
            return self._quiet_score(move)

        return sorted(moves, key=key, reverse=True)

    def _store_cutoff(self, move, depth, ply):
        if move.isAttackingMove() or _is_promotion(move):
            return
        move_id = move.getId()
        killers = self.killers[ply]
        if killers[0] != move_id:
            killers[1] = killers[0]
            killers[0] = move_id
        slot = (move.getStartPos(), move.getEndPos())
        self.history_scores[slot] = self.history_scores.get(slot, 0) + depth * depth

    def _negamax(self, depth, ply, alpha, beta):
        self.node_count = self.node_count + 1
        self._check_time()
        board = self.board
        key = board.getHash()
        features = self.features

        if "draws" in features and ply > 0 and self._is_draw_by_rule(key):
            return 0

        alpha_orig = alpha
        entry = self.tt.get(key)
        if entry is not None and entry.getDepth() >= depth:
            score = _mate_from_tt(entry.getScore(), ply)
            if entry.getType() == EntryType.EXACT:
                return score
            if entry.getType() == EntryType.LOWER_BOUND:
                alpha = max(alpha, score)
            else:
                beta = min(beta, score)
            if alpha >= beta:
                return score

        in_check = not board.kingIsSafe()
        if in_check and "checkext" in features and ply < MAX_PLY:
            depth = depth + 1
        if depth <= 0:
            return self._quiesce(ply, alpha, beta, 0) if "qsearch" in features else Evaluator.evaluate(board)

        moves = board.getAllLegalMove(board.turn)
        if not moves:
            return self._mated_score(ply) if in_check else 0
        if "draws" in features and board.halfmove_clock >= 100:
            return 0

        moves = self._ordered(moves, min(ply, MAX_PLY), self.best_moves.get(key))
        self.seen[key] = self.seen.get(key, 0) + 1
        best_score, best_move = -_INF, None
        for index, move in enumerate(moves):
            board.makeMove(move)
            if index == 0 or "pvs" not in features:
                score = -self._negamax(depth - 1, ply + 1, -beta, -alpha)
            else:
                score = -self._negamax(depth - 1, ply + 1, -alpha - 1, -alpha)
                if alpha < score < beta:
                    score = -self._negamax(depth - 1, ply + 1, -beta, -alpha)
            board.undoMove()
            if score > best_score:
                best_score, best_move = score, move
            alpha = max(alpha, score)
            if alpha >= beta:
                if "killers" in features:
                    self._store_cutoff(move, depth, min(ply, MAX_PLY))
                break
        self.seen[key] = self.seen[key] - 1

        if best_score <= alpha_orig:
            entry_type = EntryType.UPPER_BOUND
        elif best_score >= beta:
            entry_type = EntryType.LOWER_BOUND
        else:
            entry_type = EntryType.EXACT
        self.tt[key] = HashEntry(_mate_to_tt(best_score, ply), depth, entry_type)
        if best_move is not None:
            self.best_moves[key] = best_move.getId()
        return best_score

    def _quiesce(self, ply, alpha, beta, qdepth):
        """Resolve captures, promotions and check evasions so the static eval is only used in quiet positions."""
        self.node_count = self.node_count + 1
        self._check_time()
        board = self.board
        if "draws" in self.features and ply > 0 and (
            board.halfmove_clock >= 100 or self._is_draw_by_rule(board.getHash())
        ):
            return 0
        in_check = not board.kingIsSafe()
        if qdepth >= QSEARCH_LIMIT + 2:
            return Evaluator.evaluate(board)

        if in_check:
            moves = board.getAllLegalMove(board.turn)
            if not moves:
                return self._mated_score(ply)
            best = -_INF
            candidates = sorted(moves, key=_tactical_key, reverse=True)
        else:
            stand_pat = Evaluator.evaluate(board)
            if stand_pat >= beta or qdepth >= QSEARCH_LIMIT:
                return stand_pat
            alpha = max(alpha, stand_pat)
            best = stand_pat
            tactical = [
                move for move in board.getAllPossibleMove(board.turn)
                if move.isAttackingMove() or move.getType() == MoveType.ENPASSENT or move.getPromotion() == PieceType.QUEEN
            ]
            candidates = sorted(tactical, key=_tactical_key, reverse=True)

        enemy = board.turn
        for move in candidates:
            if not in_check and not _is_promotion(move):
                gain = _VALUE[move.getAttackedPiece().getPieceType()] if move.getAttackedPiece() is not None else _VALUE[PieceType.PAWN]
                if best + gain + 200 < alpha:                 # delta pruning: cannot raise alpha even with a bonus
                    continue
            board.makeMove(move)
            mover_king = board.white_king if enemy == "WHITE" else board.black_king
            legal = board.isSquareSafe(mover_king.getPosition(), board.turn)
            score = -self._quiesce(ply + 1, -beta, -alpha, qdepth + 1) if legal else None
            board.undoMove()
            if score is None:
                continue
            best = max(best, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best
