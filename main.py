from src.menu.menu import get_config
from src.chess_replicated.ui import UI
from src.chess_replicated.evaluator import*

def main():
    while True:
        board, algorithm, depth, mcts_iterations = get_config()

    
        ui = UI(board, algorithm, depth, mcts_iterations)

        next_action = ui.run()

        if next_action == "menu":
            continue
        else:
            break

if __name__ == "__main__":
    main()
    