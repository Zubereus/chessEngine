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

    KING_TABLE_END = [
        -50,-40,-30,-20,-20,-30,-40,-50,
        -30,-20,-10,  0,  0,-10,-20,-30,
        -30,-10, 20, 30, 30, 20,-10,-30,
        -30,-10, 30, 40, 40, 30,-10,-30,
        -30,-10, 30, 40, 40, 30,-10,-30,
        -30,-10, 20, 30, 30, 20,-10,-30,
        -30,-30,  0,  0,  0,  0,-30,-30,
        -50,-30,-30,-30,-30,-30,-30,-50,
    ]

    PASSED_PAWN_BONUS = (0, 10, 15, 25, 45, 80, 130, 0)   # indexed by squares advanced from the start rank
    BISHOP_PAIR = 30
    DOUBLED_PAWN = -12
    ISOLATED_PAWN = -10
    ROOK_OPEN_FILE = 20
    ROOK_SEMI_OPEN_FILE = 10
    PHASE_WEIGHT = {PieceType.KNIGHT: 1, PieceType.BISHOP: 1, PieceType.ROOK: 2, PieceType.QUEEN: 4}
    MAX_PHASE = 24

    PIECE_DATA = None
    SIGNED_TABLES = None          # {(team, piece type): 64 white-positive scores, material included}

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

    @classmethod
    def _signed_tables(cls):
        """Black's square is the VERTICAL mirror (index ^ 56). `63 - pos` also flipped the files, which made
        asymmetric tables (the queen's) score a position differently depending on the colour that owned it."""
        if cls.SIGNED_TABLES is None:
            data = cls.get_piece()
            cls.SIGNED_TABLES = {
                (team, piece_type): tuple(
                    (value + table[square if team == Team.WHITE else square ^ 56])
                    * (1 if team == Team.WHITE else -1)
                    for square in range(64)
                )
                for piece_type, (value, table) in data.items()
                for team in (Team.WHITE, Team.BLACK)
            }
        return cls.SIGNED_TABLES

    @staticmethod
    def evaluate_piece(piece):
        value, table = Evaluator.get_piece()[piece.getPieceType()]
        pos = piece.getPosition()
        if piece.getTeam() == Team.WHITE:
            return value + table[pos]
        return -(value + table[pos ^ 56])

    @staticmethod
    def evaluate_white(board):
        """Static score from White's point of view (positive = White is better)."""
        tables = Evaluator._signed_tables()
        score, phase = 0, 0
        bishops = {Team.WHITE: 0, Team.BLACK: 0}
        pawns = {Team.WHITE: [], Team.BLACK: []}
        rooks = []
        kings = {}
        material = {Team.WHITE: 0, Team.BLACK: 0}
        for index, square in enumerate(board.game_board):
            piece = square.pieceOnSquare
            if piece is None:
                continue
            piece_type, team = piece.piece_type, piece.team
            if piece_type == PieceType.KING:
                kings[team] = index
                continue
            score = score + tables[(team, piece_type)][index]
            if piece_type == PieceType.PAWN:
                pawns[team].append(index)
                continue
            material[team] = material[team] + 1
            phase = phase + Evaluator.PHASE_WEIGHT[piece_type]
            if piece_type == PieceType.BISHOP:
                bishops[team] = bishops[team] + 1
            elif piece_type == PieceType.ROOK:
                rooks.append((team, index))

        # kings: blend the middlegame (hide) and endgame (centralise) tables by remaining material
        phase = min(phase, Evaluator.MAX_PHASE)
        for team, index in kings.items():
            sq = index if team == Team.WHITE else index ^ 56
            blended = (
                Evaluator.KING_TABLE_EARLY[sq] * phase + Evaluator.KING_TABLE_END[sq] * (Evaluator.MAX_PHASE - phase)
            ) // Evaluator.MAX_PHASE
            score = score + (blended if team == Team.WHITE else -blended)

        score = score + Evaluator._pawn_structure(pawns, rooks)
        score = score + Evaluator.BISHOP_PAIR * ((bishops[Team.WHITE] >= 2) - (bishops[Team.BLACK] >= 2))
        score = score + Evaluator._mop_up(kings, material, pawns)
        return score

    @staticmethod
    def _pawn_structure(pawns, rooks):
        white, black = pawns[Team.WHITE], pawns[Team.BLACK]
        white_files = [[i // 8 for i in white if i % 8 == f] for f in range(8)]
        black_files = [[i // 8 for i in black if i % 8 == f] for f in range(8)]
        score = 0
        for index in white:
            file, row = index % 8, index // 8
            near = [f for f in (file - 1, file, file + 1) if 0 <= f < 8]
            if not any(r < row for f in near for r in black_files[f]):
                score = score + Evaluator.PASSED_PAWN_BONUS[6 - row]
            if len(white_files[file]) > 1:
                score = score + Evaluator.DOUBLED_PAWN
            if not any(white_files[f] for f in (file - 1, file + 1) if 0 <= f < 8):
                score = score + Evaluator.ISOLATED_PAWN
        for index in black:
            file, row = index % 8, index // 8
            near = [f for f in (file - 1, file, file + 1) if 0 <= f < 8]
            if not any(r > row for f in near for r in white_files[f]):
                score = score - Evaluator.PASSED_PAWN_BONUS[row - 1]
            if len(black_files[file]) > 1:
                score = score - Evaluator.DOUBLED_PAWN
            if not any(black_files[f] for f in (file - 1, file + 1) if 0 <= f < 8):
                score = score - Evaluator.ISOLATED_PAWN
        for team, index in rooks:
            file = index % 8
            own, enemy = (white_files, black_files) if team == Team.WHITE else (black_files, white_files)
            bonus = (
                Evaluator.ROOK_OPEN_FILE if not own[file] and not enemy[file]
                else Evaluator.ROOK_SEMI_OPEN_FILE if not own[file]
                else 0
            )
            score = score + (bonus if team == Team.WHITE else -bonus)
        return score

    @staticmethod
    def _mop_up(kings, material, pawns):
        """Lone king against material: herd it to the edge and bring our king close, or the engine never mates."""
        if Team.WHITE not in kings or Team.BLACK not in kings:
            return 0
        white_alone = material[Team.WHITE] == 0 and not pawns[Team.WHITE]
        black_alone = material[Team.BLACK] == 0 and not pawns[Team.BLACK]
        if white_alone == black_alone:
            return 0
        loser, winner = (Team.WHITE, Team.BLACK) if white_alone else (Team.BLACK, Team.WHITE)
        lrow, lcol = divmod(kings[loser], 8)
        wrow, wcol = divmod(kings[winner], 8)
        edge_distance = max(3 - lrow, lrow - 4) + max(3 - lcol, lcol - 4)
        king_distance = abs(lrow - wrow) + abs(lcol - wcol)
        bonus = 10 * edge_distance + 4 * (14 - king_distance)
        return bonus if winner == Team.WHITE else -bonus

    @staticmethod
    def evaluate(board):
        score = Evaluator.evaluate_white(board)
        return score if board.turn == Team.WHITE else -score

    @staticmethod
    def evaluateEndGame(board):
        """
        0 for stalemate, -CHECKMATE_VALUE when the side to move is checkmated.
        """
        if board.kingIsSafe():
            return 0
        return -Evaluator.CHECKMATE_VALUE
