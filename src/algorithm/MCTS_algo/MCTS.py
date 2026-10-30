import math
import random
from copy import deepcopy
from src.chess_replicated.enum_chess import Team
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

    def ucb_score(self, exploration):
        if self.visits == 0:
            return float("inf")
        exploitation = self.value_sum / self.visits
        exploration_term = exploration * math.sqrt(
            math.log(self.parent.visits + 1) / self.visits
        )
        return exploitation + exploration_term


def _simulate_random_playout(board, player_to_move, root_color, rollout_depth=20):
	"""
	Random rollout using make/undo instead of deepcopy.
	After evaluation the board is fully restored to its pre-rollout state.
	"""
	moves_made = 0
	turn = player_to_move

	for _ in range(rollout_depth):
		legal_moves = board.getAllLegalMove(turn)
		if not legal_moves:
			break
		move = random.choice(legal_moves)
		board.makeMove(move)
		moves_made += 1
		turn = _opponent(turn)

	# Evaluate at the leaf
	score = simple_evaluate(board, root_color)
	if score > 0:
		reward = 1.0
	elif score < 0:
		reward = -1.0
	else:
		reward = 0.0

	# Restore board: undo every rollout move in reverse order
	for _ in range(moves_made):
		board.undoMove()

	return reward


def _best_ucb_child(node, exploration):
    return max(node.children, key=lambda c: c.ucb_score(exploration))


def _best_visit_child(node):
    return max(node.children, key=lambda c: c.visits)


def _get_legal_moves_tt(board, player_to_move, legal_moves_tt):
    key = (board.hashCode, player_to_move)
    cached = legal_moves_tt.get(key)
    if cached is not None:
        # Return a shallow copy because callers may mutate (pop) node.untried_moves.
        return list(cached)
    moves = board.getLegalMoves(player_to_move)
    legal_moves_tt[key] = tuple(moves)
    return list(moves)


def _evaluate_leaf_tt(board, root_color, eval_tt):
    key = (board.hashCode, root_color)
    cached = eval_tt.get(key)
    if cached is not None:
        return cached
    score = simple_evaluate(board, root_color)
    if score > 0:
        reward = 1.0
    elif score < 0:
        reward = -1.0
    else:
        reward = 0.0
    eval_tt[key] = reward
    return reward


def _expand(node, board, color):
    move = node.untried_moves.pop(random.randrange(len(node.untried_moves)))
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
        if current.player_to_move == current.root_color:
            current.value_sum += reward
        else:
            current.value_sum -= reward
        current = current.parent


def mcts_search(board, color, iterations=300, exploration=1.41, rollout_depth=20):
	"""
	Returns the best move for `color` using MCTS with make/undo.
	Only ONE deepcopy is made — at search startup — to avoid mutating
	the caller's board.
	"""
	# Single copy for the entire search — all tree ops mutate this one board
	working_board = deepcopy(board)

	root = MCTSNode(player_to_move=color, root_color=color)
	root.untried_moves = working_board.getAllLegalMove(color)

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
			node.untried_moves = working_board.getAllLegalMove(node.player_to_move)

		if node.untried_moves:
			node = _expand(node, working_board, color)
			depth += 1
			# Populate the new child's untried moves while we're already here
			if node.untried_moves is None:
				node.untried_moves = working_board.getAllLegalMove(node.player_to_move)

		# ── 3) SIMULATION ─────────────────────────────────────────────────
		# Rollout from the current leaf; board is restored inside the function
		reward = _simulate_random_playout(
			working_board, node.player_to_move, color, rollout_depth
		)

		# ── 4) BACKPROPAGATION ────────────────────────────────────────────
		_backpropagate(node, reward)

		# ── 5) RESTORE ───────────────────────────────────────────────────
		# Undo the selection + expansion moves so the next iteration
		# starts from the root state again
		for _ in range(depth):
			working_board.undoMove()

	best_child = _best_visit_child(root)
	return best_child.move