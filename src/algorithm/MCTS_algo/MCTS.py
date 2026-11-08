import math
import random
from copy import deepcopy
from src.chess_replicated.chess_board import King
from src.chess_replicated.enum_chess import MoveType, Team
from .mcts_evalutor import simple_evaluate

_root_cache = {}

def clear_mcts_cache():
    _root_cache.clear()

def _opponent(color):
	return Team.BLACK if color == Team.WHITE else Team.WHITE

class MCTSNode:
    def __init__(self, player_to_move, root_color, move=None, parent=None):
        # Nodes no longer store a board — the single working_board is shared
        self.player_to_move = player_to_move
        self.root_color = root_color
        self.move = move          # the move that led TO this node
        self.parent = parent
        self.untried_moves = None # populated lazily when first visited
        self.children = []
        self.visits = 0
        self.value_sum = 0.0

    def is_fully_expanded(self):
        return self.untried_moves is not None and len(self.untried_moves) == 0

    def ucb_score(self, exploration, maximize=True):
        if self.visits == 0:
            return float("inf")
        exploitation = self.value_sum / self.visits
        if not maximize:
            exploitation = -exploitation
        exploration_term = exploration * math.sqrt(
            math.log(self.parent.visits + 1) / self.visits
        )
        return exploitation + exploration_term


def _simulate_random_playout(
    board,
    player_to_move,
    root_color,
    rollout_depth=2,
    legal_moves_tt=None,
    eval_tt=None,
):
    """Run a low-cost, capture-aware rollout and restore the board."""
    legal_moves_tt = legal_moves_tt if legal_moves_tt is not None else {}
    eval_tt = eval_tt if eval_tt is not None else {}
    moves_made = 0
    turn = player_to_move
    terminal = False

    for _ in range(rollout_depth):
        legal_moves = _get_legal_moves_tt(board, turn, legal_moves_tt)
        if not legal_moves:
            terminal = True
            break
        priorities = [_move_priority(move) for move in legal_moves]
        best_priority = max(priorities)
        if best_priority > 0 and random.random() < 0.75:
            candidates = [
                move for move, priority in zip(legal_moves, priorities)
                if priority >= best_priority - 150
            ]
            move = random.choice(candidates)
        else:
            move = random.choice(legal_moves)
        board.makeMove(move)
        moves_made += 1
        turn = _opponent(turn)

    if not terminal and moves_made == rollout_depth:
        terminal = not _get_legal_moves_tt(board, turn, legal_moves_tt)

    if terminal:
        if board.kingIsSafe():
            reward = 0.0
        else:
            winner = _opponent(turn)
            reward = 1.0 if winner == root_color else -1.0
    else:
        reward = _evaluate_leaf_tt(board, root_color, eval_tt)

    for _ in range(moves_made):
        board.undoMove()
    return reward


def _quiescence(board, root_color, depth):
    stand_pat = simple_evaluate(board, root_color)
    if depth == 0:
        return stand_pat
    side = board.turn
    captures = [m for m in board.getAllPossibleMove(side)
                if m.getAttackedPiece() is not None]
    # A capture of the king means the previous move left its own king in
    # check (illegal). Never play it on the board: undoMove would put back a
    # COPY of the king and board.white_king / black_king would go stale.
    if any(isinstance(m.getAttackedPiece(), King) for m in captures):
        return _KING_CAPTURE_SCORE if side == root_color else -_KING_CAPTURE_SCORE
    captures.sort(key=_move_priority, reverse=True)
    best = stand_pat
    for move in captures[:6]:
        board.makeMove(move)
        score = _quiescence(board, root_color, depth - 1)
        board.undoMove()
        best = max(best, score) if side == root_color else min(best, score)
    return best


def _terminal_reward(board, node, root_color, legal_moves_tt):
    if _get_legal_moves_tt(board, node.player_to_move, legal_moves_tt):
        return None
    if board.kingIsSafe():
        return 0.0
    return -1.0 if node.player_to_move == root_color else 1.0


def _best_ucb_child(node, exploration):
    return max(
        node.children,
        key=lambda child: child.ucb_score(
            exploration,
            maximize=node.player_to_move == node.root_color,
        ),
    )


def _best_visit_child(node):
    return max(node.children, key=lambda c: c.visits)


def _get_legal_moves_tt(board, player_to_move, legal_moves_tt):
    key = (board.getHash(), player_to_move)
    cached = legal_moves_tt.get(key)
    if cached is not None:
        # Return a shallow copy because callers may mutate (pop) node.untried_moves.
        return list(cached)
    moves = board.getAllLegalMove(player_to_move)
    legal_moves_tt[key] = tuple(moves)
    return list(moves)


def _evaluate_leaf_tt(board, root_color, eval_tt):
    key = (board.getHash(), root_color)
    cached = eval_tt.get(key)
    if cached is not None:
        return cached
    score = _quiescence(board, root_color, 2)
    reward = math.tanh(score / 300.0)
    eval_tt[key] = reward
    return reward


_PIECE_VALUES = {
    "P": 100,
    "N": 320,
    "B": 330,
    "R": 500,
    "Q": 900,
    "K": 20000,
}


def _move_priority(move):
    attacker = _PIECE_VALUES.get(move.getPiece().getPieceType(), 100)
    captured = move.getAttackedPiece()
    victim_value = (
        _PIECE_VALUES.get(captured.getPieceType(), 0)
        if captured is not None
        else 100 if move.getType() == MoveType.ENPASSENT else 0
    )
    promotion_bonus = (
        800
        if move.getType() in (MoveType.PAWN, MoveType.PAWN_ATTACK)
        and move.getEndPos() // 8 in (0, 7)
        else 0
    )
    return victim_value * 10 - attacker + promotion_bonus


def _expand(node, board, color):
    move = node.untried_moves.pop(0)
    board.makeMove(move)
    child = MCTSNode(
        player_to_move=_opponent(node.player_to_move),
        root_color=color,
        move=move,
        parent=node,
    )
    node.children.append(child)
    return child


def _backpropagate(node, reward):
    current = node
    while current is not None:
        current.visits += 1
        current.value_sum += reward
        current = current.parent


_MATE = 100000
_KING_CAPTURE_SCORE = 20000
_fallback_count = 0


def _worst_case_value(board, move, root_color):
    """
    3-ply check from the root position: our move, every opponent reply,
    then one capture round for us. Returns the opponent's best outcome
    (root_color's view). +_MATE if the move mates, -_MATE if it allows mate.
    """
    board.makeMove(move)
    replies = board.getAllLegalMove(board.turn)
    if not replies:
        value = _MATE if not board.kingIsSafe() else 0
        board.undoMove()
        return value

    worst = _MATE
    for reply in replies:
        board.makeMove(reply)
        gives_mate = (not board.kingIsSafe()) and not board.getAllLegalMove(board.turn)
        value = -_MATE if gives_mate else _quiescence(board, root_color, 1)
        board.undoMove()
        worst = min(worst, value)
        if worst == -_MATE:
            break
    board.undoMove()
    return worst


def _choose_safe_move(board, root, root_color, num_candidates=4, margin=50):
    """Pick among the most-visited moves, vetoing ones that lose material or get mated."""
    ranked = sorted(root.children, key=lambda c: c.visits, reverse=True)

    # 1) play a mate in one if any root move delivers it
    for child in root.children:
        board.makeMove(child.move)
        mates = (not board.kingIsSafe()) and not board.getAllLegalMove(board.turn)
        board.undoMove()
        if mates:
            return child.move

    # 2) otherwise check the top candidates and drop the unsafe ones
    scored = [
        (child, _worst_case_value(board, child.move, root_color))
        for child in ranked[:num_candidates]
    ]
    best_value = max(value for _, value in scored)
    safe = [child for child, value in scored if value >= best_value - margin]
    return max(safe, key=lambda c: c.visits).move


def mcts_search(board, color, iterations=300, exploration=0.3, rollout_depth=2,
                num_candidates=4, margin=50):
	"""
	Returns the best move for `color` using MCTS with make/undo.
	Only ONE deepcopy is made — at search startup — to avoid mutating
	the caller's board.
	"""
	# Single copy for the entire search — all tree ops mutate this one board
	working_board = deepcopy(board)

	root = MCTSNode(player_to_move=color, root_color=color)
	legal_moves_tt = {}
	eval_tt = {}
	root.untried_moves = sorted(
		_get_legal_moves_tt(working_board, color, legal_moves_tt),
		key=_move_priority,
		reverse=True,
	)

	if not root.untried_moves:
		return None

	for _ in range(iterations):
		node = root
		depth = 0  # how many moves we applied going down the tree

		# ── 1) SELECTION ──────────────────────────────────────────────────
		# Walk down fully-expanded nodes, applying each move on working_board
		while node.is_fully_expanded() and node.children:
			node = _best_ucb_child(node, exploration)
			working_board.makeMove(node.move)
			depth += 1

		# ── 2) EXPANSION ──────────────────────────────────────────────────
		# Populate untried_moves lazily (board is now at this node's state)
		if node.untried_moves is None:
			node.untried_moves = sorted(
				_get_legal_moves_tt(
					working_board, node.player_to_move, legal_moves_tt
				),
				key=_move_priority,
				reverse=True,
			)

		if node.untried_moves:
			node = _expand(node, working_board, color)
			depth += 1
			# Populate the new child's untried moves while we're already here
			if node.untried_moves is None:
				node.untried_moves = sorted(
					_get_legal_moves_tt(
						working_board, node.player_to_move, legal_moves_tt
					),
					key=_move_priority,
					reverse=True,
				)

		# ── 3) SIMULATION ─────────────────────────────────────────────────
		# Rollout from the current leaf; board is restored inside the function
		reward = _terminal_reward(working_board, node, color, legal_moves_tt)
		if reward is None:
			reward = _evaluate_leaf_tt(working_board, color, eval_tt)

		# ── 4) BACKPROPAGATION ────────────────────────────────────────────
		_backpropagate(node, reward)

		# ── 5) RESTORE ───────────────────────────────────────────────────
		# Undo the selection + expansion moves so the next iteration
		# starts from the root state again
		for _ in range(depth):
			working_board.undoMove()

	try:
		return _choose_safe_move(working_board, root, color, num_candidates, margin)
	except IndexError:
		# Rare board-state glitch while probing replies; the working board is
		# a throwaway copy, so just fall back to the most-visited move.
		global _fallback_count
		_fallback_count += 1
		return _best_visit_child(root).move