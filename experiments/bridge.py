"""Bridge between the engine's Board and python-chess (used only as a reference oracle)."""
import sys, os
sys.path.insert(0, os.environ.get('ENGINE_ROOT', os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import chess
from src.chess_replicated.chess_board import (
    Board, Square, Pawn, Knight, Bishop, Rook, Queen, King, Move,
)
from src.chess_replicated.enum_chess import Team, MoveType

CLASS = {chess.PAWN: Pawn, chess.KNIGHT: Knight, chess.BISHOP: Bishop,
         chess.ROOK: Rook, chess.QUEEN: Queen, chess.KING: King}


def to_engine_sq(sq):          # chess a1=0  ->  engine a8=0
    return (7 - chess.square_rank(sq)) * 8 + chess.square_file(sq)


def to_chess_sq(idx):
    return (7 - idx // 8) * 8 + idx % 8


def board_from_fen(fen):
    cb = chess.Board(fen)
    b = Board()
    b.game_board = [Square(None) for _ in range(64)]
    for sq, piece in cb.piece_map().items():
        idx = to_engine_sq(sq)
        team = Team.WHITE if piece.color else Team.BLACK
        cls = CLASS[piece.piece_type]
        first = True
        if piece.piece_type == chess.PAWN:
            first = chess.square_rank(sq) == (1 if piece.color else 6)
        elif piece.piece_type == chess.KING:
            first = cb.has_castling_rights(piece.color)
        elif piece.piece_type == chess.ROOK:
            first = bool(cb.castling_rights & chess.BB_SQUARES[sq])
        b.game_board[idx] = Square(cls(team, idx, first))
        if piece.piece_type == chess.KING:
            if piece.color: b.white_king = b.game_board[idx].getPiece()
            else: b.black_king = b.game_board[idx].getPiece()
    b.turn = Team.WHITE if cb.turn else Team.BLACK
    b.move_history = []
    b.halfmove_clock = cb.halfmove_clock
    if cb.ep_square is not None:
        ep = to_engine_sq(cb.ep_square)
        end = ep + 8 if cb.turn else ep - 8          # square the jumped pawn stands on
        pawn = b.game_board[end].getPiece()
        start = ep - 8 if cb.turn else ep + 8
        fake = Move.__new__(Move)
        fake.piece, fake.attacked_piece, fake.start_pos, fake.end_pos = pawn, None, start, end
        fake.move_type, fake.first_move, fake.is_attacking_move = MoveType.PAWN_JUMP, True, False
        b.move_history.append(fake)
    b.hash_code = None
    return b, cb


PROMO = {"Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP, "N": chess.KNIGHT}


def engine_move_key(m):
    """(from, to, promotion piece type or None) in python-chess terms."""
    return (to_chess_sq(m.getStartPos()), to_chess_sq(m.getEndPos()), PROMO.get(getattr(m, "promotion", None)))


def chess_move_keys(cb):
    return {(m.from_square, m.to_square, m.promotion) for m in cb.legal_moves}


def uci_of(key):
    return chess.Move(key[0], key[1], key[2]).uci()


def find_engine_move(b, key):
    return next(filter(lambda m: engine_move_key(m) == key, b.getAllLegalMove(b.turn)))


def snapshot(b):
    return tuple((i, type(s.getPiece()).__name__, s.getPiece().getTeam(), s.getPiece().isFirstMove())
                 for i, s in enumerate(b.game_board) if not s.isEmpty()) + (b.turn,)
