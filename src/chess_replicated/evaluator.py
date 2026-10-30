from .enum_chess import Team, PieceType

class Evaluator:
    PAWN_VALUE = 100
    KNIGHT_VALUE = 320
    BISHOP_VALUE = 330
    ROOK_VALUE = 500
    QUEEN_VALUE = 900
    KING_VALUE = 20000
    CHECKMATE_VALUE = 100000

    PAWN_TABLE = [
         0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0,
    ]

    KNIGHT_TABLE = [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50,
    ]

    BISHOP_TABLE = [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20,
    ]

    ROOK_TABLE = [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         0,  0,  0,  5,  5,  0,  0,  0,
    ]

    QUEEN_TABLE = [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20,
    ]

    KING_TABLE_EARLY = [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20,
    ]

    PIECE_DATA = None

    @classmethod
    def get_piece(cls):
        if cls.PIECE_DATA is None:
            cls.PIECE_DATA = {
                PieceType.PAWN: (cls.PAWN_VALUE, cls.PAWN_TABLE),
                PieceType.KNIGHT: (cls.KNIGHT_VALUE, cls.KNIGHT_TABLE),
                PieceType.BISHOP: (cls.BISHOP_VALUE, cls.BISHOP_TABLE),
                PieceType.ROOK:  (cls.ROOK_VALUE, cls.ROOK_TABLE),
                PieceType.QUEEN: (cls.QUEEN_VALUE, cls.QUEEN_TABLE),
                PieceType.KING: (cls.KING_VALUE, cls.KING_TABLE_EARLY),
            }
        return cls.PIECE_DATA
    @staticmethod
    def evaluate_piece(piece):
        piece_data = Evaluator.get_piece()
        value, table = piece_data[piece.getPieceType()]
        pos = piece.getPosition()

        if piece.getTeam() == Team.WHITE:
            return value + table[pos]
        else:
            return -(value + table[63 - pos])
    @staticmethod
    def evaluate(board):
        score = sum(Evaluator.evaluate_piece(square.getPiece())
            for square in board.game_board
            if not square.isEmpty())
        
        return score if board.turn == Team.WHITE else -score
    @staticmethod
    def evaluateEndGame(board):
        """
        Trả về 0 nếu hòa cờ (stalemate),
        -100_000 nếu bị chiếu hết (checkmate).
        """
        if board.kingIsSafe():
            return 0
        return -Evaluator.CHECKMATE_VALUE
