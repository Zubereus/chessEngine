import pygame
import os
from src.chess_replicated.chess_board import Board
pygame.init()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
IMG_DIR = os.path.join(PROJECT_ROOT, "assets", "chess_img")

PIECES = ["king", "queen", "bishop", "knight", "rook", "pawn"]

# ===== LOAD IMAGE =====
def load_img(name, size=(60, 60)):
    path = os.path.join(IMG_DIR, name)
    if os.path.exists(path):
        img = pygame.image.load(path)
        return pygame.transform.scale(img, size)
    else:
        # debug nếu thiếu ảnh
        surf = pygame.Surface(size)
        surf.fill((255, 0, 0))
        return surf


def get_config():
    screen = pygame.display.set_mode((960, 650))
    pygame.display.set_caption("Chess Config Custom")

    font = pygame.font.SysFont("Arial", 24, bold=True)
    small_font = pygame.font.SysFont("Arial", 18)

    # ===== CONFIG =====
    modes = ["Standard", "Custom"]
    selected_mode = "Standard"
    size = 8

    white_counts = [1, 0, 0, 0, 0, 0]
    black_counts = [1, 0, 0, 0, 0, 0]
    LIMITS = [1, 1, 2, 2, 2, 8]


    algorithm = "alphabeta vs alphabeta"
    depth = 2
    mcts_iterations = 100

    WHITE_Y = 270
    BLACK_Y = 450

    # ===== LOAD PIECES =====
    white_imgs = [load_img(f"w_{p}.png") for p in PIECES]
    black_imgs = [load_img(f"b_{p}.png") for p in PIECES]
    # ===== BUTTON =====
    btn_up1 = pygame.Rect(0,0,0,0)
    btn_down1 = pygame.Rect(0,0,0,0)
    btn_up2 = pygame.Rect(0,0,0,0)
    btn_down2 = pygame.Rect(0,0,0,0)

    clock = pygame.time.Clock()

    while True:
        screen.fill((45, 45, 48))
        total_pieces = sum(white_counts) + sum(black_counts)
        max_cells = size * size

        # ===== MODE =====
        label = font.render("MODE:", True, (255,255,255))
        label_rect = label.get_rect()
        label_rect.midleft = (50, 50)
        screen.blit(label, label_rect)

        for i, mode in enumerate(modes):
            btn = pygame.Rect(250 + i*170, 25, 150, 40)
            color = (0,120,215) if mode == selected_mode else (80,80,80)
            pygame.draw.rect(screen, color, btn, border_radius=5)
            val_surf = font.render(mode, True, (255,255,255))
            val_rect = val_surf.get_rect(center=btn.center)
            screen.blit(val_surf, val_rect)

            if btn.collidepoint(pygame.mouse.get_pos()):
                if pygame.mouse.get_pressed()[0]:
                    selected_mode = mode
        

        # ===== ALGORITHM =====
        label = font.render("ALGORITHM:", True, (255,255,255))
        label_rect = label.get_rect()
        label_rect.midleft = (50, 100)
        screen.blit(label, label_rect)

        btn_ab_vs_ab = pygame.Rect(250, 75, 150, 40)
        btn_mcts_vs_mcts = pygame.Rect(420, 75, 150, 40)
        btn_ab_vs_mcts = pygame.Rect(590, 75, 150, 40)
        btn_mcts_vs_ab = pygame.Rect(760, 75, 150, 40)

        pygame.draw.rect(screen, (0,120,215) if algorithm=="alphabeta vs alphabeta" else (80,80,80), btn_ab_vs_ab, border_radius=5)
        pygame.draw.rect(screen, (150,50,150) if algorithm=="mcts vs mcts" else (80,80,80), btn_mcts_vs_mcts, border_radius=5)
        pygame.draw.rect(screen, (0,120,215) if algorithm=="alphabeta vs mcts" else (80,80,80), btn_ab_vs_mcts, border_radius=5)
        pygame.draw.rect(screen, (150,50,150) if algorithm=="mcts vs alphabeta" else (80,80,80), btn_mcts_vs_ab, border_radius=5)

        ab_vs_ab_surf = font.render("A-B vs A-B", True, (255,255,255))
        ab_vs_ab_rect = ab_vs_ab_surf.get_rect(center=btn_ab_vs_ab.center)
        screen.blit(ab_vs_ab_surf, ab_vs_ab_rect)

        mcts_vs_mcts_surf = font.render("MCTS vs MCTS", True, (255,255,255))
        mcts_vs_mcts_rect = mcts_vs_mcts_surf.get_rect(center=btn_mcts_vs_mcts.center)
        screen.blit(mcts_vs_mcts_surf, mcts_vs_mcts_rect)

        ab_vs_mcts_surf = font.render("A-B vs MTCS", True, (255,255,255))
        ab_vs_mcts_rect = ab_vs_mcts_surf.get_rect(center=btn_ab_vs_mcts.center)
        screen.blit(ab_vs_mcts_surf, ab_vs_mcts_rect)

        mcts_vs_ab_surf = font.render("MCTS vs A-B", True, (255,255,255))
        mcts_vs_ab_rect = mcts_vs_ab_surf.get_rect(center=btn_mcts_vs_ab.center)
        screen.blit(mcts_vs_ab_surf, mcts_vs_ab_rect)

        # ===== DEPTH =====
        if algorithm == "alphabeta vs alphabeta" or algorithm == "mcts vs mcts":
            label_text = "DEPTH:" if algorithm == "alphabeta vs alphabeta" else "ITERATIONS:"
            label = font.render(label_text, True, (255,255,255))
            label_rect = label.get_rect()
            label_rect.midleft = (50, 150)
            screen.blit(label, label_rect)

            btn_up1 = pygame.Rect(250, 125, 40, 40)
            btn_down1 = pygame.Rect(300, 125, 40, 40)

            is_ab = (algorithm == "alphabeta vs alphabeta")

            pygame.draw.rect(screen, (50,150,50), btn_up1, border_radius=5)
            pygame.draw.rect(screen, (150,50,50), btn_down1, border_radius=5)

            plus_surf = font.render("+", True, (255,255,255))
            plus_rect = plus_surf.get_rect(center=btn_up1.center)
            screen.blit(plus_surf, plus_rect)
            minus_surf = font.render("-", True, (255,255,255))
            minus_rect = minus_surf.get_rect(center=btn_down1.center)
            screen.blit(minus_surf, minus_rect)

            if is_ab:
                depth_text = str(depth)
            else:
                depth_text = str(mcts_iterations)
            depth_surf = font.render(depth_text, True, (255,255,0))
            depth_rect = depth_surf.get_rect()
            depth_rect.midleft = (360, 145)
            screen.blit(depth_surf, depth_rect)
        else:
            #===== DEPTH + ITERATION =====
            label_text = "DEPTH:"
            label = font.render(label_text, True, (255,255,255))
            label_rect = label.get_rect()
            label_rect.midleft = (50, 150)
            screen.blit(label, label_rect)

            btn_up1 = pygame.Rect(250, 125, 40, 40)
            btn_down1 = pygame.Rect(300, 125, 40, 40)

            pygame.draw.rect(screen, (50,150,50), btn_up1, border_radius=5)
            pygame.draw.rect(screen, (150,50,50), btn_down1, border_radius=5)

            plus_surf = font.render("+", True, (255,255,255))
            plus_rect = plus_surf.get_rect(center=btn_up1.center)
            screen.blit(plus_surf, plus_rect)
            minus_surf = font.render("-", True, (255,255,255))
            minus_rect = minus_surf.get_rect(center=btn_down1.center)
            screen.blit(minus_surf, minus_rect)

            depth_surf = font.render(str(depth), True, (255,255,0))
            depth_rect = depth_surf.get_rect()
            depth_rect.midleft = (360, 145)
            screen.blit(depth_surf, depth_rect)


            label_text = "ITERATIONS:"
            label = font.render(label_text, True, (255,255,255))
            label_rect = label.get_rect()
            label_rect.midleft = (50, 200)
            screen.blit(label, label_rect)

            btn_up2 = pygame.Rect(250, 175, 40, 40)
            btn_down2 = pygame.Rect(300, 175, 40, 40)

            pygame.draw.rect(screen, (50,150,50), btn_up2, border_radius=5)
            pygame.draw.rect(screen, (150,50,50), btn_down2, border_radius=5)

            plus_surf = font.render("+", True, (255,255,255))
            plus_rect = plus_surf.get_rect(center=btn_up2.center)
            screen.blit(plus_surf, plus_rect)
            minus_surf = font.render("-", True, (255,255,255))
            minus_rect = minus_surf.get_rect(center=btn_down2.center)
            screen.blit(minus_surf, minus_rect)

            depth_surf = font.render(str(mcts_iterations), True, (255,255,0))
            depth_rect = depth_surf.get_rect()
            depth_rect.midleft = (360, 195)
            screen.blit(depth_surf, depth_rect)

        # ===== CUSTOM MODE =====
        if selected_mode == "Custom":
            for j, (color_name, counts, imgs, start_y) in enumerate([
                ("WHITE TEAM", white_counts, white_imgs, WHITE_Y),
                ("BLACK TEAM", black_counts, black_imgs, BLACK_Y)
            ]):
                label = font.render(color_name, True, (255,255,255))
                label_rect = label.get_rect()
                label_rect.midleft = (50, start_y - 20)
                screen.blit(label, label_rect)

                for i in range(1, 6):
                    x = 100 + (i - 1) * 140

                    img_rect = imgs[i].get_rect()
                    img_rect.center = (x + 65, start_y + 30)
                    screen.blit(imgs[i], img_rect)

                    # Draw piece count (number) exactly as before, centered below the piece image
                    txt = font.render(str(counts[i]), True, (255,255,0))
                    txt_rect = txt.get_rect(center=(x + 65, start_y + 85))
                    screen.blit(txt, txt_rect)

                    btn_plus = pygame.Rect(x + 85, start_y + 70, 30, 30)
                    btn_minus = pygame.Rect(x + 15, start_y + 70, 30, 30)

                    pygame.draw.rect(screen, (50,150,50), btn_plus, border_radius=15)
                    pygame.draw.rect(screen, (150,50,50), btn_minus, border_radius=15)

                    plus_surf = small_font.render("+", True, (255,255,255))
                    plus_rect = plus_surf.get_rect(center=btn_plus.center)
                    screen.blit(plus_surf, plus_rect)
                    minus_surf = small_font.render("-", True, (255,255,255))
                    minus_rect = minus_surf.get_rect(center=btn_minus.center)
                    screen.blit(minus_surf, minus_rect)

        # ===== EVENTS =====
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                if btn_ab_vs_ab.collidepoint(mx, my):
                    algorithm = "alphabeta vs alphabeta"

                if btn_mcts_vs_mcts.collidepoint(mx, my):
                    algorithm = "mcts vs mcts"

                if btn_ab_vs_mcts.collidepoint(mx, my):
                    algorithm = "alphabeta vs mcts"

                if btn_mcts_vs_ab.collidepoint(mx, my):
                    algorithm = "mcts vs alphabeta"

                if btn_up1.collidepoint(mx, my):
                    if algorithm == "alphabeta vs alphabeta" or algorithm == "alphabeta vs mcts" or algorithm == "mcts vs alphabeta":
                        depth = min(depth + 1, 8)
                    elif algorithm == "mcts vs mcts":
                        mcts_iterations = min(mcts_iterations + 10, 200)

                if btn_down1.collidepoint(mx, my):
                    if algorithm == "alphabeta vs alphabeta" or algorithm == "alphabeta vs mcts" or algorithm == "mcts vs alphabeta":
                        depth = max(depth - 1, 1)
                    elif algorithm == "mcts vs mcts":
                        mcts_iterations = max(mcts_iterations - 10, 10)

                # XỬ LÝ NÚT UP/DOWN 2 (Chỉ dành cho Iterations khi ở chế độ đối đầu mixed)
                if btn_up2.collidepoint(mx, my):
                    mcts_iterations = min(mcts_iterations + 10, 200)
                
                if btn_down2.collidepoint(mx, my):
                    mcts_iterations = max(mcts_iterations - 10, 10)

                if selected_mode == "Custom":
                    for j, cnts in enumerate([white_counts, black_counts]):
                        y_base = WHITE_Y if j == 0 else BLACK_Y

                        for i in range(1, 6):
                            x = 100 + (i - 1) * 140
                            btn_plus = pygame.Rect(x + 85, y_base + 70, 30, 30)
                            btn_minus = pygame.Rect(x + 15, y_base + 70, 30, 30)
                            if btn_plus.collidepoint(mx, my):
                                if cnts[i] < LIMITS[i]:
                                    cnts[i] += 1
                            if btn_minus.collidepoint(mx, my):
                                if cnts[i] > 0:
                                    cnts[i] -= 1
                    

        # ===== START =====

        btn_start = pygame.Rect(380, 580, 200, 50)

        pygame.draw.rect(screen, (0,122,204), btn_start, border_radius=10)
        start_surf = font.render("START GAME", True, (255,255,255))
        start_rect = start_surf.get_rect(center=btn_start.center)
        screen.blit(start_surf, start_rect)

        if pygame.mouse.get_pressed()[0]:
            if btn_start.collidepoint(pygame.mouse.get_pos()):
                PIECES_KEYS = ["king", "queen", "bishop", "knight", "rook", "pawn"]
                white_dict = {PIECES_KEYS[i]: white_counts[i] for i in range(6) if white_counts[i] > 0}
                black_dict = {PIECES_KEYS[i]: black_counts[i] for i in range(6) if black_counts[i] > 0}
                # Trả về các giá trị đã được format đúng
                board_config = Board()
                if selected_mode == "Custom":
                    board_config.setUpRandomBoard(white_dict, black_dict)
                return board_config, algorithm, depth, mcts_iterations


        pygame.display.flip()
        clock.tick(60)
        