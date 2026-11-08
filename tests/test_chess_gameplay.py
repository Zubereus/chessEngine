import os
import random
import unittest
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame

from src.chess_replicated.chess_board import (
    Bishop,
    Board,
    King,
    Knight,
    Pawn,
    Queen,
    Rook,
)
from src.chess_replicated.enum_chess import Team
from src.chess_replicated.mouse_repeat import MouseHoldRepeater
from src.chess_replicated.ui import UI
from src.menu.menu import get_config
from src.algorithm.MCTS_algo.mcts_evalutor import Evaluator, simple_evaluate
from src.chess_replicated.display import is_fullscreen, toggle_fullscreen


class ChessGameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def make_ui(
        self, algorithm="alphabeta", clock_minutes=10, game_mode="human vs ai"
    ):
        return UI(
            Board(),
            algorithm,
            depth=2,
            mcts_iterations=100,
            game_mode=game_mode,
            clock_minutes=clock_minutes,
        )

    def test_mouse_hold_repeater_delay_interval_and_stop(self):
        repeater = MouseHoldRepeater(initial_delay=350, interval=75)
        repeater.start(1000)

        self.assertEqual(repeater.update(1349, True), 0)
        self.assertEqual(repeater.update(1350, True), 1)
        self.assertEqual(repeater.update(1500, True), 2)
        self.assertEqual(repeater.update(1501, False), 0)
        self.assertEqual(repeater.update(2000, True), 0)

        repeater.start(2000)
        self.assertEqual(repeater.update(2350, True), 1)
        self.assertEqual(repeater.update(2351, False), 0)

    def test_human_move_and_alternating_alpha_beta_turn(self):
        ui = self.make_ui()
        now = pygame.time.get_ticks()
        ui.clock_tick_at = now

        self.assertFalse(ui._handle_human_click(52, now))
        self.assertEqual(ui.selected_square, 52)
        self.assertTrue(any(move.getEndPos() == 36 for move in ui.selected_moves))
        self.assertTrue(ui._handle_human_click(36, now + 1000))
        self.assertEqual(ui.board.turn, Team.BLACK)
        self.assertEqual(ui.move_log_rows[0]["white"], "HUMAN: e2-e4")
        self.assertIsNone(ui.move_log_rows[0]["black"])
        self.assertLessEqual(ui.clock_remaining[Team.WHITE], 599.01)
        self.assertTrue(ui.run_ai_once())
        self.assertEqual(ui.board.turn, Team.WHITE)
        self.assertIsNotNone(ui.move_log_rows[0]["black"])
        self.assertTrue(
            ui.move_log_rows[0]["black"].startswith("ALPHA-BETA: ")
        )

    def test_gameplay_layout_places_controls_beside_larger_board(self):
        ui = self.make_ui()
        ui.draw_controls()

        self.assertEqual(ui.board_pixel_width, 640)
        self.assertEqual(ui.window_size, (1360, 760))
        self.assertGreaterEqual(ui.btn_run_ai.left, ui.control_panel_x)
        self.assertGreaterEqual(ui.btn_up2.left, ui.control_panel_x)
        self.assertGreater(ui.btn_run_ai.top, 400)
        self.assertLessEqual(ui.btn_menu.right, ui.window_width - 30)
        self.assertGreater(ui.move_log_viewport.height, 0)

    def test_move_log_keeps_all_moves_and_clamps_scroll_position(self):
        ui = self.make_ui(
            algorithm="alphabeta vs mcts",
            game_mode="ai vs ai",
        )
        move = ui.board.getAllLegalMove(Team.WHITE)[0]
        for _ in range(8):
            ui._record_move(move, Team.WHITE)
            ui._record_move(move, Team.BLACK)

        self.assertEqual(len(ui.move_log_rows), 8)
        self.assertTrue(ui.move_log_rows[0]["white"].startswith("ALPHA-BETA: "))
        self.assertTrue(ui.move_log_rows[0]["black"].startswith("MCTS: "))

        ui.move_log_scroll = 100
        ui.draw_controls()
        self.assertEqual(
            ui.move_log_scroll,
            max(0, len(ui.move_log_rows) - ui.move_log_visible_rows),
        )

    def test_mcts_reply_and_timeout(self):
        ui = self.make_ui(algorithm="mcts", clock_minutes=1)
        now = pygame.time.get_ticks()
        ui.clock_tick_at = now
        ui._handle_human_click(52, now)
        self.assertTrue(ui._handle_human_click(36, now + 250))
        self.assertTrue(ui.run_ai_once())
        self.assertEqual(ui.board.turn, Team.WHITE)

        ui.clock_remaining[Team.WHITE] = 0.5
        ui.clock_tick_at = 1000
        self.assertFalse(ui._update_clock(2000))
        self.assertTrue(ui.game_over)
        self.assertIn("BLACK wins", ui.status_text)

    def test_mcts_default_move_is_legal_and_does_not_mutate_board(self):
        from src.algorithm.MCTS_algo.MCTS import mcts_search

        board = Board()
        original_hash = board.getHash()
        move = mcts_search(board, Team.WHITE, iterations=100)
        self.assertIsNotNone(move)
        self.assertEqual(board.getHash(), original_hash)
        self.assertTrue(
            any(
                (candidate.getStartPos(), candidate.getEndPos(), candidate.getType())
                == (move.getStartPos(), move.getEndPos(), move.getType())
                for candidate in board.getAllLegalMove(Team.WHITE)
            )
        )

    def test_mcts_scores_mate_on_final_rollout_ply_as_a_win(self):
        from src.algorithm.MCTS_algo.MCTS import _simulate_random_playout

        board = Board()
        for index in range(64):
            board.getSquare(index).setPiece(None)
        white_king = King(Team.WHITE, 18)
        black_king = King(Team.BLACK, 0)
        queen = Queen(Team.WHITE, 17)
        board.getSquare(18).setPiece(white_king)
        board.getSquare(0).setPiece(black_king)
        board.getSquare(17).setPiece(queen)
        board.white_king = white_king
        board.black_king = black_king
        board.turn = Team.WHITE
        board.move_history = []
        board.hash_code = board.zobrist.getFullHash(board)
        mating_move = next(
            move
            for move in board.getAllLegalMove(Team.WHITE)
            if move.getStartPos() == 17 and move.getEndPos() == 9
        )
        original_hash = board.getHash()

        with patch(
            "src.algorithm.MCTS_algo.MCTS.random.choice",
            return_value=mating_move,
        ), patch("src.algorithm.MCTS_algo.MCTS.random.random", return_value=0.99):
            reward = _simulate_random_playout(
                board,
                Team.WHITE,
                Team.WHITE,
                rollout_depth=1,
            )

        self.assertEqual(reward, 1.0)
        self.assertEqual(board.getHash(), original_hash)

    def test_hash_stays_canonical_during_make_and_undo(self):
        board = Board()
        random.seed(3)

        for _ in range(30):
            self.assertEqual(board.getHash(), board.zobrist.getFullHash(board))
            legal_moves = board.getAllLegalMove(board.turn)
            if not legal_moves:
                break
            board.makeMove(random.choice(legal_moves))

        while board.move_history:
            self.assertEqual(board.getHash(), board.zobrist.getFullHash(board))
            board.undoMove()
        self.assertEqual(board.getHash(), board.zobrist.getFullHash(board))

    def test_square_safety_handles_pieces_blockers_and_castling(self):
        board = Board()

        for index in range(64):
            board.getSquare(index).setPiece(None)

        board.getSquare(0).setPiece(Rook(Team.BLACK, 0))
        self.assertFalse(board.isSquareSafe(7, Team.BLACK))
        board.getSquare(3).setPiece(Pawn(Team.WHITE, 3))
        self.assertTrue(board.isSquareSafe(7, Team.BLACK))

        for index in range(64):
            board.getSquare(index).setPiece(None)
        board.getSquare(9).setPiece(Bishop(Team.BLACK, 9))
        self.assertFalse(board.isSquareSafe(0, Team.BLACK))
        board.getSquare(11).setPiece(Knight(Team.BLACK, 11))
        self.assertFalse(board.isSquareSafe(1, Team.BLACK))
        board.getSquare(27).setPiece(Pawn(Team.BLACK, 27))
        self.assertFalse(board.isSquareSafe(36, Team.BLACK))
        board.getSquare(53).setPiece(King(Team.BLACK, 53))
        self.assertFalse(board.isSquareSafe(60, Team.BLACK))

        for index in range(64):
            board.getSquare(index).setPiece(None)
        board.getSquare(60).setPiece(King(Team.WHITE, 60))
        board.getSquare(63).setPiece(Rook(Team.WHITE, 63))
        board.getSquare(52).setPiece(Bishop(Team.BLACK, 52))
        self.assertFalse(board.canShortCastle(Team.WHITE))

    def test_menu_returns_selected_engine_and_clock(self):
        events = [
            pygame.event.Event(
                pygame.KEYDOWN, {"key": pygame.K_F11, "mod": 0}
            ),
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, {"pos": (495, 145), "button": 1}
            ),
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, {"pos": (480, 295), "button": 1}
            ),
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, {"pos": (480, 755), "button": 1}
            ),
        ]
        with patch("pygame.event.get", return_value=events):
            _, algorithm, _, _, game_mode, clock_minutes = get_config()

        self.assertEqual(algorithm, "mcts")
        self.assertEqual(game_mode, "human vs ai")
        self.assertEqual(clock_minutes, 11)
        self.assertTrue(is_fullscreen())

        ui = UI(Board(), algorithm, 2, 100, game_mode, clock_minutes)
        self.assertEqual(ui.screen.get_size(), ui.window_size)
        toggle_fullscreen((960, 800))
        self.assertFalse(is_fullscreen())

        with patch(
            "pygame.event.get",
            return_value=[
                pygame.event.Event(
                    pygame.KEYDOWN, {"key": pygame.K_F11, "mod": 0}
                ),
                pygame.event.Event(pygame.QUIT),
            ],
        ):
            self.assertEqual(ui.run(), "quit")
        self.assertTrue(is_fullscreen())
        toggle_fullscreen(ui.window_size)
        self.assertFalse(is_fullscreen())

    def test_ai_vs_ai_alpha_beta_button_shows_selected_color(self):
        events = [
            [
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, {"pos": (495, 95), "button": 1}
                ),
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, {"pos": (325, 145), "button": 1}
                ),
            ],
            [
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, {"pos": (480, 755), "button": 1}
                ),
            ],
        ]
        original_draw_rect = pygame.draw.rect
        alpha_beta_button_colors = []

        def capture_draw_rect(surface, color, rect, *args, **kwargs):
            if rect == pygame.Rect(250, 125, 150, 40):
                alpha_beta_button_colors.append(color)
            return original_draw_rect(surface, color, rect, *args, **kwargs)

        with patch("pygame.event.get", side_effect=events), patch(
            "pygame.draw.rect", side_effect=capture_draw_rect
        ):
            _, algorithm, _, _, game_mode, _ = get_config()

        self.assertEqual(algorithm, "alphabeta vs alphabeta")
        self.assertEqual(game_mode, "ai vs ai")
        self.assertEqual(alpha_beta_button_colors[-1], (0, 120, 215))

    def test_ai_vs_ai_mcts_button_shows_selected_color(self):
        events = [
            [
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, {"pos": (495, 95), "button": 1}
                ),
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, {"pos": (495, 145), "button": 1}
                ),
            ],
            [
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, {"pos": (480, 755), "button": 1}
                ),
            ],
        ]
        original_draw_rect = pygame.draw.rect
        mcts_button_colors = []

        def capture_draw_rect(surface, color, rect, *args, **kwargs):
            if rect == pygame.Rect(420, 125, 150, 40):
                mcts_button_colors.append(color)
            return original_draw_rect(surface, color, rect, *args, **kwargs)

        with patch("pygame.event.get", side_effect=events), patch(
            "pygame.draw.rect", side_effect=capture_draw_rect
        ):
            _, algorithm, _, _, game_mode, _ = get_config()

        self.assertEqual(algorithm, "mcts vs mcts")
        self.assertEqual(game_mode, "ai vs ai")
        self.assertEqual(mcts_button_colors[-1], (150, 50, 150))

    def test_evaluator_handles_material_draws_and_position_features(self):
        def make_eval_board(pieces):
            board = Board()
            for index in range(64):
                board.getSquare(index).setPiece(None)
            for piece, position in pieces:
                piece.setPosition(position)
                board.getSquare(position).setPiece(piece)
            board.white_king = next(
                piece
                for piece, _ in pieces
                if piece.getTeam() == Team.WHITE and piece.getPieceType() == "K"
            )
            board.black_king = next(
                piece
                for piece, _ in pieces
                if piece.getTeam() == Team.BLACK and piece.getPieceType() == "K"
            )
            return board

        kings_only = make_eval_board(
            [(King(Team.WHITE, 60), 60), (King(Team.BLACK, 4), 4)]
        )
        self.assertEqual(simple_evaluate(kings_only, Team.WHITE), 0)
        self.assertEqual(
            Evaluator.evaluate_dynamic(kings_only, "white"),
            0,
        )

        bishop_vs_king = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (Bishop(Team.WHITE, 26), 26),
                (King(Team.BLACK, 4), 4),
            ]
        )
        self.assertEqual(simple_evaluate(bishop_vs_king, Team.WHITE), 0)
        self.assertEqual(Evaluator.evaluate_dynamic(bishop_vs_king, "white"), 0)
        self.assertTrue(
            Evaluator._is_insufficient_material(
                Evaluator._collect_team_pieces(bishop_vs_king, Team.WHITE),
                Evaluator._collect_team_pieces(bishop_vs_king, Team.BLACK),
            )
        )

        passed_pawn_board = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (King(Team.BLACK, 4), 4),
                (Pawn(Team.WHITE, 35), 35),
                (Pawn(Team.BLACK, 8), 8),
            ]
        )
        blocked_pawn_board = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (King(Team.BLACK, 4), 4),
                (Pawn(Team.WHITE, 35), 35),
                (Pawn(Team.BLACK, 11), 11),
            ]
        )
        self.assertGreater(
            simple_evaluate(passed_pawn_board, Team.WHITE),
            simple_evaluate(blocked_pawn_board, Team.WHITE),
        )

        doubled_pawns = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (King(Team.BLACK, 4), 4),
                (Pawn(Team.WHITE, 27), 27),
                (Pawn(Team.WHITE, 35), 35),
            ]
        )
        connected_pawns = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (King(Team.BLACK, 4), 4),
                (Pawn(Team.WHITE, 27), 27),
                (Pawn(Team.WHITE, 36), 36),
            ]
        )
        self.assertEqual(
            simple_evaluate(connected_pawns, Team.WHITE)
            - simple_evaluate(doubled_pawns, Team.WHITE),
            32,
        )

        open_rook_file = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (Rook(Team.WHITE, 28), 28),
                (King(Team.BLACK, 4), 4),
                (Pawn(Team.BLACK, 8), 8),
            ]
        )
        semi_open_rook_file = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (Rook(Team.WHITE, 28), 28),
                (King(Team.BLACK, 4), 4),
                (Pawn(Team.BLACK, 12), 12),
            ]
        )
        self.assertGreater(
            simple_evaluate(open_rook_file, Team.WHITE),
            simple_evaluate(semi_open_rook_file, Team.WHITE),
        )

        bishop_pair = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (Bishop(Team.WHITE, 26), 26),
                (Bishop(Team.WHITE, 29), 29),
                (King(Team.BLACK, 4), 4),
            ]
        )
        single_bishop = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (Bishop(Team.WHITE, 26), 26),
                (King(Team.BLACK, 4), 4),
            ]
        )
        self.assertGreater(
            simple_evaluate(bishop_pair, Team.WHITE),
            simple_evaluate(single_bishop, Team.WHITE),
        )

        rook_vs_king = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (Rook(Team.WHITE, 56), 56),
                (King(Team.BLACK, 4), 4),
            ]
        )
        both_sides_have_rooks = make_eval_board(
            [
                (King(Team.WHITE, 60), 60),
                (Rook(Team.WHITE, 56), 56),
                (King(Team.BLACK, 4), 4),
                (Rook(Team.BLACK, 0), 0),
            ]
        )
        self.assertTrue(
            Evaluator._is_rook_endgame(
                Evaluator._collect_team_pieces(rook_vs_king, Team.WHITE),
                Evaluator._collect_team_pieces(rook_vs_king, Team.BLACK),
            )
        )
        self.assertFalse(
            Evaluator._is_rook_endgame(
                Evaluator._collect_team_pieces(
                    both_sides_have_rooks, Team.WHITE
                ),
                Evaluator._collect_team_pieces(
                    both_sides_have_rooks, Team.BLACK
                ),
            )
        )


if __name__ == "__main__":
    unittest.main()
