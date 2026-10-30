from .chess_board import Move, Board
from .evaluator import Evaluator
from .hashentry import *

class SortingHat:
    @staticmethod
    def sortMove(moves, board):
        scored = []
        for move in moves:
            board.makeMove(move)
            score = Evaluator.evaluate(board)
            board.undoMove()
            scored.append((score, move))


        scored.sort(key=lambda x: x[0], reverse=True)
        return [move for _, move in scored]


class NegaMaxAlphaBetaTransposition:
    def __init__(self, board, max_depth, transposition_table, on_complete=None):
        self.board               = board
        self.max_depth           = max_depth
        self.transposition_table = transposition_table
        self.node_count          = 0

    def negamaxRoot(self, alpha, beta):
        best_move  = None
        best_score = alpha                          # ← theo dõi điểm tốt nhất
        legal_moves = SortingHat.sortMove(self.board.getAllLegalMove(self.board.turn), self.board)

        for move in legal_moves:
            self.board.makeMove(move)
            score = -self.negamaxFunc(self.board, self.max_depth - 1, -beta, -alpha)
            self.board.undoMove()

            if score > alpha:
                alpha      = score
                best_score = score
                best_move  = move

        return best_move, best_score               # ← trả về tuple

    def negamaxFunc(self, board, depth, alpha, beta):
        self.node_count += 1
        alpha_orig = alpha
        zobrist_key = board.getHash()
        entry = self.transposition_table.get(zobrist_key)
        if entry is not None and entry.getDepth() >= depth:
            if entry.getType() == EntryType.EXACT:
                return entry.getScore()
            elif entry.getType() == EntryType.LOWER_BOUND:
                alpha = max(alpha, entry.getScore())
            elif entry.getType() == EntryType.UPPER_BOUND:
                beta = min(beta, entry.getScore())
            if alpha >= beta:
                return entry.getScore()
        if depth == 0:
            return Evaluator.evaluate(board)
        legal_moves = board.getAllLegalMove(board.turn)
        if not legal_moves:
            return Evaluator.evaluateEndGame(board)
        
        best_score = -(10**9) # Khởi tạo giá trị âm vô cực
        for move in legal_moves:
            board.makeMove(move)
            # Lấy điểm của nước đi này
            current_score = -self.negamaxFunc(board, depth - 1, -beta, -alpha)
            board.undoMove()

            # Cập nhật điểm tốt nhất tìm được (Max)
            best_score = max(best_score, current_score)
            
            # Cập nhật alpha và cắt tỉa
            alpha = max(alpha, current_score)
            if alpha >= beta:
                break
                
        # Lưu vào Transposition Table dựa trên best_score
        if best_score <= alpha_orig:
            entry_type = EntryType.UPPER_BOUND
        elif best_score >= beta:
            entry_type = EntryType.LOWER_BOUND
        else:
            entry_type = EntryType.EXACT

        self.transposition_table[zobrist_key] = HashEntry(best_score, depth, entry_type)
        return best_score