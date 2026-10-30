
import random
from .enum_chess import*
class Zobrist:
    """
    Cấu trúc hash:
    - piece_vals[màu][loại quân][ô] — vị trí từng quân
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
        
        for index, square in enumerate(board.game_board):
            if not square.isEmpty():
                piece = square.getPiece()
                h ^= self.getPieceValue(piece.getTeam(), piece.getPieceType(), index)
        if board.turn == Team.BLACK:
            h ^= self.black_to_move
        
        if board.canShortCastle(Team.WHITE):
            h ^= self.castle[Zobrist.WHITE_SHORT]
        if board.canLongCastle(Team.WHITE):
            h ^= self.castle[Zobrist.WHITE_LONG]
        if board.canShortCastle(Team.BLACK):
            h ^= self.castle[Zobrist.BLACK_SHORT]
        if board.canLongCastle(Team.BLACK):
            h ^= self.castle[Zobrist.BLACK_LONG]

        #Luật bắt tốt qua đường
        #Cách hoạt động: nếu nước cuối có label "PAWN_JUMP" thì kiểm tra 2 bên trái, phải của pawn xem có tồn tại enemy_pawn không
        # Nếu có thì cột của enemy_pawn là enpassant col, cần phải thực hiện hashing
        last_move = board.peekLastMove()

        if(last_move != None and last_move.getType() == MoveType.PAWN_JUMP):
            left_square = board.getSquare(last_move.getEndPos() + 1)
            if(not left_square.isEmpty()):
                pice_left = left_square.getPiece()
                if(pice_left.getTeam() == board.turn and pice_left.getPieceType() == PieceType.PAWN):
                    ep_file = last_move.getEndPos() % 8
                    h ^= self.en_passant[ep_file]
                    return h

            right_square = board.getSquare(last_move.getEndPos() - 1)
            if (not right_square.isEmpty()):
                piece_right = right_square.getPiece()
                if(piece_right.getTeam() == board.turn and piece_right.getPieceType() == PieceType.PAWN):
                    ep_file = last_move.getEndPos() % 8
                    h ^= self.en_passant[ep_file]
        
        return h
    

    def updateHash(self, hash_code, move, board):
        start_pos = move.getStartPos()
        end_pos = move.getEndPos()
        piece = move.getPiece()
        piece_type = piece.getPieceType()
        team = piece.getTeam()
        hasEnPassant = False
        if board.canShortCastle(Team.WHITE):
            hash_code ^= self.castle[self.WHITE_SHORT]
        if board.canLongCastle(Team.WHITE):
            hash_code ^= self.castle[self.WHITE_LONG]
        if board.canShortCastle(Team.BLACK):
            hash_code ^= self.castle[self.BLACK_SHORT]
        if board.canLongCastle(Team.BLACK):
            hash_code ^= self.castle[self.BLACK_LONG]
        

        #Bắt tốt qua đường
        #Luật bắt tốt qua đường
        #Cách hoạt động: nếu nước cuối có label "PAWN_JUMP" thì kiểm tra 2 bên trái, phải của pawn xem có tồn tại enemy_pawn không
        # Nếu có thì cột của enemy_pawn là enpassant col, cần phải thực hiện hashing
        last_move = board.peekLastMove()

        if(last_move != None and last_move.getType() == MoveType.PAWN_JUMP):
            left_square = board.getSquare(last_move.getEndPos() + 1)
            if(not left_square.isEmpty()):
                piece_left = left_square.getPiece()
                if(piece_left.getTeam() == board.turn and piece_left.getPieceType() == PieceType.PAWN):
                    ep_file = last_move.getEndPos() % 8
                    hash_code ^= self.en_passant[ep_file]
                    hasEnPassant = True
            if(not hasEnPassant):
                right_square = board.getSquare(last_move.getEndPos() - 1)
                if (not right_square.isEmpty()):
                    piece_right = right_square.getPiece()
                    if(piece_right.getTeam() == board.turn and piece_right.getPieceType() == PieceType.PAWN):
                        ep_file = last_move.getEndPos() % 8
                        hash_code ^= self.en_passant[ep_file]
        #Lần hash đầu tiên nếu quân cờ đã có trong hash table, loại bỏ
        hash_code ^= self.getPieceValue(team, piece_type,start_pos)
        #Khi ở vị trí mới thì thêm vào
        hash_code ^= self.getPieceValue(team, piece_type,end_pos)
        hash_code ^= self.black_to_move
        return hash_code
        

