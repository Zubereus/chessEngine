import pygame
from src.setting import *
from src.chess_replicated.chess_board import Move
from src.chess_replicated.ai_thinking import AIThinkTank
from src.algorithm.MCTS_algo.MCTS import mcts_search
import os

class UI:
    def __init__(self, board, algorithm, depth, mcts_iterations):
        pygame.init()
        self.board = board
        self.board_history = {}
        self.depth = depth
        self.mcts_iterations = mcts_iterations
        self.algorithm = algorithm
        if algorithm == "alphabeta vs mcts":
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
        # ===== BOARD SIZE =====
        BOARD_PIXEL_SIZE = 560
        self.cell = BOARD_PIXEL_SIZE // 8
        self.board_pixel_width = self.cell * 8

        # ===== WINDOW =====
        self.window_width = 1200
        self.window_height = self.board_pixel_width + 200

        self.screen = pygame.display.set_mode((self.window_width, self.window_height))

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
        self.status_text = ""

        # Load images
        self.images = self._load_assets()
        # Mapping new alpha-beta to UI
        self.alphabeta = AIThinkTank(self.board)
        self.autoplay = False  # Trạng thái tự động chơi
        self.move_delay = 600  # Khoảng nghỉ giữa các nước đi (miliseconds)
        self.last_move_time = pygame.time.get_ticks()

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

    # ===== CONTROL PANEL =====
    def draw_controls(self):
        panel_y = self.board_pixel_width + 30

        # ===== ALGORITHM LABEL =====
        if self.algorithm == "alphabeta vs alphabeta" or self.algorithm == "mcts vs mcts":
            is_ab = self.algorithm == "alphabeta vs alphabeta"
            algo_color = (0, 255, 255) if is_ab else (255, 0, 255)

            algo_text = "ALPHA-BETA" if is_ab else "MCTS"
            self.screen.blit(
                self.font.render(f"ALGORITHM: {algo_text}", True, algo_color),
                (20, panel_y),
            )

            # ===== DEPTH =====
            depth_color = (255, 255, 255) if is_ab else (100, 100, 100)
            if is_ab:
                depth_display = self.depth
            else:
                depth_display = f"{self.mcts_iterations} iters"

            self.screen.blit(
                self.font.render(f"SEARCH DEPTH: {depth_display}", True, depth_color),
                (20, panel_y + 40),
            )
            
            # ===== BUTTONS + - =====
            self.btn_up1 = pygame.Rect(220, panel_y + 35, 35, 35)
            self.btn_down1 = pygame.Rect(265, panel_y + 35, 35, 35)

            color_up = (50, 150, 50)
            color_down = (150, 50, 50)

            pygame.draw.rect(self.screen, color_up, self.btn_up1, border_radius=5)
            pygame.draw.rect(self.screen, color_down, self.btn_down1, border_radius=5)

            self.screen.blit(self.font.render("+", True, (255, 255, 255)), (self.btn_up1.x + 10, self.btn_up1.y + 5))
            self.screen.blit(self.font.render("-", True, (255, 255, 255)), (self.btn_down1.x + 12, self.btn_down1.y + 5))

        else:
            self.screen.blit(
                self.font.render(f"ALGORITHM: ALPHA-BETA", True, (0, 255, 255)),
                (20, panel_y),
            )
            # ===== DEPTH =====
            self.screen.blit(
                self.font.render(f"SEARCH DEPTH: {self.depth}", True, (255, 255, 255)),
                (20, panel_y + 40),
            )
            # ===== BUTTONS + - =====
            self.btn_up1 = pygame.Rect(220, panel_y + 35, 35, 35)
            self.btn_down1 = pygame.Rect(265, panel_y + 35, 35, 35)

            color_up = (50, 150, 50)
            color_down = (150, 50, 50)

            pygame.draw.rect(self.screen, color_up, self.btn_up1, border_radius=5)
            pygame.draw.rect(self.screen, color_down, self.btn_down1, border_radius=5)

            self.screen.blit(self.font.render("+", True, (255, 255, 255)), (self.btn_up1.x + 10, self.btn_up1.y + 5))
            self.screen.blit(self.font.render("-", True, (255, 255, 255)), (self.btn_down1.x + 12, self.btn_down1.y + 5))

            self.screen.blit(
                self.font.render(f"ALGORITHM: MTCS", True, (0, 255, 255)),
                (20, panel_y + 80),
            )
            # ===== DEPTH =====
            self.screen.blit(
                self.font.render(f"SEARCH DEPTH: {self.mcts_iterations} iters", True, (255, 255, 255)),
                (20, panel_y + 120),
            )
            # ===== BUTTONS + - =====
            self.btn_up2 = pygame.Rect(220, panel_y + 35 + 80, 35, 35)
            self.btn_down2 = pygame.Rect(265, panel_y + 35 + 80, 35, 35)

            color_up = (50, 150, 50)
            color_down = (150, 50, 50)

            pygame.draw.rect(self.screen, color_up, self.btn_up2, border_radius=5)
            pygame.draw.rect(self.screen, color_down, self.btn_down2, border_radius=5)

            self.screen.blit(self.font.render("+", True, (255, 255, 255)), (self.btn_up2.x + 10, self.btn_up2.y + 5))
            self.screen.blit(self.font.render("-", True, (255, 255, 255)), (self.btn_down2.x + 12, self.btn_down2.y + 5))


        #Auto_play button
        self.btn_autoplay = pygame.Rect(700, panel_y + 35, 120, 35)
        auto_color = (0, 200, 0) if self.autoplay else (150, 0, 0)
        pygame.draw.rect(self.screen, auto_color, self.btn_autoplay, border_radius=6)
        
        auto_txt = "AUTO: ON" if self.autoplay else "AUTO: OFF"
        self.screen.blit(self.font.render(auto_txt, True, (255, 255, 255)), (self.btn_autoplay.x + 15, self.btn_autoplay.y + 7))
        # ===== RUN AI BUTTON =====
        self.btn_run_ai = pygame.Rect(340, panel_y + 35, 140, 35)
        can_run = True
        run_color = (0, 122, 204) if can_run else (70, 70, 70)
        pygame.draw.rect(self.screen, run_color, self.btn_run_ai, border_radius=6)
        self.screen.blit(self.font.render("RUN AI", True, (255, 255, 255)), (self.btn_run_ai.x + 34, self.btn_run_ai.y + 7))

        # ===== RETURN MENU BUTTON =====
        self.btn_menu = pygame.Rect(500, panel_y + 35, 180, 35)
        pygame.draw.rect(self.screen, (90, 90, 90), self.btn_menu, border_radius=6)
        self.screen.blit(self.font.render("RETURN TO MENU", True, (255, 255, 255)), (self.btn_menu.x + 14, self.btn_menu.y + 7))

        if self.status_text:
            status_surface = pygame.font.SysFont("Arial", 20).render(self.status_text, True, (220, 220, 220))
            self.screen.blit(status_surface, (700, panel_y + 10))


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
                pos = (20 + c * self.cell, r * self.cell)
                self.screen.blit(square,pos)

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
                    self.screen.blit(label_surf, (5, r * self.cell + self.cell // 3))

                # 4. Vẽ ký hiệu Cột (a-h) - Chỉ vẽ ở hàng cuối cùng (r == 7)
                if r == 7:
                    label_text = chr(ord('A') + c)
                    label_surf = font.render(label_text, True, (255, 255, 255))
                    # Đặt phía dưới ô cờ
                    text_pos = (15 + c * self.cell + self.cell // 2, (r + 1) * self.cell + 5)
                    self.screen.blit(label_surf, text_pos)

    def pos_to_notation(self, pos):
        row = pos // 8
        col = pos % 8
        file = chr(ord('a') + col)  # Chuyển cột thành ký tự a-h
        rank = str(8 - row)           # Chuyển hàng thành số 1-8 (đếm từ dưới lên)
        return f"{file}{rank}"

    def _run_alpha_beta(self):
        # 1. Gọi AI tìm nước đi
        best_move, best_score = self.alphabeta.think(self.depth)  # Trả về đối tượng Move hoặc None nếu không có nước đi nào hợp lệ
        
        if best_move:
            # 2. Trích xuất thông tin từ đối tượng Move và Piece
            piece = best_move.getPiece()
            p_type = piece.piece_type.upper()       # VD: PAWN, KING
            p_color = piece.team.upper()     # VD: WHITE, BLACK
            m_type = best_move.getType()       # VD: ATTACK, PROMOTION...
            start = best_move.getStartPos()
            end = best_move.getEndPos()
            start_notation = self.pos_to_notation(start)
            end_notation = self.pos_to_notation(end)
            # 3. IN RA CONSOLE THEO ĐỊNH DẠNG YÊU CẦU
            # Kết quả: "Quân cờ WHITE PAWN di chuyển (1, 0) -> (2, 0) [NORMAL]"
            
            # 4. Thực hiện di chuyển và in bàn cờ
            self.board.makeMove(best_move)
            print(self.board)  # In ra console để kiểm tra
            # Cập nhật UI
            self.status_text = f"A-B (depth = {self.depth}): {p_color} {p_type} {start_notation}->{end_notation} [{m_type}]"
            return True
            
        return False

    def _run_mcts(self, color=None):
        if color is None:
            color = self.board.turn
        best_move = mcts_search(
            self.board,
            color,
            iterations=self.mcts_iterations,
            exploration=1.41,
            rollout_depth=12
        )

        if best_move:
            start = best_move.getStartPos()
            end = best_move.getEndPos()
            piece = self.board.getSquare(start).getPiece()
            attacked = self.board.getSquare(end).getPiece()
            m_type = best_move.getType()

            real_move = Move(piece, end, m_type, attacked)
            self.board.makeMove(real_move)

            p_type = piece.piece_type.upper()
            p_color = piece.team.upper()

            start_notation = self.pos_to_notation(start)
            end_notation = self.pos_to_notation(end)

            self.status_text = f"MCTS (iterations = {self.mcts_iterations}): {p_color} {p_type} {start_notation}->{end_notation} [{m_type}]"
            return True

        self.status_text = f"MCTS found no move for {color}."
        return False

    def run_ai_once(self):
        current_player = self.white_ai if self.board.turn == "WHITE" else self.black_ai
        if current_player == "alphabeta":
            return self._run_alpha_beta()
        elif current_player == "mcts":
            return self._run_mcts()
    def _draw_end_game_overlay(self):
        # Tạo font chữ lớn
        big_font = pygame.font.SysFont("Arial", 40, bold=True)
        text_surface = big_font.render("GAME OVER", True, (255, 0, 0))
        
        # Lấy vị trí trung tâm bàn cờ
        text_rect = text_surface.get_rect(center=(600 + self.board_pixel_width // 2 + 20, self.board_pixel_width // 2))
        
        # Vẽ một hình chữ nhật nền phía sau chữ cho dễ đọc
        bg_rect = text_rect.inflate(20, 20)
        pygame.draw.rect(self.screen, (0, 0, 0), bg_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, 2)
        
        self.screen.blit(text_surface, text_rect)
        
    # ===== MAIN LOOP =====

    def run(self):
        running = True
        game_over = False # Biến cờ để khóa tương tác khi kết thúc
        current_hash = self.board.getHash()
        self.board_history[current_hash] = 1
        def isDraw(board):
            if self.board_history[current_hash] > 3:
                return True, "3-fold repetition"
            if board.isEndGameScenario() and board.kingIsSafe():
                return True, "Stalemate"
            if board.isKingVsKing():
                return True, "King vs King"
            return False, None

        while running:
            current_time = pygame.time.get_ticks()
            # 1. KIỂM TRA TRẠNG THÁI KẾT THÚC
            if self.board.isEndGameScenario():
                game_over = True
                self.autoplay = False
                # Xác định thông báo cụ thể
                if self.board.turn == "WHITE":
                    self.status_text = "GAME OVER: BLACK WINS (Check Mate)!"
                else:
                    self.status_text = "GAME OVER: WHITE WINS (Check Mate)!"
            draw, reason = isDraw(self.board)
            if not game_over and draw:
                game_over = True
                self.autoplay = False
                self.status_text = f"GAME OVER: DRAW by {reason}!"

            if self.autoplay and not game_over:
                # Tự động chạy AI sau mỗi khoảng thời gian định sẵn
                if current_time - self.last_move_time > self.move_delay:
                    self.run_ai_once()
                    current_hash = self.board.getHash()
                    self.board_history[current_hash] = self.board_history.get(current_hash, 0) + 1
                    self.last_move_time = current_time
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    
                    # 2. CHỈ CHẠY AI NẾU CHƯA KẾT THÚC
                    if self.btn_run_ai.collidepoint(mx, my):
                        if not game_over:
                            self.run_ai_once()
                            current_hash = self.board.getHash()
                            self.board_history[current_hash] = self.board_history.get(current_hash, 0) + 1
                            print(f"Board hash after move: {current_hash}, count: {self.board_history[current_hash]}")
                        else:
                            print("The game has already ended. Please return to menu.")
                    if self.btn_autoplay.collidepoint(mx, my) and not game_over:
                        self.autoplay = not self.autoplay
                    if self.btn_menu.collidepoint(mx, my):
                        running = False
                        return "menu"
                    
                    # Nhóm 1: Nút điều chỉnh chung hoặc nút bên trái (Thường là Depth)
                    if self.btn_up1.collidepoint(mx, my):
                        if self.algorithm == "mcts vs mcts":
                            self.mcts_iterations = min(self.mcts_iterations + 10, 200)
                        else: # alphabeta vs alphabeta HOẶC chế độ mixed
                            self.depth = min(self.depth + 1, 8)
                            
                    elif self.btn_down1.collidepoint(mx, my):
                        if self.algorithm == "mcts vs mcts":
                            self.mcts_iterations = max(self.mcts_iterations - 10, 10)
                        else:
                            self.depth = max(self.depth - 1, 1)

                    # Nhóm 2: Nút điều chỉnh bên phải (Chỉ xuất hiện trong chế độ mixed - Iterations)
                    elif self.btn_up2.collidepoint(mx, my):
                        self.mcts_iterations = min(self.mcts_iterations + 10, 200)
                        
                    elif self.btn_down2.collidepoint(mx, my):
                        self.mcts_iterations = max(self.mcts_iterations - 10, 10)

            # 3. VẼ GIAO DIỆN
            self.screen.fill((30, 30, 30))
            self.draw_board()
            self.draw_controls()
            
            # Nếu game kết thúc, vẽ thêm một lớp phủ mờ (Overlay) hoặc chữ to ở giữa
            if game_over:
                self._draw_end_game_overlay()

            pygame.display.flip()
        return "quit"