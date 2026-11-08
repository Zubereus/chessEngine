import pygame
import os
from src.chess_replicated.chess_board import Board
from src.chess_replicated.display import create_display, toggle_fullscreen
from src.chess_replicated.mouse_repeat import MouseHoldRepeater
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
    screen_size = (960, 800)
    screen = create_display(screen_size)
    pygame.display.set_caption("Chess Config Custom")

    font = pygame.font.SysFont("Arial", 24, bold=True)
    small_font = pygame.font.SysFont("Arial", 18, bold=True)

    # ===== CONFIG =====
    modes = ["Standard", "Custom"]
    selected_mode = "Standard"
    size = 8

    white_counts = [1, 0, 0, 0, 0, 0]
    black_counts = [1, 0, 0, 0, 0, 0]
    LIMITS = [1, 1, 2, 2, 2, 8]


    game_mode = "human vs ai"
    algorithm = "alphabeta"
    depth = 2
    mcts_iterations = 100
    clock_minutes = 10

    WHITE_Y = 350
    BLACK_Y = 530

    # ===== LOAD PIECES =====
    white_imgs = [load_img(f"w_{p}.png") for p in PIECES]
    black_imgs = [load_img(f"b_{p}.png") for p in PIECES]
    # ===== BUTTON =====
    btn_up1 = pygame.Rect(0,0,0,0)
    btn_down1 = pygame.Rect(0,0,0,0)
    btn_up2 = pygame.Rect(0,0,0,0)
    btn_down2 = pygame.Rect(0,0,0,0)
    btn_start = pygame.Rect(380, 730, 200, 50)
    iteration_repeater = MouseHoldRepeater()

    clock = pygame.time.Clock()

    while True:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        mouse_held = pygame.mouse.get_pressed()[0]
        repeat_count = iteration_repeater.update(
            pygame.time.get_ticks(),
            mouse_held and btn_up2.collidepoint(mouse_x, mouse_y),
        )
        if repeat_count:
            mcts_iterations = min(mcts_iterations + 10 * repeat_count, 10000)
            if mcts_iterations == 10000:
                iteration_repeater.stop()

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
        

        # ===== GAME MODE =====
        label = font.render("PLAY:", True, (255,255,255))
        label_rect = label.get_rect()
        label_rect.midleft = (50, 100)
        screen.blit(label, label_rect)

        btn_human_vs_ai = pygame.Rect(250, 75, 200, 40)
        btn_ai_vs_ai = pygame.Rect(470, 75, 200, 40)
        for button, value, text in (
            (btn_human_vs_ai, "human vs ai", "HUMAN VS AI"),
            (btn_ai_vs_ai, "ai vs ai", "AI VS AI"),
        ):
            pygame.draw.rect(
                screen,
                (0, 120, 215) if game_mode == value else (80, 80, 80),
                button,
                border_radius=5,
            )
            rendered = small_font.render(text, True, (255, 255, 255))
            screen.blit(rendered, rendered.get_rect(center=button.center))

        # ===== ALGORITHM =====
        label = font.render("AI:", True, (255,255,255))
        label_rect = label.get_rect()
        label_rect.midleft = (50, 150)
        screen.blit(label, label_rect)

        btn_ab_vs_ab = pygame.Rect(250, 125, 150, 40)
        btn_mcts_vs_mcts = pygame.Rect(420, 125, 150, 40)
        btn_ab_vs_mcts = pygame.Rect(590, 125, 150, 40)
        btn_mcts_vs_ab = pygame.Rect(760, 125, 150, 40)
        ai_buttons = (
            (btn_ab_vs_ab, "alphabeta", "ALPHA-BETA"),
            (btn_mcts_vs_mcts, "mcts", "MONTE CARLO"),
            (btn_ab_vs_mcts, "alphabeta vs mcts", "A-B vs MCTS"),
            (btn_mcts_vs_ab, "mcts vs alphabeta", "MCTS vs A-B"),
        )
        visible_ai_buttons = ai_buttons[:2] if game_mode == "human vs ai" else ai_buttons
        for button, value, text in visible_ai_buttons:
            selected_algorithm = value
            if game_mode == "ai vs ai" and value in {"alphabeta", "mcts"}:
                selected_algorithm = f"{value} vs {value}"
            is_selected = algorithm == selected_algorithm
            pygame.draw.rect(
                screen,
                (150, 50, 150) if is_selected and "mcts" in selected_algorithm else
                (0, 120, 215) if is_selected else (80, 80, 80),
                button,
                border_radius=5,
            )
            rendered = small_font.render(text, True, (255, 255, 255))
            screen.blit(rendered, rendered.get_rect(center=button.center))

        # ===== SEARCH SETTINGS =====
        for label_text, value, up_button, down_button, y in (
            ("DEPTH:", depth, pygame.Rect(250, 175, 40, 40), pygame.Rect(300, 175, 40, 40), 200),
            ("ITERATIONS:", mcts_iterations, pygame.Rect(250, 225, 40, 40), pygame.Rect(300, 225, 40, 40), 250),
        ):
            screen.blit(font.render(label_text, True, (255,255,255)), (50, y - 5))
            pygame.draw.rect(screen, (50,150,50), up_button, border_radius=5)
            pygame.draw.rect(screen, (150,50,50), down_button, border_radius=5)
            plus = font.render("+", True, (255,255,255))
            minus = font.render("-", True, (255,255,255))
            screen.blit(plus, plus.get_rect(center=up_button.center))
            screen.blit(minus, minus.get_rect(center=down_button.center))
            screen.blit(font.render(str(value), True, (255,255,0)), (360, y - 5))
        btn_up1 = pygame.Rect(250, 175, 40, 40)
        btn_down1 = pygame.Rect(300, 175, 40, 40)
        btn_up2 = pygame.Rect(250, 225, 40, 40)
        btn_down2 = pygame.Rect(300, 225, 40, 40)

        # ===== GAME CLOCK =====
        screen.blit(font.render("CLOCK PER SIDE:", True, (255,255,255)), (50, 285))
        btn_clock_down = pygame.Rect(280, 275, 40, 40)
        btn_clock_up = pygame.Rect(460, 275, 40, 40)
        for button, symbol, color in (
            (btn_clock_down, "-", (150, 50, 50)),
            (btn_clock_up, "+", (50, 150, 50)),
        ):
            pygame.draw.rect(screen, color, button, border_radius=5)
            rendered = font.render(symbol, True, (255,255,255))
            screen.blit(rendered, rendered.get_rect(center=button.center))
        value = font.render(f"{clock_minutes} min", True, (255,255,0))
        screen.blit(value, value.get_rect(center=(375, 295)))

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

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                screen = toggle_fullscreen(screen_size)
                continue

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                iteration_repeater.stop()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                if event.button == 1 and btn_up2.collidepoint(mx, my):
                    mcts_iterations = min(mcts_iterations + 10, 10000)
                    if mcts_iterations < 10000:
                        iteration_repeater.start(pygame.time.get_ticks())
                    else:
                        iteration_repeater.stop()

                if btn_human_vs_ai.collidepoint(mx, my):
                    game_mode = "human vs ai"
                    if algorithm not in {"alphabeta", "mcts"}:
                        algorithm = "alphabeta"
                elif btn_ai_vs_ai.collidepoint(mx, my):
                    game_mode = "ai vs ai"
                    if algorithm in {"alphabeta", "mcts"}:
                        algorithm = f"{algorithm} vs {algorithm}"

                if game_mode == "human vs ai":
                    if btn_ab_vs_ab.collidepoint(mx, my):
                        algorithm = "alphabeta"
                    elif btn_mcts_vs_mcts.collidepoint(mx, my):
                        algorithm = "mcts"
                else:
                    if btn_ab_vs_ab.collidepoint(mx, my):
                        algorithm = "alphabeta vs alphabeta"
                    elif btn_mcts_vs_mcts.collidepoint(mx, my):
                        algorithm = "mcts vs mcts"
                    elif btn_ab_vs_mcts.collidepoint(mx, my):
                        algorithm = "alphabeta vs mcts"
                    elif btn_mcts_vs_ab.collidepoint(mx, my):
                        algorithm = "mcts vs alphabeta"

                if btn_up1.collidepoint(mx, my):
                    depth = min(depth + 1, 8)
                elif btn_down1.collidepoint(mx, my):
                    depth = max(depth - 1, 1)
                if btn_down2.collidepoint(mx, my):
                    mcts_iterations = max(mcts_iterations - 10, 10)

                if btn_clock_up.collidepoint(mx, my):
                    clock_minutes = min(clock_minutes + 1, 180)
                elif btn_clock_down.collidepoint(mx, my):
                    clock_minutes = max(clock_minutes - 1, 1)

                if btn_start.collidepoint(mx, my):
                    pieces_keys = ["king", "queen", "bishop", "knight", "rook", "pawn"]
                    white_dict = {
                        pieces_keys[i]: white_counts[i]
                        for i in range(6)
                        if white_counts[i] > 0
                    }
                    black_dict = {
                        pieces_keys[i]: black_counts[i]
                        for i in range(6)
                        if black_counts[i] > 0
                    }
                    board_config = Board()
                    if selected_mode == "Custom":
                        board_config.setUpRandomBoard(white_dict, black_dict)
                    return (
                        board_config,
                        algorithm,
                        depth,
                        mcts_iterations,
                        game_mode,
                        clock_minutes,
                    )

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

        pygame.draw.rect(screen, (0,122,204), btn_start, border_radius=10)
        start_surf = font.render("START GAME", True, (255,255,255))
        start_rect = start_surf.get_rect(center=btn_start.center)
        screen.blit(start_surf, start_rect)
        fullscreen_hint = small_font.render(
            "F11: FULLSCREEN", True, (170, 170, 175)
        )
        screen.blit(
            fullscreen_hint,
            fullscreen_hint.get_rect(bottomright=(930, 785)),
        )

        pygame.display.flip()
        clock.tick(60)
        