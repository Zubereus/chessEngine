class Team:
    BLACK = "BLACK"
    WHITE = "WHITE"
class MoveType:
    """Thay thế cho Enum moveType trong Java"""
    HEAVY = "HEAVY"
    ATTACK = "ATTACK"
    HEAVY_ATTACK = "HEAVY_ATTACK"
    PAWN = "PAWN"
    PAWN_JUMP = "PAWN_JUMP"
    PAWN_ATTACK = "PAWN_ATTACK"
    ENPASSENT = "ENPASSENT"
    SHORT_CASTLE = "SHORT_CASTLE"
    LONG_CASTLE = "LONG_CASTLE"

class PieceType:
    PAWN, ROOK, KNIGHT, BISHOP, QUEEN, KING = 'P', 'R', 'N', 'B', 'Q', 'K'