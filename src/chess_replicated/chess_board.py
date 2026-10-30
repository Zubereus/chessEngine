from abc import ABC, abstractmethod
from .zobrist import Zobrist
from .enum_chess import*
import random

class Utility:
    # Các hằng số cơ bản
    WHITE_KING_START_POSITION = 60
    BLACK_KING_START_POSITION = 4
    BOARD_SQUARE_COUNT = 64
    RANK_SQUARE_COUNT = 8

    # Trong Python, thay vì tạo mảng boolean 64 phần tử (tốn bộ nhớ), 
    # chúng ta có thể dùng phép chia lấy dư (%) để kiểm tra cột cực nhanh.
    
    @staticmethod
    def isValidPosition(position):
        """Kiểm tra vị trí có nằm trong khoảng 0-63 không"""
        return 0 <= position < Utility.BOARD_SQUARE_COUNT

    @staticmethod
    def isBackRank(piece):
        """Kiểm tra xem quân tốt đã đi đến hàng cuối để phong cấp chưa"""
        if piece is None:
            return False
        rank = piece.getPosition() // Utility.RANK_SQUARE_COUNT
        # Trắng đến hàng 0 (rank 0), Đen đến hàng 7 (rank 7)
        return (rank == 0 and piece.getTeam() == "WHITE") or \
               (rank == 7 and piece.getTeam() == "BLACK")
    @staticmethod
    def isFirstFile(position): return position % 8 == 0
    @staticmethod
    def isSecondFile(position): return position % 8 == 1
    @staticmethod
    def isSeventhFile(position): return position % 8 == 6
    @staticmethod
    def isEighthFile(position): return position % 8 == 7


class Move:
    def __init__(self, piece, end_pos, move_type,  attacked_piece=None):
        self.piece = piece
        self.attacked_piece = attacked_piece
        self.start_pos = piece.getPosition()
        self.end_pos = end_pos
        self.move_type = move_type
        self.first_move = piece.isFirstMove()

        if attacked_piece:
            self.attacked_piece = attacked_piece.copyOf()
            self.is_attacking_move = True
        else:
            self.attacked_piece = None
            self.is_attacking_move = False
    def getEndPos(self):
        return self.end_pos
    def getStartPos(self):
        return self.start_pos
    def getPiece(self):
        return self.piece
    def getType(self):
        return self.move_type
    def getAttackedPiece(self):
        if self.attacked_piece: return self.attacked_piece
        else: return None
    def isAttackingMove(self):
        return self.is_attacking_move
    def isFirstMove(self):
        return self.first_move
    

class Piece(ABC):
    def __init__(self, piece_type, team, position, first_move=True):
        self.piece_type = piece_type
        self.position = position
        self.team = team #black or white
        self.first_move = first_move # is first move ?
    
    def getPosition(self):
        return self.position
    
    def getTeam(self):
        return self.team
    
    def isFirstMove(self):
        return self.first_move == True
    
    def copyOf(self):
        return self.__class__(self.team, self.position, self.first_move)
    
    def setIsFirstMove(self, isFirstMove):
        self.first_move = isFirstMove
    def getPieceType(self):
        return self.piece_type
    
    def setPosition(self, position):
        self.position = position
    
    @abstractmethod
    def generatePossibleMove(self, board):
        pass

    def __str__(self):
        return self.piece_type

class Pawn(Piece):
    
    def __init__(self, team, position, first_move=True):
        super().__init__(PieceType.PAWN, team, position, first_move)
        self.current_offset = [7,8,9]
    def generatePossibleMove(self, board):
        moveList = []
        i = 1 if self.getTeam() == "BLACK" else -1
        for offset in self.current_offset:
            proposed_pos = self.getPosition() + offset*i
            if(Utility.isValidPosition(proposed_pos)):
                if offset == 8 and board.getSquare(proposed_pos).isEmpty():
                    moveList.append(Move(self, proposed_pos, MoveType.PAWN))
                    proposed_pos += offset*i
                    if(self.isFirstMove() and board.getSquare(proposed_pos).isEmpty()):
                        moveList.append(Move(self, proposed_pos, MoveType.PAWN_JUMP))
                elif offset == 7 or offset == 9:
                    if(Pawn.isFileEdgeCase(self.getPosition(),offset*i)): continue
                    enpassantOffset = 1 if offset == 7 else -1
                    if self.getTeam() == Team.BLACK: enpassantOffset *=-1
                    if board.peekLastMove() != None and board.peekLastMove().getType() == MoveType.PAWN_JUMP:
                        if board.peekLastMove().getEndPos() == self.getPosition() + enpassantOffset:
                            moveList.append(Move(self,proposed_pos,MoveType.ENPASSENT))
                    
                    if not board.getSquare(proposed_pos).isEmpty() and board.getSquare(proposed_pos).getPiece().getTeam() != self.getTeam():
                        moveList.append(Move(self,proposed_pos,MoveType.PAWN_ATTACK,board.getSquare(proposed_pos).getPiece()))
        return moveList
       
    @staticmethod
    def isFileEdgeCase(position, offset):
        isFirstEdgeCase = Utility.isFirstFile(position) and (offset == 7 or offset == -9)
        isEightEdgeCase = Utility.isEighthFile(position) and (offset == 9 or offset == -7)
        return isFirstEdgeCase or isEightEdgeCase

class Knight(Piece):

    def __init__(self, team, position, first_move = True):
        super().__init__(PieceType.KNIGHT, team, position, first_move)
        self.current_offset = [6, 10, 15, 17]


    def generatePossibleMove(self, board):
        moveList = []
        for offset in self.current_offset:
            for i in range(-1,2,2):
                if(Knight.isFileEdgeCase(self.getPosition(), offset*i)): continue
                destination = self.getPosition() + offset*i
                if(Utility.isValidPosition(destination)):
                    propose_square = board.getSquare(destination)
                    if(propose_square.isEmpty()):
                        moveList.append(Move(self,destination,MoveType.HEAVY))
                    else:
                        piece_destination = propose_square.getPiece()
                        opponent_team = piece_destination.getTeam()
                        if(self.getTeam() != opponent_team): moveList.append(Move(self,destination,MoveType.ATTACK,piece_destination))
        
        return moveList
    @staticmethod
    def isFileEdgeCase(position,offset):
        isFirstEdgeCase = Utility.isFirstFile(position) and (offset == -17 or offset == -10 or offset == 6 or offset == 15)
        isSecondEdgeCase = Utility.isSecondFile(position) and (offset == -10 or offset == 6)
        isSevenEdgeCase = Utility.isSeventhFile(position) and (offset == -6 or offset == 10)
        isEightEdgeCase = Utility.isEighthFile(position) and (offset == -15 or offset == -6 or
                offset == 10 or offset == 17)
        return isFirstEdgeCase or isSecondEdgeCase or isSevenEdgeCase or isEightEdgeCase
    

class Bishop(Piece):
    def __init__(self, team, position, first_move = True):
        super().__init__(PieceType.BISHOP, team, position, first_move)
        self.current_offset = [7,9]
    
    
    def generatePossibleMove(self, board):
        moveList = []

        for offset in self.current_offset:
            for i in range(-1,2,2):
                propose_pos = self.getPosition()
                while(Utility.isValidPosition(propose_pos)):
                    if(Bishop.isFileEdgeCase(propose_pos, offset*i)): break
                    propose_pos += offset*i

                    if(Utility.isValidPosition(propose_pos)):
                        propose_square = board.getSquare(propose_pos)
                        if(propose_square.isEmpty()):
                            moveList.append(Move(self,propose_pos,MoveType.HEAVY))
                        else:
                            piece_destination = propose_square.getPiece()
                            if(self.getTeam() != piece_destination.getTeam()):
                                moveList.append(Move(self, propose_pos,MoveType.HEAVY_ATTACK,piece_destination))
                            break
        return moveList

    @staticmethod
    def isFileEdgeCase(position, offset):
        isFirstEdgeCase = Utility.isFirstFile(position) and (offset == 7 or offset == -9)
        isEightEdgeCase = Utility.isEighthFile(position) and (offset == 9 or offset == -7)
        return isFirstEdgeCase or isEightEdgeCase

class Rook(Piece):
    def __init__(self, team, position, first_move = True):
        super().__init__(PieceType.ROOK, team, position, first_move)
        self.current_offset = [1,8]
    
    
    def generatePossibleMove(self, board):
        moveList = []
        for offset in self.current_offset:
            for i in range(-1,2,2):
                propose_pos = self.getPosition()
                while Utility.isValidPosition(propose_pos):
                    if(Rook.isFileEdgeCase(propose_pos,offset*i)): break
                    propose_pos += offset*i
                    if(Utility.isValidPosition(propose_pos)):
                        propose_square = board.getSquare(propose_pos)
                        if(propose_square.isEmpty()):
                            moveList.append(Move(self, propose_pos, MoveType.HEAVY))
                        else:
                            piece_destination = propose_square.getPiece()
                            if(piece_destination.getTeam() != self.getTeam()):
                                moveList.append(Move(self, propose_pos,MoveType.HEAVY_ATTACK,piece_destination))
                            break;
        return moveList

    @staticmethod
    def isFileEdgeCase(position, offset):
        isFirstEdgeCase = Utility.isFirstFile(position) and offset == -1
        isEightEdgeCase = Utility.isEighthFile(position) and offset == 1
        return isEightEdgeCase or isFirstEdgeCase
    
class Queen(Piece):
    def __init__(self, team, position, first_move = True):
        super().__init__(PieceType.QUEEN, team, position, first_move)
        self.current_offset = [1,7,8,9]
    
    
    def generatePossibleMove(self, board):
        moveList = []
        for offset in self.current_offset:
            for i in range(-1,2,2):
                propose_pos = self.getPosition()
                while(Utility.isValidPosition(propose_pos)):
                    if(Queen.isFileEdgeCase(propose_pos,offset*i)): break
                    propose_pos += offset*i
                    if(Utility.isValidPosition(propose_pos)):
                        propose_square = board.getSquare(propose_pos)
                        if(propose_square.isEmpty()): moveList.append(Move(self, propose_pos, MoveType.HEAVY))
                        else:
                            piece_destination = propose_square.getPiece()
                            if(piece_destination.getTeam() != self.getTeam()):
                                moveList.append(Move(self,propose_pos,MoveType.HEAVY_ATTACK,piece_destination))
                            break
        
        return moveList
    
    @staticmethod
    def isFileEdgeCase(position, offset):
        isFirstEdgeCase = Utility.isFirstFile(position) and (offset == -1 or offset == 7 or offset == -9)
        isEightEdgeCase = Utility.isEighthFile(position) and (offset == 1 or offset == 9 or offset == -7)
        return isFirstEdgeCase or isEightEdgeCase

class King(Piece):
    def __init__(self, team, position, first_move=True):
        super().__init__(PieceType.KING, team, position, first_move)
        self.current_offset = [1,7,8,9]
    
    def generatePossibleMove(self, board):
        moveList = []
        
        for offset in self.current_offset:
            for i in range(-1,2,2):
                propose_pos = self.getPosition()
                if(King.isFileEdgeCase(propose_pos,offset*i)): continue
                propose_pos += offset*i

                if(Utility.isValidPosition(propose_pos)):
                    propose_square = board.getSquare(propose_pos)
                    if(propose_square.isEmpty()): moveList.append(Move(self, propose_pos, MoveType.HEAVY))
                    else:
                        piece_destination = propose_square.getPiece()
                        if(piece_destination.getTeam() != self.getTeam()):
                            moveList.append(Move(self,propose_pos,MoveType.HEAVY_ATTACK,piece_destination))
        return moveList


    @staticmethod
    def isFileEdgeCase(position, offset):
        isFirstEdgeCase = Utility.isFirstFile(position) and (offset == -1 or offset == 7 or offset == -9)
        isEightEdgeCase = Utility.isEighthFile(position) and (offset == 1 or offset == 9 or offset == -7)
        return isFirstEdgeCase or isEightEdgeCase

class Square:
    def __init__(self, pieceOnSquare):
        self.pieceOnSquare = pieceOnSquare
    
    def isEmpty(self):
        return self.pieceOnSquare is None
    def getPiece(self):
        return self.pieceOnSquare
    def setPiece(self, pieceOnSquare):
        self.pieceOnSquare = pieceOnSquare
    
    def __str__(self):
        if self.isEmpty():
            return "-"
        else:
            piece_str = str(self.pieceOnSquare)
            if self.pieceOnSquare.getTeam() == Team.WHITE:
                return piece_str
            else:
                return piece_str.lower()


class Board:
    def __init__(self):
        self.zobrist = Zobrist()
        self.game_board = [Square(None) for _ in range(64)]
        self.turn = Team.WHITE
        self.move_history = []
        self.setUpStandardBoard()
        self.white_king = self.game_board[Utility.WHITE_KING_START_POSITION].getPiece()
        self.black_king = self.game_board[Utility.BLACK_KING_START_POSITION].getPiece()
        self.hash_code = self.zobrist.getFullHash(self)
        
    
    def setUpStandardBoard(self):
        self.game_board[0] = Square(Rook(Team.BLACK, 0))
        self.game_board[1] = Square(Knight(Team.BLACK, 1))
        self.game_board[2] = Square(Bishop(Team.BLACK, 2))
        self.game_board[3] = Square(Queen(Team.BLACK, 3))
        self.game_board[4] = Square(King(Team.BLACK, 4))
        self.game_board[5] = Square(Bishop(Team.BLACK, 5))
        self.game_board[6] = Square(Knight(Team.BLACK, 6))
        self.game_board[7] = Square(Rook(Team.BLACK, 7))

        for i in range(8, 16): self.game_board[i] = Square(Pawn(Team.BLACK, i))

        for i in range(48, 56): self.game_board[i] = Square(Pawn(Team.WHITE, i))

        self.game_board[56] = Square(Rook(Team.WHITE, 56))
        self.game_board[57] = Square(Knight(Team.WHITE, 57))
        self.game_board[58] = Square(Bishop(Team.WHITE, 58))
        self.game_board[59] = Square(Queen(Team.WHITE, 59))
        self.game_board[60] = Square(King(Team.WHITE, 60))
        self.game_board[61] = Square(Bishop(Team.WHITE, 61))
        self.game_board[62] = Square(Knight(Team.WHITE, 62))
        self.game_board[63] = Square(Rook(Team.WHITE, 63))
    
    def setUpRandomBoard(self, white_dict, black_dict):
        # Khởi tạo bàn cờ trống (chỉ 1 lần)
        self.game_board = [Square(None) for _ in range(64)]
        
        # Tạo danh sách tất cả vị trí và xáo trộn 1 lần duy nhất
        all_positions = list(range(64))
        random.shuffle(all_positions)

        w_king = white_dict.pop("king", 0)
        b_king = black_dict.pop("king", 0)

        def place_pieces(count_dict, team):
            # Lấy các ô không hợp lệ cho Pawn của team này
            invalid_for_pawn = [0,1,2,3,4,5,6,7,56,57,58,59,60,61,62,63]
            
            for piece_type, count in count_dict.items():
                for _ in range(count):
                    # Tìm một ô trống hợp lệ
                    found_pos = None
                    for i, pos in enumerate(all_positions):
                        # Nếu là Pawn, không được nằm ở hàng cuối của nó
                        if piece_type == "pawn" and pos in invalid_for_pawn:
                            continue
                        
                        # Nếu ô này hợp lệ, lấy nó ra khỏi danh sách dùng chung
                        found_pos = all_positions.pop(i)
                        break
                    
                    if found_pos is not None:
                        cls_map = {"queen": Queen, "rook": Rook, 
                                "bishop": Bishop, "knight": Knight, "pawn": Pawn}
                        if piece_type == "pawn":
                            piece = cls_map[piece_type](team, found_pos, first_move=False)
                        else:
                            piece = cls_map[piece_type](team, found_pos)
                        self.game_board[found_pos] = Square(piece)
                        

        # --- Đặt quân ---
        place_pieces(white_dict, Team.WHITE)
        place_pieces(black_dict, Team.BLACK)

        def place_king(team):
            enemy_team = Team.BLACK if team == Team.WHITE else Team.WHITE
            for i, pos in enumerate(all_positions):
                # Tạm thời đặt thử King vào ô này
                test_king = King(team, pos)
                self.game_board[pos] = Square(test_king)
                
                # Kiểm tra xem ô này có bị quân đối phương tấn công không
                if self.isSquareSafe(pos, enemy_team):
                    all_positions.pop(i)
                    if team == Team.WHITE: self.white_king = test_king
                    else: self.black_king = test_king
                    return # Đã đặt xong King hợp lệ
                else:
                    # Nếu bị chiếu, xóa đi và thử ô khác
                    self.game_board[pos] = Square(None)
            
            # Trường hợp xấu nhất: Không tìm được ô nào không bị chiếu (hiếm gặp)
            # Có thể lấy đại ô đầu tiên nếu danh sách all_positions vẫn còn
            if all_positions:
                pos = all_positions.pop(0)
                king = King(team, pos)
                self.game_board[pos] = Square(king)
                if team == Team.WHITE: self.white_king = king
                else: self.black_king = king
            
        place_king(Team.WHITE)
        place_king(Team.BLACK)

        white_dict["king"] = w_king
        black_dict["king"] = b_king

    def getSquare(self, position):
        return self.game_board[position]
    
    def peekLastMove(self):
        return self.move_history[-1] if self.move_history else None
    
    def guiRequestMove(self, start_pos, end_pos):
        legalMove = self.getAllLegalMove(self.turn)
        for move in legalMove:
            if(move.getPiece().getPosition() == start_pos and move.getEndPos() == end_pos):
                self.makeMove(move)
                return True
        return False

    
    def movePiece(self, start_pos, end_pos, is_first_move):
        start_square = self.game_board[start_pos]
        end_square = self.game_board[end_pos]
        piece_to_move = None
        if not start_square.isEmpty():
            piece_to_move = start_square.getPiece()
            piece_to_move.setIsFirstMove(is_first_move)
            piece_to_move.setPosition(end_pos)
        
        start_square.setPiece(None)
        end_square.setPiece(piece_to_move)
    
    def makeMove(self, move):
        self.toggleTurn()
        self.movePiece(move.getStartPos(), move.getEndPos(), False)
        
        m_type = move.getType()

        if m_type == MoveType.ENPASSENT:
            offset = -8 if self.turn == Team.WHITE else 8
            attack_pawn_pos = move.getEndPos() + offset
            self.getSquare(attack_pawn_pos).setPiece(None)
        elif m_type == MoveType.SHORT_CASTLE:
            rookStartPos = move.getStartPos() + 3
            rookEndPos = move.getStartPos() + 1
            self.movePiece(rookStartPos, rookEndPos, False)
        elif m_type == MoveType.LONG_CASTLE:
            rookStartPos = move.getStartPos() - 4
            rookEndPos = move.getStartPos() - 1
            self.movePiece(rookStartPos, rookEndPos, False)
        elif m_type in [MoveType.PAWN, MoveType.PAWN_ATTACK]:
            piece_at_des = self.game_board[move.getEndPos()].getPiece()
            if piece_at_des is not None and Utility.isBackRank(piece_at_des):
                promotion_piece = Queen(move.getPiece().getTeam(), move.getEndPos(), False)
                self.getSquare(move.getEndPos()).setPiece(promotion_piece)
        
        self.move_history.append(move)
        self.hash_code = self.zobrist.updateHash(self.hash_code, move, self)
            

    def undoMove(self):
        move = self.move_history.pop()
    
        m_type = move.getType()

        if m_type == MoveType.ENPASSENT:
            offset = -8 if self.turn == Team.WHITE else 8
            piece_attacked = Pawn(self.turn, move.getEndPos() + offset, False)
            attacked_pos = piece_attacked.getPosition()
            self.getSquare(attacked_pos).setPiece(piece_attacked)
        elif m_type == MoveType.SHORT_CASTLE:
            rook_start_pos = move.getStartPos() + 3
            rook_end_pos = move.getStartPos() + 1
            self.movePiece(rook_end_pos,rook_start_pos, True)
        elif m_type == MoveType.LONG_CASTLE:
            rook_start_pos = move.getStartPos() - 4
            rook_end_pos = move.getStartPos() - 1
            self.movePiece(rook_end_pos,rook_start_pos, True)
        elif m_type in [MoveType.PAWN, MoveType.PAWN_ATTACK]:
            piece_at_des = self.game_board[move.getEndPos()].getPiece()
            if piece_at_des is not None and Utility.isBackRank(piece_at_des):
                move.getPiece().setPosition(move.getEndPos())
                self.getSquare(move.getEndPos()).setPiece(move.getPiece())
        
        self.movePiece(move.getEndPos(), move.getStartPos(), move.isFirstMove())
        if m_type == MoveType.ENPASSENT:
            self.game_board[move.getEndPos()].setPiece(None)
        else:
            attacked = move.getAttackedPiece()
            if attacked is not None:
                attacked.setPosition(move.getEndPos())  # ← thêm sync
                self.game_board[move.getEndPos()].setPiece(attacked)
            else:
                self.game_board[move.getEndPos()].setPiece(None)
        self.toggleTurn()
        self.hash_code = self.zobrist.updateHash(self.hash_code, move, self)

    def kingIsSafe(self):
        king = self.white_king if self.turn == Team.WHITE else self.black_king

        enemy_team = Team.BLACK if self.turn == Team.WHITE else Team.WHITE
        return self.isSquareSafe(king.getPosition(), enemy_team)
    def isSquareSafe(self,position, enemy):
        for move in self.getAllPossibleMove(enemy):
            if move.getEndPos() == position:
                return False
        return True
    def toggleTurn(self):
        self.turn = Team.WHITE if self.turn == Team.BLACK else Team.BLACK
    def getAllPossibleMove(self,team):
        possible_move_list = []
        for index, square in enumerate(self.game_board):
            if not square.isEmpty() and square.getPiece().getTeam() == team :
                piece = square.getPiece()
                piece.setPosition(index)
                possible_move_list.extend(piece.generatePossibleMove(self))

        return possible_move_list    
    

    def canShortCastle(self,team):
        king_start_pos = Utility.WHITE_KING_START_POSITION if team == Team.WHITE else Utility.BLACK_KING_START_POSITION
        rook_start_pos = king_start_pos + 3
        enemy_turn = Team.BLACK if team == Team.WHITE else Team.WHITE
        if(self.getSquare(king_start_pos).isEmpty() or self.getSquare(rook_start_pos).isEmpty()): return False
        pice_should_be_king = self.getSquare(king_start_pos).getPiece()
        piece_should_be_rook = self.getSquare(rook_start_pos).getPiece()

        if (isinstance(pice_should_be_king,King) and pice_should_be_king.isFirstMove() and isinstance(piece_should_be_rook,Rook)
            and piece_should_be_rook.isFirstMove() and self.getSquare(king_start_pos+1).isEmpty()
            and self.getSquare(king_start_pos+2).isEmpty()):
            for i in range(1,3):
                if(not self.isSquareSafe(king_start_pos + i,enemy_turn)): return False

            return True
        return False

    def canLongCastle(self,team):
        king_start_pos = Utility.WHITE_KING_START_POSITION if team == Team.WHITE else Utility.BLACK_KING_START_POSITION
        rook_start_pos = king_start_pos - 4
        enemy_turn = Team.BLACK if team == Team.WHITE else Team.WHITE
        if(self.getSquare(king_start_pos).isEmpty() or self.getSquare(rook_start_pos).isEmpty()): return False
        pice_should_be_king = self.getSquare(king_start_pos).getPiece()
        piece_should_be_rook = self.getSquare(rook_start_pos).getPiece()
        if (isinstance(pice_should_be_king,King) and pice_should_be_king.isFirstMove() and isinstance(piece_should_be_rook,Rook)
            and piece_should_be_rook.isFirstMove() and self.getSquare(king_start_pos - 1).isEmpty()
            and self.getSquare(king_start_pos - 2).isEmpty() and self.getSquare(king_start_pos - 3).isEmpty()):
            for i in range(1,3):
                if(not self.isSquareSafe(king_start_pos - i,enemy_turn)): return False
            return True
        return False

    def getAllLegalMove(self,team):
        feasible_move = []
        king = self.white_king if team == Team.WHITE else self.black_king
        enemy_turn = Team.BLACK if team == Team.WHITE else Team.WHITE
        for posible_move in self.getAllPossibleMove(team):
            self.makeMove(posible_move)
            if(self.isSquareSafe(king.getPosition(),enemy_turn)):
                feasible_move.append(posible_move)
            self.undoMove()
        
        if (self.canShortCastle(team)):
            feasible_move.append(Move(king, king.getPosition() + 2, MoveType.SHORT_CASTLE))

        if (self.canLongCastle(team)):
            feasible_move.append(Move(king, king.getPosition() - 2, MoveType.LONG_CASTLE))
        return feasible_move
    
    def isEndGameScenario(self):
       return len(self.getAllLegalMove(self.turn)) == 0
    
    def getHash(self):
        return self.hash_code

    def isKingVsKing(self):
        pieces = [sq.getPiece() for sq in self.game_board if not sq.isEmpty()]
        return len(pieces) == 2  # chỉ còn 2 vua

    @staticmethod
    def pretty_print(square):
        if not square.isEmpty():
            piece_str = str(square)  # giả sử Square.__str__ trả về 'P', 'R', ...
            if square.getPiece().getTeam() == Team.BLACK:
                return piece_str.lower()
            else:
                return piece_str
        return str(square)




    def __str__(self):
        builder = []

        for row in range(8):
            builder.append(f"{8 - row} ")  # số hàng

            for col in range(8):
                i = row * 8 + col
                tile_text = Board.pretty_print(self.game_board[i])
                builder.append(f"{tile_text:>3}")

            builder.append("\n")

        builder.append("   a  b  c  d  e  f  g  h\n")
        return "".join(builder)


if __name__ == "__main__":
    # 1. Khởi tạo bàn cờ
    board = Board()
    print("--- Trạng thái bàn cờ ban đầu ---")
    print(board)
    