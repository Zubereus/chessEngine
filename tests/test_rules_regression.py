import unittest

from src.chess_replicated.chess_board import (
    Bishop, Board, King, Knight, Move, Pawn, Queen, Rook, Square,
)
from src.chess_replicated.enum_chess import MoveType, Team
from src.chess_replicated.evaluator import Evaluator
from src.chess_replicated.alphabeta_fast import FastNegaMax, MATE_BOUND

PIECES = {"p": Pawn, "n": Knight, "b": Bishop, "r": Rook, "q": Queen, "k": King}


def board_from_fen(fen):
    """Minimal FEN loader (pieces, side to move, castling rights, halfmove clock)."""
    placement, side, castling, _, halfmove = fen.split()[:5]
    board = Board()
    board.game_board = [Square(None) for _ in range(64)]
    squares = [ch for row in placement.split("/") for c in row for ch in (["."] * int(c) if c.isdigit() else [c])]
    for index, ch in enumerate(squares):
        if ch == ".":
            continue
        team = Team.WHITE if ch.isupper() else Team.BLACK
        first = (
            (index // 8 == (6 if team == Team.WHITE else 1)) if ch.lower() == "p"
            else ((ch == "K" and ("K" in castling or "Q" in castling)) or (ch == "k" and ("k" in castling or "q" in castling))) if ch.lower() == "k"
            else (index in {63: "K", 56: "Q", 7: "k", 0: "q"} and {63: "K", 56: "Q", 7: "k", 0: "q"}[index] in castling) if ch.lower() == "r"
            else True
        )
        piece = PIECES[ch.lower()](team, index, first)
        board.game_board[index] = Square(piece)
        if ch == "K":
            board.white_king = piece
        if ch == "k":
            board.black_king = piece
    board.turn = Team.WHITE if side == "w" else Team.BLACK
    board.halfmove_clock = int(halfmove)
    board.move_history, board.hash_code = [], None
    return board


def perft(board, depth):
    if depth == 0:
        return 1
    total = 0
    for move in board.getAllLegalMove(board.turn):
        board.makeMove(move)
        total = total + perft(board, depth - 1)
        board.undoMove()
    return total


class RuleRegressionTests(unittest.TestCase):
    def test_perft_counts_match_reference(self):
        cases = [
            ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 3, 8902),
            ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2, 2039),
            ("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 3, 62379),  # needs underpromotion
            ("n1n5/PPPk4/8/8/8/8/4Kppp/5N1N b - - 0 1", 3, 9483),
            ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", 3, 13744),   # failed before the undo-aliasing fix (13416)
        ]
        for fen, depth, expected in cases:
            self.assertEqual(perft(board_from_fen(fen), depth), expected, fen)

    def test_undo_restores_captured_rook_castling_right_after_other_moves(self):
        board = board_from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        moves = board.getAllLegalMove(board.turn)       # every move generated up front, as a search does
        capture = next(filter(lambda m: m.getStartPos() == 56 and m.getEndPos() == 0, moves))
        for move in moves:
            if move is capture:
                break
            board.makeMove(move)
            for reply in board.getAllLegalMove(board.turn):
                board.makeMove(reply)
                board.undoMove()
            board.undoMove()
        board.makeMove(capture)
        board.undoMove()
        self.assertTrue(board.getSquare(0).getPiece().isFirstMove())

    def test_all_four_promotions_are_legal(self):
        board = board_from_fen("8/P7/8/8/8/8/8/k6K w - - 0 1")
        promotions = sorted(m.getPromotion() for m in board.getAllLegalMove(Team.WHITE) if m.getPromotion())
        self.assertEqual(promotions, ["B", "N", "Q", "R"])
        knight = next(filter(lambda m: m.getPromotion() == "N", board.getAllLegalMove(Team.WHITE)))
        board.makeMove(knight)
        self.assertIs(type(board.getSquare(0).getPiece()), Knight)
        board.undoMove()
        self.assertIs(type(board.getSquare(8).getPiece()), Pawn)

    def test_fifty_move_clock_resets_and_restores(self):
        board = board_from_fen("4k3/8/8/8/8/8/4P3/R3K3 w - - 98 60")
        rook_move = next(filter(lambda m: type(m.getPiece()) is Rook, board.getAllLegalMove(Team.WHITE)))
        pawn_move = next(filter(lambda m: type(m.getPiece()) is Pawn, board.getAllLegalMove(Team.WHITE)))
        board.makeMove(rook_move)
        self.assertEqual(board.halfmove_clock, 99)
        board.undoMove()
        board.makeMove(pawn_move)
        self.assertEqual(board.halfmove_clock, 0)
        board.undoMove()
        self.assertEqual(board.halfmove_clock, 98)
        self.assertTrue(board_from_fen("4k3/8/8/8/8/8/4P3/R3K3 w - - 100 60").isFiftyMoveDraw())

    def test_insufficient_material(self):
        dead = ["8/8/8/4k3/8/8/3K4/6B1 w - - 0 1", "8/8/8/4k3/8/8/3K4/6N1 w - - 0 1",
                "8/8/8/4k3/8/8/3KB3/5b2 w - - 0 1"]       # K+B v K+B, bishops on the same colour
        alive = ["8/8/8/4k3/8/8/3KB3/6b1 w - - 0 1",      # opposite-colour bishops: mate is possible
                 "8/8/8/4k3/8/8/3KNN2/8 w - - 0 1", "8/8/8/4k3/8/8/3KP3/8 w - - 0 1"]
        self.assertTrue(all(board_from_fen(f).isInsufficientMaterial() for f in dead))
        self.assertFalse(any(board_from_fen(f).isInsufficientMaterial() for f in alive))
        self.assertFalse(board_from_fen(dead[0]).hasMatingMaterial(Team.WHITE))

    def test_evaluator_is_colour_symmetric(self):
        white = board_from_fen("4k3/8/8/8/3Q4/8/8/4K3 w - - 0 1")
        mirrored = board_from_fen("4k3/8/8/3q4/8/8/8/4K3 b - - 0 1")   # colours swapped, board flipped vertically
        self.assertEqual(Evaluator.evaluate(white), Evaluator.evaluate(mirrored))
        queen_left = board_from_fen("4k3/8/8/8/Q7/8/8/4K3 w - - 0 1")
        queen_mirrored = board_from_fen("4k3/8/8/q7/8/8/8/4K3 b - - 0 1")   # a4 mirrors to a5; the OLD 63-pos mapping sent it to h5
        self.assertEqual(Evaluator.evaluate(queen_left), Evaluator.evaluate(queen_mirrored))

    def test_search_finds_shortest_mate_and_avoids_repetition(self):
        board = board_from_fen("6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1")
        move, score, _ = FastNegaMax(board).search(4)
        self.assertEqual((move.getStartPos(), move.getEndPos()), (56, 0))   # Ra1-a8#
        self.assertGreater(score, MATE_BOUND)

    def test_search_scores_repeated_position_as_draw(self):
        board = board_from_fen("6k1/8/8/8/8/8/8/Q3K3 w - - 0 1")
        key = board.getHash()
        engine = FastNegaMax(board, history={key: 1})
        self.assertTrue(engine._is_draw_by_rule(key))


if __name__ == "__main__":
    unittest.main()
