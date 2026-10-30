import time
from collections import defaultdict
from src.chess_replicated.chess_board import Board, Team, Move
from src.chess_replicated.evaluator import Evaluator
from src.chess_replicated.ai_thinking import AIThinkTank
from src.algorithm.MCTS_algo.MCTS import mcts_search
from src.chess_replicated.enum_chess import MoveType


# ─── Tiện ích ──────────────────────────────────────────────────────────────

def pos_to_algebraic(pos):
    col = pos % 8
    row = 8 - (pos // 8)
    return "abcdefgh"[col] + str(row)


def move_to_uci(move):
    from_sq = pos_to_algebraic(move.getStartPos())
    to_sq   = pos_to_algebraic(move.getEndPos())
    if move.getType() in [MoveType.PAWN, MoveType.PAWN_ATTACK]:
        end_row = move.getEndPos() // 8
        if end_row == 0 or end_row == 7:
            return from_sq + to_sq + "q"
    return from_sq + to_sq


def isDraw(board, position_counts):
    """
    Kiểm tra các điều kiện hoà:
    - Stalemate (hết nước đi mà vua không bị chiếu)
    - Vua vs Vua
    - Lặp thế cờ 3 lần (Threefold Repetition) dựa trên Zobrist hash
    """
    if board.isEndGameScenario() and board.kingIsSafe():
        return True, "Stalemate"
    if board.isKingVsKing():
        return True, "Vua vs Vua"
    if position_counts[board.getHash()] >= 3:
        return True, "Lặp thế cờ 3 lần"
    return False, None


# ─── Wrapper AI ────────────────────────────────────────────────────────────

class AlphaBetaPlayer:
    """Wrapper AlphaBeta — giao diện thống nhất với MCTSPlayer."""

    def __init__(self, board, depth=3):
        self.depth    = depth
        self._ai      = AIThinkTank(board)
        self.label    = f"AlphaBeta(d={depth})"
        self._last_score = None

    def get_move(self):
        best_move, best_score = self._ai.think(self.depth)  # unpack tuple
        self._last_score = best_score
        return best_move

    def get_node_count(self):
        return self._ai.get_node_count()

    def get_last_score(self):
        """Trả về điểm đánh giá của nước đi vừa chọn (chỉ có ở AlphaBeta)."""
        return self._last_score


class MCTSPlayer:
    """Wrapper MCTS — giao diện thống nhất với AlphaBetaPlayer."""

    def __init__(self, board, iterations=300, rollout_depth=20):
        self.board          = board
        self.iterations     = iterations
        self.rollout_depth  = rollout_depth
        self.label          = f"MCTS(iter={iterations})"
        self._node_count    = 0

    def get_move(self):
        move = mcts_search(
            self.board,
            self.board.turn,
            iterations=self.iterations,
            rollout_depth=self.rollout_depth,
        )
        self._node_count = self.iterations   # MCTS duyệt đúng `iterations` node
        return move

    def get_node_count(self):
        return self._node_count

    def get_last_score(self):
        """MCTS không tính điểm tĩnh — trả về None."""
        return None


# ─── Engine chơi ván cờ ────────────────────────────────────────────────────

def play_game(white_player, black_player, board,
              max_moves=200, pgn_file="game.pgn", verbose=True):
    """
    Chạy một ván cờ giữa hai player bất kỳ.
    Trả về dict thống kê của ván cờ.
    """
    moves_pgn      = []
    result         = "*"
    move_times     = []
    node_counts    = []
    game_start     = time.time()

    # ── Theo dõi thế cờ để phát hiện lặp 3 lần ───────────────────────────
    position_counts = defaultdict(int)
    position_counts[board.getHash()] += 1   # Trạng thái ban đầu

    if verbose:
        white_label = white_player.label
        black_label = black_player.label
        print(f"\n{'='*65}")
        print(f"  ♔ Trắng : {white_label}")
        print(f"  ♚ Đen   : {black_label}")
        print(f"{'='*65}\n")

    for move_count in range(1, max_moves + 1):
        current_team   = board.turn
        current_player = white_player if current_team == Team.WHITE else black_player
        team_str       = "Trắng ♔" if current_team == Team.WHITE else "Đen ♚"

        start_time = time.time()
        best_move  = current_player.get_move()
        elapsed    = time.time() - start_time

        move_times.append(elapsed)
        node_counts.append(current_player.get_node_count())

        # Lấy điểm đánh giá (chỉ AlphaBeta mới có)
        score = current_player.get_last_score()
        
        score_str = f"{score:+d}" if score is not None else "N/A"  # ← đổi score → score_display
        
        if best_move is None:
            if board.kingIsSafe():
                result = "1/2-1/2"
                if verbose:
                    print(f"\n🤝 HÒA CỜ (Stalemate)! Sau {move_count - 1} nước đi.")
            else:
                result = "0-1" if current_team == Team.WHITE else "1-0"
                winner = black_player.label if current_team == Team.WHITE else white_player.label
                if verbose:
                    print(f"\n🏆 CHIẾU HẾT! {winner} thắng sau {move_count - 1} nước đi.")
            break

        moves_pgn.append(move_to_uci(best_move))

        if verbose:
            print(
                f"Lượt {move_count:>3} | {team_str} | "
                f"{best_move.getPiece().getPieceType()} "
                f"{best_move.getStartPos():>2} → {best_move.getEndPos():>2} | "
                f"{best_move.getType():<15} | "
                f"score: {score_str:>7} | "
                f"{elapsed:.2f}s | nodes: {current_player.get_node_count():,}"
            )

        board.makeMove(best_move)

        # Cập nhật bộ đếm thế cờ sau mỗi nước đi
        position_counts[board.getHash()] += 1

        is_draw, draw_reason = isDraw(board, position_counts)
        if is_draw:
            result = "1/2-1/2"
            if verbose:
                print(f"\n🤝 HÒA CỜ ({draw_reason})! Sau {move_count} nước đi.")
            break

        if board.isEndGameScenario():
            result = "1-0" if current_team == Team.WHITE else "0-1"
            winner = white_player.label if current_team == Team.WHITE else black_player.label
            if verbose:
                print(f"\n🏆 CHIẾU HẾT! {winner} thắng sau {move_count} nước đi.")
            break
    else:
        if verbose:
            print(f"\n⏹️  Dừng sau {max_moves} nước đi.")

    # ── Thống kê ──────────────────────────────────────────────────────────
    total_time   = time.time() - game_start
    avg_time     = sum(move_times) / len(move_times) if move_times else 0
    slowest_idx  = move_times.index(max(move_times)) + 1 if move_times else 0
    fastest_idx  = move_times.index(min(move_times)) + 1 if move_times else 0
    total_nodes  = sum(node_counts)
    avg_nodes    = total_nodes // len(node_counts) if node_counts else 0

    

    stats = {
        "result"            : result,
        "total_moves"       : len(move_times),
        "total_time"        : total_time,
        "avg_time"          : avg_time,
        "slowest_time"      : max(move_times) if move_times else 0,
        "slowest_move"      : slowest_idx,
        "fastest_time"      : min(move_times) if move_times else 0,
        "fastest_move"      : fastest_idx,
        "total_nodes"       : total_nodes,
        "avg_nodes"         : avg_nodes,
        "white"             : white_player.label,
        "black"             : black_player.label,
    }

    if verbose:
        _print_stats(stats)

    # ── Xuất PGN ──────────────────────────────────────────────────────────
    _write_pgn(pgn_file, moves_pgn, result,
               white_player.label, black_player.label)
    if verbose:
        print(f"\n📁 Đã lưu file PGN: {pgn_file}")

    return stats


def _print_stats(stats):
    def fmt_score(s):
        return f"{s:+d}" if s is not None else "N/A (MCTS)"

    print("\n" + "="*55)
    print("📊 THỐNG KÊ VÁN CỜ")
    print("="*55)
    print(f"  Trắng              : {stats['white']}")
    print(f"  Đen                : {stats['black']}")
    print(f"  Kết quả            : {stats['result']}")
    print(f"  Tổng số nước       : {stats['total_moves']}")
    print(f"  Tổng thời gian     : {stats['total_time']:.2f}s")
    print(f"  TB mỗi nước        : {stats['avg_time']:.3f}s")
    print(f"  Nước chậm nhất     : {stats['slowest_time']:.3f}s (lượt {stats['slowest_move']})")
    print(f"  Nước nhanh nhất    : {stats['fastest_time']:.3f}s (lượt {stats['fastest_move']})")
    print(f"  Tổng nodes         : {stats['total_nodes']:,}")
    print(f"  TB nodes/nước      : {stats['avg_nodes']:,}")
    print("="*55)


def _write_pgn(pgn_file, moves_pgn, result, white_label, black_label):
    with open(pgn_file, "w") as f:
        f.write('[Event "AI vs AI"]\n')
        f.write('[Site "Local"]\n')
        f.write(f'[Date "{time.strftime("%Y.%m.%d")}"]\n')
        f.write(f'[White "{white_label}"]\n')
        f.write(f'[Black "{black_label}"]\n')
        f.write(f'[Result "{result}"]\n\n')

        line = ""
        for i, move in enumerate(moves_pgn):
            token = f"{i // 2 + 1}. {move}" if i % 2 == 0 else move
            if len(line) + len(token) + 1 > 80:
                f.write(line.rstrip() + "\n")
                line = token + " "
            else:
                line += token + " "
        f.write(line.rstrip() + " " + result + "\n")


# ─── Các chế độ chơi ───────────────────────────────────────────────────────

def alphabeta_vs_alphabeta(depth_white=3, depth_black=3,
                           max_moves=200, pgn_file="ab_vs_ab.pgn"):
    board  = Board()
    white  = AlphaBetaPlayer(board, depth=depth_white)
    black  = AlphaBetaPlayer(board, depth=depth_black)
    return play_game(white, black, board, max_moves, pgn_file)


def mcts_vs_mcts(iter_white=300, iter_black=300,
                 rollout_white=20, rollout_black=20,
                 max_moves=200, pgn_file="mcts_vs_mcts.pgn"):
    board  = Board()
    white  = MCTSPlayer(board, iterations=iter_white,  rollout_depth=rollout_white)
    black  = MCTSPlayer(board, iterations=iter_black,  rollout_depth=rollout_black)
    return play_game(white, black, board, max_moves, pgn_file)


def alphabeta_vs_mcts(depth=3, iterations=300, rollout_depth=20,
                      max_moves=200, pgn_file="ab_vs_mcts.pgn"):
    """AlphaBeta (Trắng) vs MCTS (Đen)."""
    board  = Board()
    white  = AlphaBetaPlayer(board, depth=depth)
    black  = MCTSPlayer(board, iterations=iterations, rollout_depth=rollout_depth)
    return play_game(white, black, board, max_moves, pgn_file)


def mcts_vs_alphabeta(iterations=300, depth=3, rollout_depth=20,
                      max_moves=200, pgn_file="mcts_vs_ab.pgn"):
    """MCTS (Trắng) vs AlphaBeta (Đen)."""
    board  = Board()
    white  = MCTSPlayer(board, iterations=iterations, rollout_depth=rollout_depth)
    black  = AlphaBetaPlayer(board, depth=depth)
    return play_game(white, black, board, max_moves, pgn_file)


# ─── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Chọn chế độ chơi:")
    print("  1. AlphaBeta vs AlphaBeta")
    print("  2. MCTS vs MCTS")
    print("  3. AlphaBeta vs MCTS")
    print("  4. MCTS vs AlphaBeta")
    choice = input("Nhập lựa chọn (1-4): ").strip()

    if choice == "1":
        alphabeta_vs_alphabeta(depth_white=2, depth_black=4)
    elif choice == "2":
        mcts_vs_mcts(iter_white=150, iter_black=150)
    elif choice == "3":
        alphabeta_vs_mcts(depth=3, iterations=50)
    elif choice == "4":
        mcts_vs_alphabeta(iterations=50, depth=3)
    else:
        print("Lựa chọn không hợp lệ.")
