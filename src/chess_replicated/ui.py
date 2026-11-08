import pygame
from src.setting import *
from src.chess_replicated.chess_board import Move
from src.chess_replicated.enum_chess import Team
import sys
import threading
from copy import deepcopy
from src.chess_replicated.ai_thinking import AIThinkTank
from src.chess_replicated.display import create_display, toggle_fullscreen
from src.chess_replicated.mouse_repeat import MouseHoldRepeater
from src.algorithm.MCTS_algo.MCTS import mcts_search
import os

# Longest the alpha-beta AI may think about one move (it keeps the best move of
# the deepest depth it finished). Raise it for stronger, slower play.
AI_TIME_LIMIT_SECONDS = 10.0


class UI:
    def __init__(
        self,
        board,
        algorithm,
        depth,
        mcts_iterations,
        game_mode="ai vs ai",
        clock_minutes=10,
    ):
        pygame.init()
        self.board = board
        self.board_history = {}
        self.depth = depth
        self.mcts_iterations = mcts_iterations
        self.algorithm = algorithm
        self.game_mode = game_mode
        self.human_color = Team.WHITE
        if game_mode == "human vs ai":
            self.white_ai = "human"
            self.black_ai = algorithm
        elif algorithm == "alphabeta vs mcts":
            self.white_ai = "alphabeta"
            self.black_ai = "mcts"
        elif algorithm == "alphabeta vs alphabeta":
            self.white_ai = "alphabeta"
            self.black_ai = "alphabeta"
        elif algorithm == "mcts vs mcts":
            self.white_ai = "mcts"
            self.black_ai = "mcts"
        else:
            self.white_ai = "mcts"
            self.black_ai = "alphabeta"
        self.clock_minutes = max(1, int(clock_minutes))
        self.clock_remaining = {
            Team.WHITE: float(self.clock_minutes * 60),
            Team.BLACK: float(self.clock_minutes * 60),
        }
        self.clock_tick_at = pygame.time.get_ticks()
        self.game_over = False
        self.selected_square = None
        self.selected_moves = []
        # ===== BOARD SIZE =====
        BOARD_PIXEL_SIZE = 640
        self.cell = BOARD_PIXEL_SIZE // 8
        self.board_pixel_width = self.cell * 8
        self.board_origin_x = 20
        self.board_origin_y = 0

        # ===== WINDOW =====
        self.window_width = 1360
        self.window_height = 760
        self.control_panel_x = 700

        self.window_size = (self.window_width, self.window_height)
        self.screen = create_display(self.window_size)

        pygame.display.set_caption(f"Chess AI Visualizer " + algorithm.upper())
        self.square_imgs = {
        "dark": pygame.transform.scale(
            pygame.image.load(os.path.join(IMG_DIR, "square brown dark.png")),
            (self.cell, self.cell)
        ),
        "light": pygame.transform.scale(
            pygame.image.load(os.path.join(IMG_DIR, "square brown light.png")),
            (self.cell, self.cell)
        ),
        }
        self.font = pygame.font.SysFont("Arial", 18, bold=True)
        self.btn_up1 = pygame.Rect(0, 0, 0, 0)
        self.btn_down1 = pygame.Rect(0, 0, 0, 0)
        self.btn_up2 = pygame.Rect(0, 0, 0, 0)
        self.btn_down2 = pygame.Rect(0, 0, 0, 0)    
        self.btn_run_ai = pygame.Rect(0, 0, 0, 0)
        self.btn_menu = pygame.Rect(0, 0, 0, 0)
        self.btn_autoplay = pygame.Rect(0, 0, 0, 0)
        self.iteration_repeater = MouseHoldRepeater()
        self.status_text = ""
        self.move_log_rows = []
        self.move_log_scroll = 0
        self.move_log_viewport = pygame.Rect(0, 0, 0, 0)
        self.move_log_visible_rows = 1

        # Load images
        self.images = self._load_assets()
        # Mapping new alpha-beta to UI
        self.alphabeta = AIThinkTank(self.board)
        # AI work runs in a background thread so the window keeps responding.
        self.ai_thread = None
        self.ai_job = None
        sys.setswitchinterval(0.001)   # let the drawing thread get the CPU often
        self.autoplay = False  # Trạng thái tự động chơi
        self.move_delay = 600  # Khoảng nghỉ giữa các nước đi (miliseconds)
        self.last_move_time = pygame.time.get_ticks()
        self.frame_clock = pygame.time.Clock()

    def _load_assets(self):
        imgs = {}
        piece_symbol_map = {
            "pawn": "P",
            "rook": "R",
            "knight": "N",
            "bishop": "B",
            "queen": "Q",
            "king": "K"
        }

        for color in ["white", "black"]:
            prefix = "w" if color == "white" else "b"

            for p in PIECE_TYPES:
                symbol = piece_symbol_map[p]
                key = f"{symbol}-{color}"
                filename = f"{prefix}_{p}.png"
                path = os.path.join(IMG_DIR, filename)

                if os.path.exists(path):
                    img = pygame.transform.scale(pygame.image.load(path),(self.cell, self.cell))
                    imgs[key] = img
                else:
                    surf = pygame.Surface((self.cell, self.cell))
                    surf.fill((255, 0, 0))  # debug missing
                    imgs[key] = surf

        return imgs

    def draw_controls(self):
        panel_x = self.control_panel_x
        panel_width = self.window_width - panel_x - 30
        mode_label = (
            "HUMAN vs AI"
            if self.game_mode == "human vs ai"
            else self.algorithm.upper()
        )
        title_font = pygame.font.SysFont("Arial", 24, bold=True)
        section_font = pygame.font.SysFont("Arial", 16, bold=True)
        self.screen.blit(
            title_font.render(mode_label, True, (255, 255, 255)),
            (panel_x, 30),
        )
        self.screen.blit(
            self.font.render(
                "YOU PLAY WHITE" if self.game_mode == "human vs ai" else "AI vs AI",
                True,
                (190, 190, 190),
            ),
            (panel_x, 64),
        )

        self.screen.blit(
            section_font.render("CLOCK", True, (150, 150, 150)),
            (panel_x, 105),
        )
        self.screen.blit(
            section_font.render("SEARCH SETTINGS", True, (150, 150, 150)),
            (panel_x, 285),
        )

        self.screen.blit(
            self.font.render(f"ALPHA-BETA DEPTH   {self.depth}", True, (255, 255, 255)),
            (panel_x, 322),
        )
        self.btn_up1 = pygame.Rect(panel_x + panel_width - 90, 315, 35, 35)
        self.btn_down1 = pygame.Rect(panel_x + panel_width - 45, 315, 35, 35)
        self.screen.blit(
            self.font.render(
                f"MCTS ITERATIONS   {self.mcts_iterations}",
                True,
                (255, 255, 255),
            ),
            (panel_x, 382),
        )
        self.btn_up2 = pygame.Rect(panel_x + panel_width - 90, 375, 35, 35)
        self.btn_down2 = pygame.Rect(panel_x + panel_width - 45, 375, 35, 35)
        for button, symbol, color in (
            (self.btn_up1, "+", (50, 150, 50)),
            (self.btn_down1, "-", (150, 50, 50)),
            (self.btn_up2, "+", (50, 150, 50)),
            (self.btn_down2, "-", (150, 50, 50)),
        ):
            pygame.draw.rect(self.screen, color, button, border_radius=5)
            label = self.font.render(symbol, True, (255, 255, 255))
            self.screen.blit(label, label.get_rect(center=button.center))

        self.btn_run_ai = pygame.Rect(panel_x, 465, 165, 42)
        ai_turn = self.game_mode != "human vs ai" or self.board.turn != self.human_color
        run_color = (0, 122, 204) if ai_turn and not self.game_over else (70, 70, 70)
        pygame.draw.rect(self.screen, run_color, self.btn_run_ai, border_radius=6)
        run_label = self.font.render("RUN AI", True, (255, 255, 255))
        self.screen.blit(run_label, run_label.get_rect(center=self.btn_run_ai.center))

        self.btn_autoplay = pygame.Rect(panel_x + 180, 465, 155, 42)
        auto_color = (0, 160, 0) if self.autoplay else (100, 70, 70)
        pygame.draw.rect(self.screen, auto_color, self.btn_autoplay, border_radius=6)
        auto_label = self.font.render(
            "AUTO: ON" if self.autoplay else "AUTO: OFF",
            True,
            (255, 255, 255),
        )
        self.screen.blit(auto_label, auto_label.get_rect(center=self.btn_autoplay.center))

        self.btn_menu = pygame.Rect(panel_x + 350, 465, panel_width - 350, 42)
        pygame.draw.rect(self.screen, (90, 90, 90), self.btn_menu, border_radius=6)
        menu_label = self.font.render("RETURN TO MENU", True, (255, 255, 255))
        self.screen.blit(menu_label, menu_label.get_rect(center=self.btn_menu.center))

        for index, color in enumerate((Team.WHITE, Team.BLACK)):
            clock_rect = pygame.Rect(panel_x, 130 + index * 75, 280, 58)
            is_active = self.board.turn == color and not self.game_over
            border = (255, 220, 70) if is_active else (100, 100, 100)
            pygame.draw.rect(self.screen, (30, 30, 30), clock_rect, border_radius=6)
            pygame.draw.rect(
                self.screen, border, clock_rect, width=3, border_radius=6
            )
            color_name = "WHITE" if color == Team.WHITE else "BLACK"
            seconds = max(0, int(self.clock_remaining[color]))
            clock_text = f"{seconds // 60:02d}:{seconds % 60:02d}"
            name_surface = self.font.render(color_name, True, (220, 220, 220))
            time_surface = pygame.font.SysFont("Arial", 27, bold=True).render(
                clock_text, True, (255, 255, 255)
            )
            self.screen.blit(name_surface, (clock_rect.x + 10, clock_rect.y + 17))
            self.screen.blit(
                time_surface,
                (clock_rect.right - time_surface.get_width() - 10, clock_rect.y + 12),
            )

        self.screen.blit(
            section_font.render("STATUS", True, (150, 150, 150)),
            (panel_x, 520),
        )
        if self.status_text:
            status_font = pygame.font.SysFont("Arial", 16, bold=True)
            status_text = self.status_text
            while status_text and status_font.size(status_text)[0] > panel_width:
                status_text = status_text[:-4] + "..." if len(status_text) > 4 else ""
            self.screen.blit(
                status_font.render(status_text, True, (220, 220, 220)),
                (panel_x, 543),
            )

        self._draw_move_log(panel_x, panel_width, section_font)
        fullscreen_hint = pygame.font.SysFont("Arial", 15, bold=True).render(
            "F11: FULLSCREEN", True, (150, 150, 150)
        )
        self.screen.blit(
            fullscreen_hint,
            fullscreen_hint.get_rect(topright=(self.window_width - 24, 20)),
        )

    def _player_name(self, color):
        player = self.white_ai if color == Team.WHITE else self.black_ai
        return {
            "human": "HUMAN",
            "alphabeta": "ALPHA-BETA",
            "mcts": "MCTS",
        }[player]

    def _draw_move_log(self, panel_x, panel_width, section_font):
        title_font = pygame.font.SysFont("Arial", 16, bold=True)
        header_font = pygame.font.SysFont("Arial", 13, bold=True)
        entry_font = pygame.font.SysFont("Arial", 14, bold=True)
        title_y = 575
        header_y = 600
        header_height = 24
        row_y = header_y + header_height
        row_height = 22
        self.move_log_viewport = pygame.Rect(
            panel_x,
            row_y,
            panel_width,
            self.window_height - row_y - 20,
        )
        self.move_log_visible_rows = max(
            1, self.move_log_viewport.height // row_height
        )
        max_scroll = max(0, len(self.move_log_rows) - self.move_log_visible_rows)
        self.move_log_scroll = min(self.move_log_scroll, max_scroll)
        start = max_scroll - self.move_log_scroll
        end = min(start + self.move_log_visible_rows, len(self.move_log_rows))
        column_width = panel_width // 2

        self.screen.blit(
            title_font.render("MOVE HISTORY", True, (255, 255, 255)),
            (panel_x, title_y),
        )
        self.screen.blit(
            section_font.render("SCROLL TO VIEW OLDER MOVES", True, (140, 140, 140)),
            (panel_x + 155, title_y + 2),
        )

        white_header = pygame.Rect(panel_x, header_y, column_width, header_height)
        black_header = pygame.Rect(
            panel_x + column_width,
            header_y,
            panel_width - column_width,
            header_height,
        )
        pygame.draw.rect(self.screen, (220, 220, 220), white_header)
        pygame.draw.rect(self.screen, (55, 55, 55), black_header)
        pygame.draw.rect(self.screen, (120, 120, 120), white_header, width=1)
        pygame.draw.rect(self.screen, (120, 120, 120), black_header, width=1)
        for header, color_name, text_color in (
            (white_header, "WHITE", (25, 25, 25)),
            (black_header, "BLACK", (245, 245, 245)),
        ):
            player_name = self._player_name(
                Team.WHITE if color_name == "WHITE" else Team.BLACK
            )
            header_text = header_font.render(
                f"{color_name} - {player_name}", True, text_color
            )
            self.screen.blit(
                header_text,
                header_text.get_rect(center=header.center),
            )

        previous_clip = self.screen.get_clip()
        self.screen.set_clip(self.move_log_viewport)
        for visible_index, row in enumerate(self.move_log_rows[start:end]):
            y = row_y + visible_index * row_height
            white_cell = pygame.Rect(panel_x, y, column_width, row_height)
            black_cell = pygame.Rect(
                panel_x + column_width,
                y,
                panel_width - column_width,
                row_height,
            )
            background = (236, 236, 236) if visible_index % 2 == 0 else (215, 215, 215)
            pygame.draw.rect(self.screen, background, white_cell)
            pygame.draw.rect(
                self.screen,
                (45, 45, 45) if visible_index % 2 == 0 else (62, 62, 62),
                black_cell,
            )
            pygame.draw.rect(self.screen, (125, 125, 125), white_cell, width=1)
            pygame.draw.rect(self.screen, (100, 100, 100), black_cell, width=1)
            for cell, move_text, text_color in (
                (white_cell, row["white"], (25, 25, 25)),
                (black_cell, row["black"], (245, 245, 245)),
            ):
                if move_text is None:
                    continue
                rendered = entry_font.render(move_text, True, text_color)
                self.screen.blit(rendered, (cell.x + 8, cell.y + 3))
        self.screen.set_clip(previous_clip)

    # ===== DRAW BOARD =====
    def draw_board(self):
        font = pygame.font.SysFont("Arial", 18, bold=True)
        for r in range(8):
            for c in range(8):
                is_dark = (r + c) % 2 == 1
                square = self.square_imgs["dark"] if is_dark else self.square_imgs["light"]
                #Take object from Square class 
                square_obj = self.board.getSquare(r*8 + c)
                piece = square_obj.getPiece()
                pos = (
                    self.board_origin_x + c * self.cell,
                    self.board_origin_y + r * self.cell,
                )
                self.screen.blit(square,pos)
                board_index = r * 8 + c
                if self.selected_square == board_index:
                    pygame.draw.rect(
                        self.screen,
                        (246, 246, 105),
                        (*pos, self.cell, self.cell),
                        width=5,
                    )
                elif any(move.getEndPos() == board_index for move in self.selected_moves):
                    pygame.draw.circle(
                        self.screen,
                        (35, 90, 45),
                        (pos[0] + self.cell // 2, pos[1] + self.cell // 2),
                        9,
                    )

                if piece:
                    # Mapping: piece.piece_type (vd: 'K'), piece.color (vd: 'white')
                    key = f"{piece.piece_type}-{piece.team.lower()}"
                    if key in self.images:
                        self.screen.blit(self.images[key], pos)

                if c == 0:
                    # Cờ vua thực tế đếm từ dưới lên (hàng r=0 là 8, r=7 là 1)
                    label_text = str(8 - r) 
                    label_surf = font.render(label_text, True, (255, 255, 255)) # Màu trắng
                    # Đặt bên trái ô cờ (cách lề 5px)
                    self.screen.blit(
                        label_surf,
                        (
                            self.board_origin_x - 15,
                            self.board_origin_y + r * self.cell + self.cell // 3,
                        ),
                    )

                # 4. Vẽ ký hiệu Cột (a-h) - Chỉ vẽ ở hàng cuối cùng (r == 7)
                if r == 7:
                    label_text = chr(ord('A') + c)
                    label_surf = font.render(label_text, True, (255, 255, 255))
                    # Đặt phía dưới ô cờ
                    text_pos = (
                        self.board_origin_x + c * self.cell + self.cell // 2 - 5,
                        self.board_origin_y + (r + 1) * self.cell + 5,
                    )
                    self.screen.blit(label_surf, text_pos)

    def pos_to_notation(self, pos):
        row = pos // 8
        col = pos % 8
        file = chr(ord('a') + col)  # Chuyển cột thành ký tự a-h
        rank = str(8 - row)           # Chuyển hàng thành số 1-8 (đếm từ dưới lên)
        return f"{file}{rank}"

    def _update_clock(self, now=None):
        if self.game_over:
            return False
        now = pygame.time.get_ticks() if now is None else now
        elapsed = max(0, now - self.clock_tick_at) / 1000
        color = self.board.turn
        self.clock_remaining[color] = max(0.0, self.clock_remaining[color] - elapsed)
        self.clock_tick_at = now
        if self.clock_remaining[color] <= 0:
            winner = "BLACK" if color == Team.WHITE else "WHITE"
            if self.board.hasMatingMaterial(winner):
                self.status_text = f"TIME: {color} ran out; {winner} wins."
            else:                                   # FIDE 6.9: flag falls but the opponent cannot mate
                self.status_text = f"TIME: {color} ran out, but {winner} cannot checkmate: draw."
            self.game_over = True
            self.autoplay = False
            return False
        return True

    def _record_position(self):
        position_hash = self.board.getHash()
        self.board_history[position_hash] = self.board_history.get(position_hash, 0) + 1

    def _record_move(self, move, color):
        move_text = (
            f"{self._player_name(color)}: "
            f"{self.pos_to_notation(move.getStartPos())}-"
            f"{self.pos_to_notation(move.getEndPos())}"
        )
        if color == Team.WHITE:
            row = {"white": move_text, "black": None}
            self.move_log_rows.append(row)
        elif self.move_log_rows and self.move_log_rows[-1]["black"] is None:
            self.move_log_rows[-1]["black"] = move_text
        else:
            self.move_log_rows.append({"white": None, "black": move_text})

    def _commit_move(self, move, description):
        now = pygame.time.get_ticks()
        if not self._update_clock(now):
            return False
        moving_color = self.board.turn
        self._record_move(move, moving_color)
        self.board.makeMove(move)
        self.selected_square = None
        self.selected_moves = []
        self._record_position()
        self.clock_tick_at = pygame.time.get_ticks()
        self.last_move_time = self.clock_tick_at
        self.status_text = description
        return True

    def _handle_human_click(self, position, now):
        if self.game_over or self.game_mode != "human vs ai":
            return False
        if self.board.turn != self.human_color or not self._update_clock(now):
            return False

        clicked_piece = self.board.getSquare(position).getPiece()
        if self.selected_square is not None:
            move = next(
                (
                    candidate
                    for candidate in self.selected_moves
                    if candidate.getEndPos() == position
                ),
                None,
            )
            if move is not None:
                piece_name = move.getPiece().getPieceType()
                description = (
                    f"Your move: {piece_name} "
                    f"{self.pos_to_notation(move.getStartPos())}"
                    f"->{self.pos_to_notation(move.getEndPos())}"
                )
                return self._commit_move(move, description)

        if clicked_piece is not None and clicked_piece.getTeam() == self.human_color:
            self.selected_square = position
            legal_moves = self.board.getAllLegalMove(self.human_color)
            self.selected_moves = [
                move for move in legal_moves if move.getStartPos() == position
            ]
        else:
            self.selected_square = None
            self.selected_moves = []
        return False

    def _start_ai_job(self, work, finish):
        """
        Run work(board_copy) in a background thread. When it is done,
        _poll_ai_job() calls finish(result) on the main thread.
        """
        job = {
            "done": False,
            "result": None,
            "finish": finish,
            "history_len": len(self.board.move_history),
        }
        board_copy = deepcopy(self.board)        # the thread never touches the real board

        def runner():
            job["result"] = work(board_copy)
            job["done"] = True

        self.ai_job = job
        self.ai_thread = threading.Thread(target=runner, daemon=True)
        self.ai_thread.start()
        return True

    def _poll_ai_job(self):
        """Called every frame: apply the AI move once the worker has finished."""
        job = self.ai_job
        if job is None or not job["done"]:
            return
        self.ai_thread, self.ai_job = None, None
        position_changed = len(self.board.move_history) != job["history_len"]
        if self.game_over or position_changed:
            return                                 # the game moved on; drop the result
        job["finish"](job["result"])

    def _alpha_beta_task(self):
        depth = self.depth
        self.status_text = f"Alpha-Beta thinking (up to depth {depth})..."

        def work(board_copy):
            return self.alphabeta.think_on(
                board_copy, depth, AI_TIME_LIMIT_SECONDS, history=dict(self.board_history)
            )

        def finish(result):
            move_id, _, depth_done, nodes, seconds = result
            best_move = self.alphabeta.find_real_move(move_id)
            if best_move is None:
                self.status_text = "Alpha-Beta found no move."
                return False
            description = (
                f"Alpha-Beta depth {depth_done}/{depth}: "
                f"{self.pos_to_notation(best_move.getStartPos())}"
                f"->{self.pos_to_notation(best_move.getEndPos())} "
                f"({nodes} nodes, {seconds:.1f}s)"
            )
            return self._commit_move(best_move, description)

        return work, finish

    def _mcts_task(self, color=None):
        if color is None:
            color = self.board.turn
        iterations = self.mcts_iterations
        self.status_text = f"MCTS thinking ({iterations} iterations)..."

        def work(board_copy):
            move = mcts_search(
                board_copy,
                color,
                iterations=iterations,
                exploration=0.3,
                rollout_depth=2,
            )
            return None if move is None else move.getId()

        def finish(move_id):
            real_move = self.alphabeta.find_real_move(move_id)
            if real_move is None:
                self.status_text = f"MCTS found no move for {color}."
                return False
            description = (
                f"MCTS ({iterations} iterations): "
                f"{self.pos_to_notation(real_move.getStartPos())}"
                f"->{self.pos_to_notation(real_move.getEndPos())}"
            )
            return self._commit_move(real_move, description)

        return work, finish

    def _current_ai_task(self):
        """(work, finish) for whoever is to move, or None if nobody should think."""
        if self.game_over or self.ai_thread is not None:
            return None                       # finished game, or the AI is already thinking
        current_player = self.white_ai if self.board.turn == Team.WHITE else self.black_ai
        if current_player == "human":
            self.status_text = "Your turn: select a piece, then its destination."
            return None
        if current_player == "alphabeta":
            return self._alpha_beta_task()
        if current_player == "mcts":
            return self._mcts_task()
        return None

    def run_ai_once(self):
        """Blocking version: think, play the move, return True if a move was played."""
        task = self._current_ai_task()
        if task is None:
            return False
        work, finish = task
        return bool(finish(work(deepcopy(self.board))))

    def start_ai_in_background(self):
        """Used by the window: think in a worker thread so the UI never freezes."""
        task = self._current_ai_task()
        if task is None:
            return False
        work, finish = task
        return self._start_ai_job(work, finish)

    def _is_ai_turn(self):
        current_player = self.white_ai if self.board.turn == Team.WHITE else self.black_ai
        return current_player != "human"

    def _handle_board_click(self, position, now):
        if self.game_mode == "human vs ai":
            return self._handle_human_click(position, now)

    def _draw_end_game_overlay(self):
        big_font = pygame.font.SysFont("Arial", 40, bold=True)
        text_surface = big_font.render("GAME OVER", True, (255, 80, 80))
        text_rect = text_surface.get_rect(
            center=(
                self.board_origin_x + self.board_pixel_width // 2,
                self.board_origin_y + self.board_pixel_width // 2,
            )
        )
        bg_rect = text_rect.inflate(20, 20)
        pygame.draw.rect(self.screen, (0, 0, 0), bg_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, 2)
        self.screen.blit(text_surface, text_rect)


    def _check_game_end(self):
        legal_moves = self.board.getAllLegalMove(self.board.turn)
        if not legal_moves:
            self.game_over = True
            self.autoplay = False
            if self.board.kingIsSafe():
                self.status_text = "GAME OVER: DRAW BY STALEMATE."
            else:
                winner = "BLACK" if self.board.turn == Team.WHITE else "WHITE"
                self.status_text = f"GAME OVER: {winner} WINS BY CHECKMATE."
        elif self.board.getAutomaticDrawReason() is not None:
            self.game_over = True
            self.autoplay = False
            self.status_text = f"GAME OVER: DRAW BY {self.board.getAutomaticDrawReason()}."
        elif self.board_history.get(self.board.getHash(), 0) >= 3:
            self.game_over = True
            self.autoplay = False
            self.status_text = "GAME OVER: DRAW BY THREEFOLD REPETITION."

    def run(self):
        running = True
        self.board_history[self.board.getHash()] = 1

        while running:
            current_time = pygame.time.get_ticks()
            self._update_clock(current_time)
            if not self.game_over:
                self._check_game_end()
            self._poll_ai_job()
            mouse_x, mouse_y = pygame.mouse.get_pos()
            repeat_count = self.iteration_repeater.update(
                current_time,
                pygame.mouse.get_pressed()[0]
                and self.btn_up2.collidepoint(mouse_x, mouse_y),
            )
            if repeat_count:
                self.mcts_iterations = min(
                    self.mcts_iterations + 10 * repeat_count, 10000
                )
                if self.mcts_iterations == 10000:
                    self.iteration_repeater.stop()

            if (
                self.autoplay
                and not self.game_over
                and self._is_ai_turn()
                and current_time - self.last_move_time >= self.move_delay
            ):
                self.start_ai_in_background()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.screen = toggle_fullscreen(self.window_size)
                elif event.type == pygame.MOUSEWHEEL:
                    if self.move_log_viewport.collidepoint(pygame.mouse.get_pos()):
                        max_scroll = max(
                            0,
                            len(self.move_log_rows) - self.move_log_visible_rows,
                        )
                        self.move_log_scroll = max(
                            0,
                            min(max_scroll, self.move_log_scroll - event.y),
                        )
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.iteration_repeater.stop()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    if event.button == 1 and self.btn_up2.collidepoint(mx, my):
                        self.mcts_iterations = min(
                            self.mcts_iterations + 10, 10000
                        )
                        if self.mcts_iterations < 10000:
                            self.iteration_repeater.start(current_time)
                        else:
                            self.iteration_repeater.stop()
                    if self.btn_menu.collidepoint(mx, my):
                        return "menu"
                    if self.btn_run_ai.collidepoint(mx, my) and not self.game_over:
                        self.start_ai_in_background()
                    elif self.btn_autoplay.collidepoint(mx, my) and not self.game_over:
                        self.autoplay = not self.autoplay
                        self.last_move_time = pygame.time.get_ticks()
                    elif self.btn_up1.collidepoint(mx, my):
                        self.depth = min(self.depth + 1, 8)
                    elif self.btn_down1.collidepoint(mx, my):
                        self.depth = max(self.depth - 1, 1)
                    elif self.btn_down2.collidepoint(mx, my):
                        self.mcts_iterations = max(self.mcts_iterations - 10, 10)
                    elif (
                        self.board_origin_x <= mx < self.board_origin_x + self.board_pixel_width
                        and self.board_origin_y <= my < self.board_origin_y + self.board_pixel_width
                    ):
                        row = (my - self.board_origin_y) // self.cell
                        col = (mx - self.board_origin_x) // self.cell
                        self._handle_board_click(row * 8 + col, pygame.time.get_ticks())

            self.screen.fill((30, 30, 30))
            self.draw_board()
            self.draw_controls()
            if self.game_over:
                self._draw_end_game_overlay()
            pygame.display.flip()
            self.frame_clock.tick(60)
        return "quit"