import unittest

from api import api_response

STANDARD_START = {"type": "standard"}


class ChessApiTests(unittest.TestCase):
    def test_health(self):
        status, result = api_response("health")
        self.assertEqual(status, 200)
        self.assertEqual(result, {"status": "ok"})

    def test_new_game_returns_standard_start_and_legal_moves(self):
        status, result = api_response("new-game", {})
        self.assertEqual(status, 200)
        self.assertEqual(result["start_position"], {"type": "standard"})
        self.assertEqual(len(result["legal_moves"]), 20)

    def test_legal_moves_from_standard_start_has_twenty_moves(self):
        status, result = api_response(
            "legal-moves", {"start_position": STANDARD_START, "moves": []}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(result["legal_moves"]), 20)

    def test_legal_moves_replays_a_move(self):
        status, result = api_response(
            "legal-moves", {
                "start_position": STANDARD_START,
                "moves": [{"from": "e2", "to": "e4"}],
            }
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["moves"], [{"from": "e2", "to": "e4"}])
        self.assertEqual(len(result["legal_moves"]), 20)

    def test_illegal_move_is_rejected(self):
        status, result = api_response(
            "legal-moves", {
                "start_position": STANDARD_START,
                "moves": [{"from": "e2", "to": "e5"}],
            }
        )
        self.assertEqual(status, 400)
        self.assertIn("Illegal move", result["error"])

    def test_alpha_beta_returns_a_move_at_depth_two(self):
        status, result = api_response(
            "ai-move", {
                "start_position": STANDARD_START,
                "moves": [],
                "algorithm": "alphabeta",
                "depth": 2,
            }
        )
        self.assertEqual(status, 200)
        self.assertRegex(result["move"]["from"], r"^[a-h][1-8]$")
        self.assertEqual(result["depth_completed"], 2)
        self.assertGreater(result["node_count"], 0)

    def test_mcts_returns_a_move_at_depth_two_equivalent_work(self):
        status, result = api_response(
            "ai-move", {
                "start_position": STANDARD_START,
                "moves": [],
                "algorithm": "mcts",
                "mcts_iterations": 2,
            }
        )
        self.assertEqual(status, 200)
        self.assertRegex(result["move"]["from"], r"^[a-h][1-8]$")
        self.assertEqual(result["iteration_count"], 2)


if __name__ == "__main__":
    unittest.main()
