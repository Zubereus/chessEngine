import random
from .enum_chess import*
class Zobrist:
    """
    Cấu trúc hash:
    - piece_vals[màu][loại quân][ô] — vị trí từng quân
    - moved_piece_vals                 — trạng thái đã di chuyển của từng quân
    - black_to_move                 — lượt đi của Đen 
    - castles[4]                    — quyền nhập thành (trắng ngắn/dài, đen ngắn/dài)
    - en_passant[8]                 — cột en passant (a-h)
    
    random.getrandbits(64): trả về một số nguyên không âm có giá trị nằm trong khoảng 0-2^64-1
    """
    
    PIECE_INDEX ={
        PieceType.PAWN : 0, PieceType.ROOK : 1, PieceType.KNIGHT : 2, PieceType.BISHOP : 3, PieceType.QUEEN : 4, PieceType.KING : 5,
    }

    TEAM_INDEX ={
        Team.WHITE : 0,
        Team.BLACK : 1,
    }

    WHITE_SHORT = 0
    WHITE_LONG = 1
    BLACK_SHORT = 2
    BLACK_LONG = 3

    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
            cls.instance.init_table()
        return cls.instance
    
    def init_table(self, seed = None):
        rng = random.Random(seed) #For debug case
        self.black_to_move = rng.getrandbits(64)

        # castles[4]: WHITE_SHORT, WHITE_LONG, BLACK_SHORT, BLACK_LONG, nhập thành có 4 case
        self.castle = [rng.getrandbits(64) for _ in range(4)]
        # mã hóa cho các cột từ 0-7
        self.en_passant = [rng.getrandbits(64) for _ in range(8)]

        # mã hóa cho giá trị của từng quân cờ
        self.piece_vals = [
            [
                [rng.getrandbits(64) for _ in range(64)]
                for _ in range(6)
            ]
            for _ in range(2)
        ]
        self.piece_table = {
            (team, piece_type): self.piece_vals[Zobrist.TEAM_INDEX[team]][Zobrist.PIECE_INDEX[piece_type]]
            for team in Zobrist.TEAM_INDEX
            for piece_type in Zobrist.PIECE_INDEX
        }
        self.moved_piece_vals = [
            [
                [rng.getrandbits(64) for _ in range(64)]
                for _ in range(6)
            ]
            for _ in range(2)
        ]
    
    def __deepcopy__(self, memo):
        return self      # the tables never change, so copies can share them

    def getBlackToMove(self):
        return self.black_to_move
    
    def getCastle(self, castle_index):
        return self.castle[castle_index]
    
    def getEnPassant(self, file):
        return self.en_passant[file]
    
    def getPieceValue(self, team, piece_type, square):
        t = Zobrist.TEAM_INDEX[team]
        p = Zobrist.PIECE_INDEX[piece_type]
        return self.piece_vals[t][p][square]

    def getFullHash(self, board):
        h = 0
        
        # Only piece type + square matter. The "has moved" flags are redundant:
        # castling rights are hashed below, and a pawn's first move follows from its row.
        table = self.piece_table
        for index, square in enumerate(board.game_board):
            piece = square.pieceOnSquare
            if piece is not None:
                h ^= table[(piece.getTeam(), piece.getPieceType())][index]
        if board.turn == Team.BLACK:
            h ^= self.black_to_move

        for team, king_start, short_index, long_index in (
            (Team.WHITE, 60, Zobrist.WHITE_SHORT, Zobrist.WHITE_LONG),
            (Team.BLACK, 4, Zobrist.BLACK_SHORT, Zobrist.BLACK_LONG),
        ):
            king = board.getSquare(king_start).getPiece()
            if (
                king is None
                or king.getPieceType() != PieceType.KING
                or king.getTeam() != team
                or not king.isFirstMove()
            ):
                continue
            short_rook = board.getSquare(king_start + 3).getPiece()
            if (
                short_rook is not None
                and short_rook.getPieceType() == PieceType.ROOK
                and short_rook.getTeam() == team
                and short_rook.isFirstMove()
            ):
                h ^= self.castle[short_index]
            long_rook = board.getSquare(king_start - 4).getPiece()
            if (
                long_rook is not None
                and long_rook.getPieceType() == PieceType.ROOK
                and long_rook.getTeam() == team
                and long_rook.isFirstMove()
            ):
                h ^= self.castle[long_index]

        #Luật bắt tốt qua đường
        #Cách hoạt động: nếu nước cuối có label "PAWN_JUMP" thì kiểm tra 2 bên trái, phải của pawn xem có tồn tại enemy_pawn không
        # Nếu có thì cột của enemy_pawn là enpassant col, cần phải thực hiện hashing
        last_move = board.peekLastMove()

        if last_move is not None and last_move.getType() == MoveType.PAWN_JUMP:
            end_pos = last_move.getEndPos()
            row, col = divmod(end_pos, 8)
            adjacent_positions = []
            if col > 0:
                adjacent_positions.append(row * 8 + col - 1)
            if col < 7:
                adjacent_positions.append(row * 8 + col + 1)
            for position in adjacent_positions:
                piece = board.getSquare(position).getPiece()
                if (
                    piece is not None
                    and piece.getTeam() == board.turn
                    and piece.getPieceType() == PieceType.PAWN
                ):
                    h ^= self.en_passant[col]
                    break
        
        return h
    

    def updateHash(self, board):
        """Rebuild the position hash, including castling and en-passant state."""
        return self.getFullHash(board)