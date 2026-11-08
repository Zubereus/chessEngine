from src.chess_replicated.enum_chess import PieceType, Team


class Evaluator:
    VALUES = {
        "pawn": 100,
        "knight": 320,
        "bishop": 330,
        "rook": 500,
        "queen": 900,
        "king": 20000,
    }

    @staticmethod
    def _piece_type_name(piece):
        mapping = {
            PieceType.PAWN: "pawn",
            PieceType.KNIGHT: "knight",
            PieceType.BISHOP: "bishop",
            PieceType.ROOK: "rook",
            PieceType.QUEEN: "queen",
            PieceType.KING: "king",
        }
        return mapping.get(piece.getPieceType(), "pawn")

    @staticmethod
    def _piece_color_name(piece):
        return "white" if piece.getTeam() == Team.WHITE else "black"

    @staticmethod
    def _piece_pos(piece):
        pos = piece.getPosition()
        return pos // 8, pos % 8

    @staticmethod
    def _collect_team_pieces(board, team):
        pieces = []
        for square in board.game_board:
            if square.isEmpty():
                continue
            piece = square.getPiece()
            if piece.getTeam() == team:
                pieces.append(piece)
        return pieces

    @staticmethod
    def _find_king(pieces):
        for piece in pieces:
            if piece.getPieceType() == PieceType.KING:
                return piece
        return None

    @staticmethod
    def evaluate_dynamic(board, color):
        whitePieces = Evaluator._collect_team_pieces(board, Team.WHITE)
        blackPieces = Evaluator._collect_team_pieces(board, Team.BLACK)
        whiteKing = Evaluator._find_king(whitePieces)
        blackKing = Evaluator._find_king(blackPieces)

        if board.isEndGameScenario():
            # Nếu mất Vua
            if whiteKing is None:
                return -999999 if color == "white" else 999999
            if blackKing is None:
                return -999999 if color == "black" else 999999
            # Nếu hết nước đi
            if not board.kingIsSafe():
                board_turn = "white" if board.turn == Team.WHITE else "black"
                return -999999 if color == board_turn else 999999
            return 0

        if Evaluator._is_insufficient_material(whitePieces, blackPieces):
            return 0

        # Special case: Tàn cuộc chỉ còn xe và vua, dùng kỹ thuật dồn vua vào góc
        if Evaluator._is_rook_endgame(whitePieces, blackPieces):
            return Evaluator._evaluate_rook_endgame(whitePieces, blackPieces, whiteKing, blackKing, color)

        white_score = sum(Evaluator._get_piece_val(p, 8, board, whitePieces, blackPieces) for p in whitePieces)
        black_score = sum(Evaluator._get_piece_val(p, 8, board, whitePieces, blackPieces) for p in blackPieces)

        # Thưởng cho bên đang chiếu vua đối phương (tạo áp lực trực tiếp)
        check_bonus = Evaluator._evaluate_check_pressure(board, color)

        # Mop-up bonus: khi một bên chỉ còn vua, bên còn quân được thưởng
        # nếu biết dồn vua đối phương vào biên/góc và áp sát để kết thúc ván.
        mop_up_bonus = Evaluator._evaluate_mop_up_endgame(whitePieces, blackPieces, whiteKing, blackKing)

        total = (white_score - black_score) + check_bonus + mop_up_bonus
        return total if color == "white" else -total

    @staticmethod
    def _is_insufficient_material(whitePieces, blackPieces):
        pieces = whitePieces + blackPieces
        if any(
            Evaluator._piece_type_name(piece) in ("pawn", "rook", "queen")
            for piece in pieces
        ):
            return False

        bishops = [
            piece
            for piece in pieces
            if Evaluator._piece_type_name(piece) == "bishop"
        ]
        knights = [
            piece
            for piece in pieces
            if Evaluator._piece_type_name(piece) == "knight"
        ]
        if len(bishops) + len(knights) <= 1:
            return True
        if not knights and bishops:
            return len(
                {
                    sum(Evaluator._piece_pos(piece)) % 2
                    for piece in bishops
                }
            ) == 1
        return False

    @staticmethod
    def _evaluate_mop_up_endgame(whitePieces, blackPieces, whiteKing, blackKing):
        """Return bonus from White perspective for king-only endgame conversion."""
        if whiteKing is None or blackKing is None:
            return 0

        white_count = len(whitePieces)
        black_count = len(blackPieces)

        # Chỉ bật logic khi đúng mẫu: một bên chỉ còn vua, bên kia có thêm quân.
        white_has_extra = white_count > 1
        black_has_extra = black_count > 1
        if not ((white_count == 1 and black_has_extra) or (black_count == 1 and white_has_extra)):
            return 0

        size = 8
        max_edge_dist = (size - 1) // 2
        max_king_dist = 2 * (size - 1)

        def edge_distance(pos):
            r, c = pos
            return min(r, c, size - 1 - r, size - 1 - c)

        def manhattan(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        score = 0

        # White đang thắng, Black chỉ còn vua
        if white_has_extra and black_count == 1:
            enemy_king_pos = Evaluator._piece_pos(blackKing)
            our_king_pos = Evaluator._piece_pos(whiteKing)
            attackers = [p for p in whitePieces if Evaluator._piece_type_name(p) != "king"]

            # Dồn vua địch ra biên/góc
            enemy_edge = edge_distance(enemy_king_pos)
            score += (max_edge_dist - enemy_edge) * 35

            # Vua ta tiến lại gần vua địch
            king_dist = manhattan(our_king_pos, enemy_king_pos)
            score += (max_king_dist - king_dist) * 8

            # Quân tấn công gần vua địch giúp tạo lưới chiếu hết nhanh hơn
            if attackers:
                min_attacker_dist = min(manhattan(Evaluator._piece_pos(p), enemy_king_pos) for p in attackers)
                score += (max_king_dist - min_attacker_dist) * 6

        # Black đang thắng, White chỉ còn vua
        elif black_has_extra and white_count == 1:
            enemy_king_pos = Evaluator._piece_pos(whiteKing)
            our_king_pos = Evaluator._piece_pos(blackKing)
            attackers = [p for p in blackPieces if Evaluator._piece_type_name(p) != "king"]

            enemy_edge = edge_distance(enemy_king_pos)
            score -= (max_edge_dist - enemy_edge) * 35

            king_dist = manhattan(our_king_pos, enemy_king_pos)
            score -= (max_king_dist - king_dist) * 8

            if attackers:
                min_attacker_dist = min(manhattan(Evaluator._piece_pos(p), enemy_king_pos) for p in attackers)
                score -= (max_king_dist - min_attacker_dist) * 6

        return score

    @staticmethod
    def _is_rook_endgame(whitePieces, blackPieces):
        """Kiểm tra có phải tàn cuộc chỉ còn xe và vua không"""
        white_rooks = [
            piece for piece in whitePieces
            if Evaluator._piece_type_name(piece) == "rook"
        ]
        black_rooks = [
            piece for piece in blackPieces
            if Evaluator._piece_type_name(piece) == "rook"
        ]
        if white_rooks and not black_rooks:
            return (
                len(blackPieces) == 1
                and all(
                    Evaluator._piece_type_name(piece) in ("rook", "king")
                    for piece in whitePieces
                )
            )
        if black_rooks and not white_rooks:
            return (
                len(whitePieces) == 1
                and all(
                    Evaluator._piece_type_name(piece) in ("rook", "king")
                    for piece in blackPieces
                )
            )
        return False

    @staticmethod
    def _evaluate_rook_endgame(whitePieces, blackPieces, whiteKing, blackKing, color):
        """
        Tàn cuộc xe: bên có xe cần dồn vua địch vào góc/cạnh bàn.
        Kỹ thuật chuẩn: dùng xe cắt đường vua, hai vua đối nhau.
        """
        if whiteKing is None or blackKing is None:
            return 0

        size = 8
        wr, wc = Evaluator._piece_pos(whiteKing)
        br, bc = Evaluator._piece_pos(blackKing)

        white_rooks = [p for p in whitePieces if Evaluator._piece_type_name(p) == "rook"]
        black_rooks = [p for p in blackPieces if Evaluator._piece_type_name(p) == "rook"]

        score = 0

        if white_rooks and not black_rooks:
            # Bên trắng có xe: dồn vua đen vào góc
            # Vua địch càng gần cạnh/góc bàn = ta càng gần thắng
            edge_distance = min(br, bc, size - 1 - br, size - 1 - bc)
            score += (4 - edge_distance) * 30

            # Hai vua càng gần nhau càng tốt (vua ta hỗ trợ xe chiếu hết)
            king_dist = abs(wr - br) + abs(wc - bc)
            score += (14 - king_dist) * 10

            # Xe cắt đường vua địch theo hàng hoặc cột
            for rook in white_rooks:
                rr, rc = Evaluator._piece_pos(rook)
                if rr == br:  # Xe cùng hàng với vua địch: cắt đường dọc
                    score += 40
                if rc == bc:  # Xe cùng cột với vua địch: cắt đường ngang
                    score += 40

            return score if color == "white" else -score

        elif black_rooks and not white_rooks:
            # Bên đen có xe: dồn vua trắng vào góc
            edge_distance = min(wr, wc, size - 1 - wr, size - 1 - wc)
            score += (4 - edge_distance) * 30

            king_dist = abs(wr - br) + abs(wc - bc)
            score += (14 - king_dist) * 10

            for rook in black_rooks:
                rr, rc = Evaluator._piece_pos(rook)
                if rr == wr:
                    score += 40
                if rc == wc:
                    score += 40

            return -score if color == "white" else score

        return 0

    @staticmethod
    def _evaluate_check_pressure(board, color):
        """Thưởng nếu ta đang chiếu vua đối phương, phạt nếu vua ta đang bị chiếu"""
        color_to_move = "white" if board.turn == Team.WHITE else "black"
        if board.kingIsSafe():
            return 0
        return 150 if color_to_move != color else -150

    @staticmethod
    def _get_piece_val(piece, size, board=None, whitePieces=None, blackPieces=None):
        r, c = Evaluator._piece_pos(piece)
        piece_type = Evaluator._piece_type_name(piece)
        piece_color = Evaluator._piece_color_name(piece)
        base = Evaluator.VALUES.get(piece_type, 0)
        bonus = 0
        center = (size - 1) / 2

        # 1. Tốt: Ưu tiên tiến lên và giữ trung tâm
        if piece_type == "pawn":
            row_bonus = (size - 1 - r) if piece_color == "white" else r
            bonus += row_bonus * 18
            if abs(c - center) <= 0.5:
                bonus += 20

            # Tốt thông (passed pawn): không có tốt địch chặn đường, rất nguy hiểm
            bonus += Evaluator._passed_pawn_bonus(piece, size, whitePieces, blackPieces)

        # 2. Vua: Ở hàng cuối để an toàn, tránh bị tấn công
        elif piece_type == "king":
            is_back_rank = (r == size - 1 if piece_color == "white" else r == 0)
            if is_back_rank:
                bonus += 30

            # Phạt vua ra giữa bàn khi còn nhiều quân (nguy hiểm)
            if whitePieces is not None and blackPieces is not None:
                enemy_pieces = blackPieces if piece_color == "white" else whitePieces
                if len(enemy_pieces) > 3:
                    dist_to_center = abs(r - center) + abs(c - center)
                    bonus += dist_to_center * 8  # Vua càng xa trung tâm càng an toàn

        # 3. Các quân khác: Ưu tiên chiếm trung tâm để tăng tầm hoạt động
        else:
            dist_to_center = abs(r - center) + abs(c - center)
            bonus += (size - dist_to_center) * 8

            # 4. Phát triển quân: thưởng cho mã/tượng không ở hàng xuất phát
            if piece_type in ("knight", "bishop"):
                start_row = size - 1 if piece_color == "white" else 0
                if r != start_row:
                    bonus += 25

        # 5. Mobility + tấn công tích cực (tách biệt ô tấn công và ô di chuyển thường)
        if board is not None and piece_type != "pawn":
            legal_moves = piece.generatePossibleMove(board)
            attacker_value = Evaluator.VALUES.get(piece_type, 0)
            attack_count = 0
            attack_bonus = 0

            for move in legal_moves:
                target_piece = board.getSquare(move.getEndPos()).getPiece()
                if target_piece is None or target_piece.getTeam() == piece.getTeam():
                    continue
                attack_count += 1
                capture_value = Evaluator.VALUES.get(
                    Evaluator._piece_type_name(target_piece), 0
                )
                trade_quality = capture_value - attacker_value
                if trade_quality > 0:
                    attack_bonus += 40 + trade_quality // 10
                elif trade_quality == 0:
                    attack_bonus += 15

            non_attack_moves = len(legal_moves) - attack_count
            bonus += non_attack_moves * 6 + attack_bonus

        return base + bonus

    @staticmethod
    def _passed_pawn_bonus(piece, size, whitePieces, blackPieces):
        """
        Tốt thông: không có tốt địch nào chặn trên cùng cột hoặc cột kề.
        Tốt thông rất nguy hiểm vì có thể phong cấp tự do.
        """
        if whitePieces is None or blackPieces is None:
            return 0

        bonus = 0
        r, c = Evaluator._piece_pos(piece)
        piece_color = Evaluator._piece_color_name(piece)
        enemy_pool = blackPieces if piece_color == "white" else whitePieces
        enemy_pawns = [p for p in enemy_pool if Evaluator._piece_type_name(p) == "pawn"]

        # Kiểm tra các cột kề và cùng cột xem có tốt địch chặn không
        is_passed = True
        for ep in enemy_pawns:
            er, ec = Evaluator._piece_pos(ep)
            if abs(ec - c) <= 1:  # cùng cột hoặc cột kề
                # Tốt địch ở phía trước (theo hướng tiến của ta)
                if piece_color == "white" and er < r:
                    is_passed = False
                    break
                if piece_color == "black" and er > r:
                    is_passed = False
                    break

        if is_passed:
            # Thưởng lớn hơn khi tốt càng gần phong cấp
            advance = (size - 1 - r) if piece_color == "white" else r
            bonus += 30 + advance * 15  # Tốt càng tiến xa càng nguy hiểm

        return bonus

    @staticmethod
    def get_piece_value(piece):
        if piece is None:
            return 0
        return Evaluator.VALUES.get(Evaluator._piece_type_name(piece), 0)


# For MCTS

def simple_evaluate(board, color):
    """Fast material/position score from the requested side's perspective."""
    values = Evaluator.VALUES
    pieces = [
        square.getPiece()
        for square in board.game_board
        if not square.isEmpty()
    ]
    white_pieces = [
        piece for piece in pieces if piece.getTeam() == Team.WHITE
    ]
    black_pieces = [
        piece for piece in pieces if piece.getTeam() == Team.BLACK
    ]
    if (
        Evaluator._find_king(white_pieces) is not None
        and Evaluator._find_king(black_pieces) is not None
        and Evaluator._is_insufficient_material(white_pieces, black_pieces)
    ):
        return 0

    piece_count = len(pieces)
    pawns_by_team = {
        Team.WHITE: [],
        Team.BLACK: [],
    }
    bishops_by_team = {
        Team.WHITE: 0,
        Team.BLACK: 0,
    }
    pawn_files = {
        Team.WHITE: [0] * 8,
        Team.BLACK: [0] * 8,
    }
    for piece in pieces:
        piece_type = piece.getPieceType()
        if piece_type == PieceType.PAWN:
            pawns_by_team[piece.getTeam()].append(piece)
            pawn_files[piece.getTeam()][piece.getPosition() % 8] += 1
        elif piece_type == PieceType.BISHOP:
            bishops_by_team[piece.getTeam()] += 1

    score = (
        30 * (bishops_by_team[Team.WHITE] >= 2)
        - 30 * (bishops_by_team[Team.BLACK] >= 2)
    )
    for team in (Team.WHITE, Team.BLACK):
        sign = 1 if team == Team.WHITE else -1
        score -= sign * sum(
            12 * (file_count - 1)
            for file_count in pawn_files[team]
            if file_count > 1
        )
        for pawn in pawns_by_team[team]:
            pawn_col = pawn.getPosition() % 8
            if not any(
                abs(other_pawn.getPosition() % 8 - pawn_col) == 1
                for other_pawn in pawns_by_team[team]
            ):
                score -= sign * 10

    for piece in pieces:
        piece_type = piece.getPieceType()
        piece_name = Evaluator._piece_type_name(piece)
        team = piece.getTeam()
        row, col = Evaluator._piece_pos(piece)
        relative_row = row if team == Team.BLACK else 7 - row
        center_distance = abs(3.5 - row) + abs(3.5 - col)
        positional = 0
        if piece_name == "pawn":
            positional = relative_row * 8 + int(col in (3, 4)) * 8
            enemy_team = Team.BLACK if team == Team.WHITE else Team.WHITE
            passed = not any(
                abs(Evaluator._piece_pos(enemy_pawn)[1] - col) <= 1
                and (
                    Evaluator._piece_pos(enemy_pawn)[0] < row
                    if team == Team.WHITE
                    else Evaluator._piece_pos(enemy_pawn)[0] > row
                )
                for enemy_pawn in pawns_by_team[enemy_team]
            )
            if passed:
                positional += 20 + relative_row * 8

        elif piece_name in ("knight", "bishop", "queen"):
            positional = int((7 - center_distance) * 5)
        elif piece_name == "rook":
            friendly_pawns = pawn_files[team][col]
            opponent = Team.BLACK if team == Team.WHITE else Team.WHITE
            opponent_pawns = pawn_files[opponent][col]
            if friendly_pawns == 0:
                positional += 14 if opponent_pawns == 0 else 8
        elif piece_name == "king":
            if piece_count > 12:
                positional = int(center_distance * 4)
            else:
                positional = int((7 - center_distance) * 4)

        sign = 1 if team == Team.WHITE else -1
        score += sign * (values[piece_name] + positional)

    return score if color == Team.WHITE else -score