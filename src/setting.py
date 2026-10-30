import os

# --- KÍCH THƯỚC GIAO DIỆN ---
CELL_SIZE = 80
BOTTOM_PANEL_HEIGHT = 120
SIDE_PANEL_WIDTH = 0

# --- MÀU SẮC ---
COLOR_BOARD_LIGHT = (235, 235, 208)
COLOR_BOARD_DARK = (119, 148, 85)
COLOR_PANEL_BG = (30, 30, 30)
COLOR_TEXT = (255, 255, 255)
COLOR_BTN_MINIMAX = (0, 120, 215)
COLOR_BTN_MCTS = (150, 50, 150)

# --- PATH ROOT ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

# --- PATH ALGORITHM ---
PATH_ALPHA_BETA = os.path.join(PROJECT_ROOT, "src", "algorithm", "alpha_beta_pruning.py")
PATH_MCTS = os.path.join(PROJECT_ROOT, "src", "algorithm", "MCTS.py")

# --- PATH IMAGE ---
IMG_DIR = os.path.join(PROJECT_ROOT, "assets", "chess_img")

# --- GAME CONFIG ---
PIECE_TYPES = ["king", "queen", "bishop", "knight", "rook", "pawn"]