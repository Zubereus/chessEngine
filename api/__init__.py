"""Stateless JSON API helpers for the chess engine."""

import json
import time
from collections import Counter
from copy import deepcopy
from http.server import BaseHTTPRequestHandler

from src.algorithm.MCTS_algo.MCTS import mcts_search
from src.chess_replicated.ai_thinking import AIThinkTank
from src.chess_replicated.chess_board import (
    Bishop,
    Board,
    King,
    Knight,
    Pawn,
    Queen,
    Rook,
    Square,
)
from src.chess_replicated.enum_chess import MoveType, PieceType, Team
from src.chess_replicated.evaluator import Evaluator


# Keep every request limit together. Four seconds leaves six seconds for request
# parsing, replay, and response writing when Phase 5 sets maxDuration to ten seconds.
MAX_DEPTH = 8  # Reject deeper Alpha-Beta requests; the search also has a time cap.
MAX_MCTS_ITERATIONS = 500  # Bound MCTS work because its interface has no time limit.
AI_TIME_LIMIT_SECONDS = 4.0  # Stop Alpha-Beta before the default function timeout.
MAX_MOVES_IN_REQUEST = 400  # Keep replay work and request payloads bounded.
MAX_REQUEST_BYTES = 65536  # Reject oversized JSON bodies before decoding them.
MAX_CUSTOM_PIECES = 32  # Match the normal maximum number of chess pieces.

_FILES = "abcdefgh"
_RANKS = "12345678"
_PROMOTIONS = {
    "Q": PieceType.QUEEN,
    "R": PieceType.ROOK,
    "B": PieceType.BISHOP,
    "N": PieceType.KNIGHT,
}
_PIECE_CLASSES = {
    "king": King,
    "queen": Queen,
    "rook": Rook,
    "bishop": Bishop,
    "knight": Knight,
    "pawn": Pawn,
}


def parse_request(payload, require_game_state=False):
    """Validate the shared request fields and normalize the starting-position description."""
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    if require_game_state and not {"start_position", "moves"}.issubset(payload):
        raise ValueError("Each game request must include start_position and moves.")
    start_position = payload.get("start_position", {"type": "standard"})
    if not isinstance(start_position, dict):
        raise ValueError("start_position must be an object.")
    start_type = start_position.get("type")
    if not isinstance(start_type, str):
        raise ValueError("start_position.type must be 'standard' or 'custom'.")
    if start_type == "standard":
        if set(start_position) != {"type"}:
            raise ValueError("A standard start_position only accepts type: 'standard'.")
        normalized_start = {"type": "standard"}
    elif start_type == "custom":
        normalized_start = parse_custom_position(start_position)
    else:
        raise ValueError("start_position.type must be 'standard' or 'custom'.")

    moves = payload.get("moves", [])
    if not isinstance(moves, list) or len(moves) > MAX_MOVES_IN_REQUEST:
        raise ValueError(f"moves must be a list of at most {MAX_MOVES_IN_REQUEST} items.")
    return normalized_start, moves


def parse_custom_position(position):
    """Validate an explicit custom placement so every server replay starts identically."""
    if set(position) - {"type", "turn", "pieces"}:
        raise ValueError("Custom start_position accepts only type, turn, and pieces.")
    turn = position.get("turn", "white")
    pieces = position.get("pieces")
    if turn not in ("white", "black"):
        raise ValueError("Custom position turn must be 'white' or 'black'.")
    if not isinstance(pieces, list) or not 2 <= len(pieces) <= MAX_CUSTOM_PIECES:
        raise ValueError(f"Custom pieces must contain 2 to {MAX_CUSTOM_PIECES} pieces.")

    normalized = []
    used_squares = set()
    king_counts = {"white": 0, "black": 0}
    for piece in pieces:
        if not isinstance(piece, dict) or set(piece) != {
            "type", "color", "square", "first_move"
        }:
            raise ValueError("Each custom piece needs type, color, square, and first_move.")
        piece_type = piece["type"]
        color = piece["color"]
        square = piece["square"]
        first_move = piece["first_move"]
        if not isinstance(piece_type, str) or piece_type not in _PIECE_CLASSES:
            raise ValueError("Custom piece type must be king, queen, rook, bishop, knight, or pawn.")
        if not isinstance(color, str) or color not in ("white", "black"):
            raise ValueError("Custom piece color must be 'white' or 'black'.")
        if not isinstance(square, str) or not is_square_name(square):
            raise ValueError("Custom piece square must use algebraic notation, such as e1.")
        if type(first_move) is not bool:
            raise ValueError("Custom piece first_move must be a boolean.")
        index = square_to_index(square)
        if index in used_squares:
            raise ValueError("Custom position cannot place two pieces on one square.")
        used_squares.add(index)
        if piece_type == "king":
            king_counts[color] += 1
        if piece_type == "pawn" and index // 8 in (0, 7):
            raise ValueError("Custom pawns cannot start on the first or eighth rank.")
        normalized.append({
            "type": piece_type,
            "color": color,
            "square": square,
            "first_move": first_move,
        })

    if king_counts != {"white": 1, "black": 1}:
        raise ValueError("Custom position must contain exactly one king of each color.")
    return {"type": "custom", "turn": turn, "pieces": normalized}


def is_square_name(square):
    """Return whether a string names one of the 64 board squares."""
    return len(square) == 2 and square[0] in _FILES and square[1] in _RANKS


def square_to_index(square):
    """Convert algebraic notation to the engine's zero-based board index."""
    return (8 - int(square[1])) * 8 + _FILES.index(square[0])


def index_to_square(index):
    """Convert an engine board index to algebraic notation."""
    row, column = divmod(index, 8)
    return _FILES[column] + str(8 - row)


def build_starting_board(start_position):
    """Build a fresh standard or explicitly described custom Board."""
    board = Board()
    if start_position["type"] == "standard":
        return board

    board.game_board = [Square(None) for _ in range(64)]
    board.move_history = []
    board.halfmove_clock = 0
    for piece_data in start_position["pieces"]:
        color = Team.WHITE if piece_data["color"] == "white" else Team.BLACK
        index = square_to_index(piece_data["square"])
        piece = _PIECE_CLASSES[piece_data["type"]](
            color, index, piece_data["first_move"]
        )
        board.game_board[index] = Square(piece)
        if piece_data["type"] == "king":
            if color == Team.WHITE:
                board.white_king = piece
            else:
                board.black_king = piece
    board.turn = Team.WHITE if start_position["turn"] == "white" else Team.BLACK
    board.hash_code = None
    return board


def parse_move(move_data):
    """Validate one requested move and convert its squares to engine indices."""
    if not isinstance(move_data, dict) or set(move_data) - {"from", "to", "promotion"}:
        raise ValueError("Each move needs from and to, with optional promotion.")
    start = move_data.get("from")
    end = move_data.get("to")
    promotion = move_data.get("promotion")
    if not isinstance(start, str) or not is_square_name(start):
        raise ValueError("Move from must be a square such as e2.")
    if not isinstance(end, str) or not is_square_name(end):
        raise ValueError("Move to must be a square such as e4.")
    if promotion is not None:
        if not isinstance(promotion, str):
            raise ValueError("promotion must be one of Q, R, B, or N.")
        promotion = promotion.upper()
        if promotion not in _PROMOTIONS:
            raise ValueError("promotion must be one of Q, R, B, or N.")
    return square_to_index(start), square_to_index(end), promotion


def find_matching_move(board, move_data):
    """Resolve user move data against legal moves, rejecting ambiguous promotions."""
    start, end, promotion = parse_move(move_data)
    candidates = [
        move for move in board.getAllLegalMove(board.turn)
        if move.getStartPos() == start and move.getEndPos() == end
    ]
    if not candidates:
        raise ValueError(f"Illegal move: {index_to_square(start)} to {index_to_square(end)}.")
    if len(candidates) > 1:
        if promotion is None:
            raise ValueError("A promotion move must specify promotion as Q, R, B, or N.")
        candidates = [move for move in candidates if move.getPromotion() == promotion]
    elif promotion is not None:
        raise ValueError("promotion is only valid for a pawn promotion move.")
    if not candidates:
        raise ValueError("That promotion choice is not legal.")
    return candidates[0]


def rebuild_game(start_position, moves):
    """Replay validated legal moves and rebuild position counts for repetition detection."""
    board = build_starting_board(start_position)
    position_counts = Counter({board.getHash(): 1})
    for move_data in moves:
        move = find_matching_move(board, move_data)
        board.makeMove(move)
        position_counts[board.getHash()] += 1
    return board, position_counts


def legal_move_data(move):
    """Format a legal move for the stateless web client."""
    promotion = move.getPromotion()
    return {
        "from": index_to_square(move.getStartPos()),
        "to": index_to_square(move.getEndPos()),
        "promotion": promotion,
    }


def game_status(board, position_counts):
    """Return the desktop game's terminal status rules and check state."""
    legal_moves = board.getAllLegalMove(board.turn)
    if not legal_moves:
        if board.kingIsSafe():
            return {"status": "stalemate", "draw_reason": "stalemate"}
        return {"status": "checkmate", "draw_reason": None}
    draw_reason = board.getAutomaticDrawReason()
    if draw_reason:
        return {"status": "draw", "draw_reason": draw_reason.lower()}
    if position_counts.get(board.getHash(), 0) >= 3:
        return {"status": "draw", "draw_reason": "threefold repetition"}
    if not board.kingIsSafe():
        return {"status": "check", "draw_reason": None}
    return {"status": "ongoing", "draw_reason": None}


def legal_moves_response(payload):
    """Return the replayed position's legal moves and game status."""
    start_position, moves = parse_request(payload, require_game_state=True)
    board, position_counts = rebuild_game(start_position, moves)
    return {
        "start_position": start_position,
        "moves": moves,
        "legal_moves": [legal_move_data(move) for move in board.getAllLegalMove(board.turn)],
        "game": game_status(board, position_counts),
    }


def new_game_response(payload):
    """Create a new stateless game description and return its initial legal moves."""
    start_position, moves = parse_request(payload)
    if moves:
        raise ValueError("new-game does not accept moves; use legal-moves or ai-move.")
    board, position_counts = rebuild_game(start_position, [])
    return {
        "start_position": start_position,
        "moves": [],
        "legal_moves": [legal_move_data(move) for move in board.getAllLegalMove(board.turn)],
        "game": game_status(board, position_counts),
    }


def build_ai_response(payload):
    """Choose a bounded AI move and return its evaluation, work count, and new status."""
    start_position, moves = parse_request(payload, require_game_state=True)
    algorithm = payload.get("algorithm")
    if algorithm not in ("alphabeta", "mcts"):
        raise ValueError("algorithm must be 'alphabeta' or 'mcts'.")
    board, position_counts = rebuild_game(start_position, moves)
    before_status = game_status(board, position_counts)
    if before_status["status"] in ("checkmate", "stalemate", "draw"):
        raise ValueError("The game is over; there is no AI move to make.")

    started = time.perf_counter()
    if algorithm == "alphabeta":
        depth = payload.get("depth", 2)
        if type(depth) is not int or not 1 <= depth <= MAX_DEPTH:
            raise ValueError(f"depth must be an integer from 1 to {MAX_DEPTH}.")
        ai = AIThinkTank(board)
        move_id, _, depth_completed, node_count, _ = ai.think_on(
            deepcopy(board), depth, AI_TIME_LIMIT_SECONDS, history=dict(position_counts)
        )
        move = ai.find_real_move(move_id)
        work_count = node_count
        extra = {"depth_completed": depth_completed, "node_count": node_count}
    else:
        iterations = payload.get("mcts_iterations", 100)
        if type(iterations) is not int or not 1 <= iterations <= MAX_MCTS_ITERATIONS:
            raise ValueError(
                f"mcts_iterations must be an integer from 1 to {MAX_MCTS_ITERATIONS}."
            )
        ai = AIThinkTank(board)
        searched_move = mcts_search(
            board, board.turn, iterations=iterations, exploration=0.3, rollout_depth=2
        )
        move = ai.find_real_move(None if searched_move is None else searched_move.getId())
        work_count = iterations
        extra = {"iteration_count": iterations}

    elapsed = time.perf_counter() - started
    if move is None:
        raise ValueError("The selected algorithm did not return a legal move.")
    move_data = legal_move_data(move)
    board.makeMove(move)
    position_counts[board.getHash()] += 1
    result = {
        "move": move_data,
        "start_position": start_position,
        "moves": moves + [move_data],
        "evaluation": Evaluator.evaluate_white(board),
        "time_seconds": round(elapsed, 4),
        "game": game_status(board, position_counts),
    }
    result.update(extra)
    return result


def api_response(endpoint, payload=None):
    """Dispatch a direct API call and convert expected or unexpected errors to JSON results."""
    try:
        if endpoint == "health" and payload is None:
            return 200, {"status": "ok"}
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        if endpoint == "new-game":
            return 200, new_game_response(payload)
        if endpoint == "legal-moves":
            return 200, legal_moves_response(payload)
        if endpoint == "ai-move":
            return 200, build_ai_response(payload)
        return 404, {"error": "Not found."}
    except ValueError as error:
        return 400, {"error": str(error)}
    except Exception:
        return 500, {"error": "Internal server error."}


def create_handler(endpoint):
    """Create a Vercel-compatible HTTP handler for one endpoint."""
    class JsonHandler(BaseHTTPRequestHandler):
        def send_json(self, status_code, data):
            """Write a JSON response without exposing server internals."""
            body = json.dumps(data).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def read_json(self):
            """Read and validate a bounded JSON request body."""
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise ValueError("Content-Length must be an integer.") from error
            if length < 0 or length > MAX_REQUEST_BYTES:
                raise ValueError(f"Request body cannot exceed {MAX_REQUEST_BYTES} bytes.")
            raw_body = self.rfile.read(length)
            try:
                return json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("Request body must contain valid JSON.") from error

        def do_GET(self):
            """Serve the health route and reject unsupported methods."""
            if endpoint == "health":
                status, data = api_response(endpoint)
            else:
                status, data = 405, {"error": "Method not allowed."}
            self.send_json(status, data)

        def do_POST(self):
            """Dispatch a JSON POST and map validation and server failures to safe responses."""
            if endpoint == "health":
                self.send_json(405, {"error": "Method not allowed."})
                return
            try:
                payload = self.read_json()
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
                return
            status, data = api_response(endpoint, payload)
            self.send_json(status, data)

        def log_message(self, format_string, *args):
            """Keep request logging concise and avoid writing details into responses."""
            return

    return JsonHandler


# Vercel treats Python files inside api/ as route files; this package initializer
# must therefore expose a harmless handler as well as the shared API helpers.
handler = create_handler("internal")
