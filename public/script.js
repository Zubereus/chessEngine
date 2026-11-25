const FILES = "abcdefgh";
const PROMOTION_TYPES = [
  { code: "Q", name: "queen" },
  { code: "R", name: "rook" },
  { code: "B", name: "bishop" },
  { code: "N", name: "knight" },
];
const PIECE_NAMES = { p: "pawn", n: "knight", b: "bishop", r: "rook", q: "queen", k: "king" };
const MAX_DEPTH = 8;
const MAX_MCTS_ITERATIONS = 500;

// Convert an algebraic square to the engine's row-major board index.
export function squareToIndex(square) {
  return (8 - Number(square[1])) * 8 + FILES.indexOf(square[0]);
}

// Convert a row-major board index to algebraic notation.
export function indexToSquare(index) {
  return FILES[index % 8] + String(8 - Math.floor(index / 8));
}

// Build the full replay payload required by every stateless game endpoint.
export function makeGamePayload(startPosition, moves) {
  return { start_position: startPosition, moves: [...moves] };
}

// Start the page only in a browser, leaving the pure helpers importable in Node.
if (typeof document !== "undefined") {
  initializePage();
}

// Bind the page controls and create the one client-owned game state object.
function initializePage() {
  const elements = getElements();
  const gameState = {
    startPosition: { type: "standard" },
    moves: [],
    legalMoves: [],
    game: { status: "ongoing", draw_reason: null },
    mode: "human",
    algorithms: { white: "alphabeta", black: "alphabeta" },
    depth: 2,
    iterations: 100,
    selectedSquare: null,
    pendingPromotion: null,
    lastAi: null,
    auto: false,
    loading: false,
    aiPaused: false,
    error: "",
    retryTask: null,
    started: false,
  };

  bindEvents(gameState, elements);
  updateSetupVisibility(elements);
  render(gameState, elements);
}

// Collect the page elements once so rendering functions receive a clear view of the UI.
function getElements() {
  return {
    setupScreen: document.querySelector("#setup-screen"),
    setupForm: document.querySelector("#setup-form"),
    gameMode: document.querySelector("#game-mode"),
    humanAlgorithm: document.querySelector("#human-algorithm"),
    whiteAlgorithm: document.querySelector("#white-algorithm"),
    blackAlgorithm: document.querySelector("#black-algorithm"),
    depthInput: document.querySelector("#search-depth"),
    iterationInput: document.querySelector("#mcts-iterations"),
    humanAlgorithmField: document.querySelector("#human-algorithm-field"),
    aiAlgorithms: document.querySelector("#ai-algorithms"),
    gameScreen: document.querySelector("#game-screen"),
    board: document.querySelector("#chess-board"),
    boardWrap: document.querySelector("#board-wrap"),
    turnIndicator: document.querySelector("#turn-indicator"),
    gameStatus: document.querySelector("#game-status"),
    loading: document.querySelector("#loading-indicator"),
    loadingMessage: document.querySelector("#loading-message"),
    error: document.querySelector("#error-message"),
    errorText: document.querySelector("#error-text"),
    retry: document.querySelector("#retry-button"),
    setupError: document.querySelector("#setup-error-message"),
    setupErrorText: document.querySelector("#setup-error-text"),
    setupRetry: document.querySelector("#setup-retry-button"),
    modeSummary: document.querySelector("#mode-summary"),
    algorithmSummary: document.querySelector("#algorithm-summary"),
    humanControls: document.querySelector("#human-controls"),
    aiControls: document.querySelector("#ai-controls"),
    humanRunAi: document.querySelector("#human-run-ai"),
    runAi: document.querySelector("#run-ai-button"),
    auto: document.querySelector("#auto-button"),
    undo: document.querySelector("#undo-button"),
    lastAi: document.querySelector("#last-ai-result"),
    newGame: document.querySelector("#new-game-button"),
    back: document.querySelector("#back-button"),
    promotion: document.querySelector("#promotion-picker"),
    promotionOptions: document.querySelector("#promotion-options"),
    cancelPromotion: document.querySelector("#cancel-promotion"),
  };
}

// Attach keyboard-accessible form and board actions to the page.
function bindEvents(state, elements) {
  // Refresh the setup fields after switching the game mode.
  elements.gameMode.addEventListener("change", () => updateSetupVisibility(elements));
  // Validate and submit the setup values when the form is sent.
  elements.setupForm.addEventListener("submit", (event) => {
    event.preventDefault();
    startGameFromForm(state, elements);
  });
  // Pass board clicks to the current move-selection rules.
  elements.board.addEventListener("click", (event) => handleBoardClick(event, state, elements));
  // Retry failed requests from either error panel.
  elements.retry.addEventListener("click", () => retryLastRequest(state, elements));
  elements.setupRetry.addEventListener("click", () => retryLastRequest(state, elements));
  // Let a paused human game or AI game advance one turn.
  elements.humanRunAi.addEventListener("click", () => runAiTurn(state, elements));
  elements.runAi.addEventListener("click", () => runAiTurn(state, elements));
  // Toggle the AI-versus-AI autoplay loop.
  elements.auto.addEventListener("click", () => toggleAutoPlay(state, elements));
  // Attach navigation, undo, and promotion picker actions.
  elements.undo.addEventListener("click", () => undoLastTurn(state, elements));
  elements.newGame.addEventListener("click", () => startNewGame(state, elements));
  elements.back.addEventListener("click", () => showSetup(state, elements));
  elements.cancelPromotion.addEventListener("click", () => closePromotionPicker(state, elements));
  elements.promotionOptions.addEventListener("click", (event) => choosePromotion(event, state, elements));
}

// Show the algorithm fields that match the selected game mode.
function updateSetupVisibility(elements) {
  const isAiGame = elements.gameMode.value === "ai";
  elements.humanAlgorithmField.hidden = isAiGame;
  elements.aiAlgorithms.hidden = !isAiGame;
}

// Read and validate all setup inputs before starting a game.
function readSettings(state, elements) {
  const depth = Number(elements.depthInput.value);
  const iterations = Number(elements.iterationInput.value);
  if (!Number.isInteger(depth) || depth < 1 || depth > MAX_DEPTH) {
    elements.depthInput.setCustomValidity(`Enter a depth from 1 to ${MAX_DEPTH}.`);
    elements.depthInput.reportValidity();
    return false;
  }
  elements.depthInput.setCustomValidity("");
  if (!Number.isInteger(iterations) || iterations < 1 || iterations > MAX_MCTS_ITERATIONS) {
    elements.iterationInput.setCustomValidity(`Enter between 1 and ${MAX_MCTS_ITERATIONS} iterations.`);
    elements.iterationInput.reportValidity();
    return false;
  }
  elements.iterationInput.setCustomValidity("");
  state.mode = elements.gameMode.value;
  state.depth = depth;
  state.iterations = iterations;
  state.algorithms = state.mode === "human"
    ? { white: "human", black: elements.humanAlgorithm.value }
    : { white: elements.whiteAlgorithm.value, black: elements.blackAlgorithm.value };
  return true;
}

// Start a new standard game after setup values pass the API limits.
async function startGameFromForm(state, elements) {
  if (!readSettings(state, elements)) return;
  await startNewGame(state, elements);
}

// Fetch the new-game response before replacing an existing game.
async function startNewGame(state, elements) {
  const previous = {
    startPosition: state.startPosition,
    moves: state.moves,
  };
  state.loading = true;
  state.error = "";
  state.retryTask = "new-game";
  state.auto = false;
  render(state, elements);
  try {
    const result = await postJson("/api/new-game", { start_position: { type: "standard" } });
    state.startPosition = result.start_position;
    state.moves = result.moves;
    state.legalMoves = result.legal_moves;
    state.game = result.game;
    state.selectedSquare = null;
    state.pendingPromotion = null;
    state.lastAi = null;
    state.aiPaused = false;
    state.started = true;
    state.retryTask = null;
    elements.setupScreen.hidden = true;
    elements.gameScreen.hidden = false;
  } catch (error) {
    state.startPosition = previous.startPosition;
    state.moves = previous.moves;
    setApiError(state, error, "new-game");
  } finally {
    state.loading = false;
    render(state, elements);
  }
}

// Send JSON to the same-project API and preserve its clear error message.
async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  let result;
  try {
    result = await response.json();
  } catch {
    throw new Error("The server returned an unreadable response. Try again.");
  }
  if (!response.ok) throw new Error(result.error || `The request failed (${response.status}).`);
  return result;
}

// Refresh legal moves and status using the complete client-owned move history.
async function refreshPosition(state, elements) {
  try {
    const result = await postJson("/api/legal-moves", makeGamePayload(state.startPosition, state.moves));
    state.legalMoves = result.legal_moves;
    state.game = result.game;
    state.error = "";
    state.retryTask = null;
    state.aiPaused = false;
    return true;
  } catch (error) {
    setApiError(state, error, "legal-moves");
    return false;
  } finally {
    render(state, elements);
  }
}

// Move the selected human piece, then refresh status and request Black's reply.
async function playHumanMove(state, elements, move) {
  if (state.loading || state.game.status === "checkmate" || state.game.status === "stalemate" || state.game.status === "draw") return;
  state.moves = [...state.moves, move];
  state.selectedSquare = null;
  state.pendingPromotion = null;
  state.loading = true;
  state.error = "";
  state.retryTask = "legal-moves";
  render(state, elements);
  const refreshed = await refreshPosition(state, elements);
  state.loading = false;
  render(state, elements);
  if (refreshed && state.mode === "human" && currentColor(state) === "black" && !isGameOver(state)) {
    await runAiTurn(state, elements);
  }
}

// Ask the selected side's engine for one move using the stateless request format.
async function runAiTurn(state, elements) {
  if (state.loading || !state.started || isGameOver(state)) return false;
  const color = currentColor(state);
  if (state.mode === "human" && color !== "black") return false;
  const algorithm = state.algorithms[color];
  const payload = {
    ...makeGamePayload(state.startPosition, state.moves),
    algorithm,
    depth: state.depth,
    mcts_iterations: state.iterations,
  };
  state.loading = true;
  state.error = "";
  state.aiPaused = false;
  state.retryTask = "ai-move";
  render(state, elements);
  try {
    const result = await postJson("/api/ai-move", payload);
    state.moves = result.moves;
    state.game = result.game;
    state.lastAi = { algorithm, color, ...result };
    state.selectedSquare = null;
    state.retryTask = "legal-moves";
    const refreshed = await refreshPosition(state, elements);
    if (!refreshed) state.aiPaused = true;
    return refreshed;
  } catch (error) {
    setApiError(state, error, "ai-move");
    state.aiPaused = true;
    return false;
  } finally {
    state.loading = false;
    render(state, elements);
  }
}

// Keep asking the engine for moves until Auto is turned off or the game ends.
async function runAutoLoop(state, elements) {
  while (state.auto && !isGameOver(state)) {
    const succeeded = await runAiTurn(state, elements);
    if (!succeeded || !state.auto || isGameOver(state)) break;
    await wait(280);
  }
}

// Pause or resume the AI-versus-AI autoplay loop.
function toggleAutoPlay(state, elements) {
  state.auto = !state.auto;
  render(state, elements);
  if (state.auto) runAutoLoop(state, elements);
}

// Wait briefly between AI turns so autoplay remains readable.
function wait(milliseconds) {
  // Resolve this promise after the requested browser delay.
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

// Retry the last failed request without clearing the current position.
async function retryLastRequest(state, elements) {
  if (state.loading || !state.retryTask) return;
  const task = state.retryTask;
  state.error = "";
  if (task === "new-game") return startNewGame(state, elements);
  if (task === "legal-moves") {
    state.loading = true;
    render(state, elements);
    const refreshed = await refreshPosition(state, elements);
    state.loading = false;
    render(state, elements);
    if (refreshed && state.mode === "human" && currentColor(state) === "black") await runAiTurn(state, elements);
    return;
  }
  await runAiTurn(state, elements);
}

// Store a user-facing error and the request that can be retried.
function setApiError(state, error, task) {
  state.error = error instanceof Error ? error.message : "The request failed. Try again.";
  state.retryTask = task;
}

// Undo one AI-versus-AI move or the last human-and-AI turn.
async function undoLastTurn(state, elements) {
  if (state.loading || !state.moves.length) return;
  state.auto = false;
  const lastMove = state.moves[state.moves.length - 1];
  const moveCount = state.mode === "human" && lastMove.from && currentColor(state) === "white" ? 2 : 1;
  state.moves = state.moves.slice(0, Math.max(0, state.moves.length - moveCount));
  state.lastAi = null;
  state.selectedSquare = null;
  state.loading = true;
  state.retryTask = "legal-moves";
  render(state, elements);
  await refreshPosition(state, elements);
  state.loading = false;
  render(state, elements);
}

// Return the side whose move it is, starting with White on the standard board.
function currentColor(state) {
  return state.moves.length % 2 === 0 ? "white" : "black";
}

// Return whether the server has reported a terminal game state.
function isGameOver(state) {
  return ["checkmate", "stalemate", "draw"].includes(state.game.status);
}

// Handle selection, legal destinations, and promotion choices on the board.
function handleBoardClick(event, state, elements) {
  const squareButton = event.target.closest("button[data-square]");
  if (!squareButton || state.loading || state.mode !== "human" || currentColor(state) !== "white") return;
  const square = squareButton.dataset.square;
  // Keep only legal moves from the selected source to this destination.
  const selectedMoveOptions = state.legalMoves.filter((move) => move.from === state.selectedSquare && move.to === square);
  if (selectedMoveOptions.length > 1) {
    state.pendingPromotion = { from: state.selectedSquare, to: square };
    renderPromotionPicker(state, elements);
    return;
  }
  if (selectedMoveOptions.length === 1) {
    playHumanMove(state, elements, selectedMoveOptions[0]);
    return;
  }

  const board = getDisplayBoard(state);
  const piece = board[squareToIndex(square)];
  const isWhitePiece = typeof piece === "string" && piece === piece.toUpperCase();
  state.selectedSquare = isWhitePiece ? square : null;
  render(state, elements);
}

// Show the four legal piece choices for a pawn promotion.
function renderPromotionPicker(state, elements) {
  // Build one labeled option button for each promotion piece.
  const choices = PROMOTION_TYPES.map((piece) => {
    const image = document.createElement("img");
    image.src = `./img/w_${piece.name}.png`;
    image.alt = "";
    const button = document.createElement("button");
    button.className = "promotion-choice";
    button.type = "button";
    button.dataset.promotion = piece.code;
    button.setAttribute("aria-label", `Promote pawn to ${piece.name}`);
    button.append(image);
    return button;
  });
  elements.promotionOptions.replaceChildren(...choices);
  elements.promotion.hidden = false;
  choices[0].focus();
}

// Apply the selected promotion option and close the picker.
function choosePromotion(event, state, elements) {
  const button = event.target.closest("button[data-promotion]");
  if (!button || !state.pendingPromotion) return;
  const move = { ...state.pendingPromotion, promotion: button.dataset.promotion };
  closePromotionPicker(state, elements);
  playHumanMove(state, elements, move);
}

// Close the promotion picker and return focus to the board.
function closePromotionPicker(state, elements) {
  elements.promotion.hidden = true;
  state.pendingPromotion = null;
  elements.board.querySelector("button[data-square]")?.focus();
}

// Rebuild the visible board from the standard start and the replayed moves.
function getDisplayBoard(state) {
  const board = [
    ..."rnbqkbnr", ...Array(8).fill("p"), ...Array(32).fill(null),
    ...Array(8).fill("P"), ..."RNBQKBNR",
  ];
  for (const move of state.moves) applyDisplayMove(board, move);
  return board;
}

// Apply a legal move to the display-only board, including special chess moves.
function applyDisplayMove(board, move) {
  const from = squareToIndex(move.from);
  const to = squareToIndex(move.to);
  const piece = board[from];
  if (!piece) return;
  const fromRow = Math.floor(from / 8);
  const toRow = Math.floor(to / 8);
  const fromColumn = from % 8;
  const toColumn = to % 8;
  if (piece.toLowerCase() === "p" && fromColumn !== toColumn && board[to] === null) {
    board[to + (fromRow > toRow ? 8 : -8)] = null;
  }
  if (piece.toLowerCase() === "k" && Math.abs(to - from) === 2) {
    const rookFrom = to > from ? from + 3 : from - 4;
    const rookTo = to > from ? from + 1 : from - 1;
    board[rookTo] = board[rookFrom];
    board[rookFrom] = null;
  }
  board[from] = null;
  board[to] = move.promotion ? (piece === piece.toUpperCase() ? move.promotion : move.promotion.toLowerCase()) : piece;
}

// Draw the board, status, controls, and error messages from the current state.
function render(state, elements) {
  renderBoard(state, elements);
  renderStatus(state, elements);
  renderControls(state, elements);
  elements.loading.hidden = !state.loading;
  elements.loadingMessage.textContent = currentColor(state) === "white" ? "Updating the board…" : "The engine is thinking…";
  elements.error.hidden = !state.error;
  elements.errorText.textContent = state.error;
  elements.retry.hidden = !state.retryTask;
  const setupErrorIsVisible = !elements.setupScreen.hidden && Boolean(state.error);
  elements.setupError.hidden = !setupErrorIsVisible;
  elements.setupErrorText.textContent = state.error;
  elements.setupRetry.hidden = !state.retryTask;
  elements.auto.textContent = state.auto ? "Auto: On" : "Auto: Off";
  elements.auto.setAttribute("aria-pressed", String(state.auto));
  elements.undo.disabled = state.loading || state.moves.length === 0;
  renderAiSummary(state, elements);
}

// Render accessible square buttons, piece images, and move highlights.
function renderBoard(state, elements) {
  const board = getDisplayBoard(state);
  const lastMove = state.moves[state.moves.length - 1];
  const lastMoveSquares = lastMove ? [lastMove.from, lastMove.to] : [];
  // Mark unique legal destination squares for the selected piece.
  const destinations = new Set(state.legalMoves.filter((move) => move.from === state.selectedSquare).map((move) => move.to));
  const checkedKing = ["check", "checkmate"].includes(state.game.status)
    ? findKingSquare(board, currentColor(state))
    : null;
  // Build one accessible button for every square in the visible position.
  const squares = board.map((piece, index) => {
    const square = indexToSquare(index);
    const button = document.createElement("button");
    const isLight = (Math.floor(index / 8) + index % 8) % 2 === 1;
    button.className = `square ${isLight ? "light" : "dark"}`;
    button.type = "button";
    button.dataset.square = square;
    button.setAttribute("role", "gridcell");
    const color = piece && piece === piece.toUpperCase() ? "White" : "Black";
    const name = piece ? `${color} ${PIECE_NAMES[piece.toLowerCase()]}` : "empty";
    button.setAttribute("aria-label", `${square}, ${name}`);
    if (piece) {
      const image = document.createElement("img");
      image.src = `./img/${piece === piece.toUpperCase() ? "w" : "b"}_${PIECE_NAMES[piece.toLowerCase()]}.png`;
      image.alt = "";
      button.append(image);
    }
    if (square === state.selectedSquare) button.classList.add("selected");
    if (destinations.has(square)) button.classList.add("legal-target");
    if (lastMoveSquares.includes(square)) button.classList.add("last-move");
    if (square === checkedKing) button.classList.add("in-check");
    button.disabled = state.loading || state.mode !== "human" || currentColor(state) !== "white" || isGameOver(state);
    return button;
  });
  elements.board.replaceChildren(...squares);
  elements.boardWrap.classList.toggle("is-busy", state.loading);
}

// Find the side-to-move king square for the check highlight.
function findKingSquare(board, color) {
  const king = color === "white" ? "K" : "k";
  for (let index = 0; index < board.length; index += 1) {
    if (board[index] === king) return indexToSquare(index);
  }
  return null;
}

// Render the current turn and the server's terminal or check status.
function renderStatus(state, elements) {
  const color = currentColor(state);
  const side = color === "white" ? "White" : "Black";
  const status = state.game.status;
  const messages = {
    ongoing: `${side} to move`,
    check: `${side} to move · Check`,
    checkmate: `Checkmate · ${color === "white" ? "Black" : "White"} wins`,
    stalemate: "Draw · Stalemate",
    draw: `Draw · ${state.game.draw_reason || "draw"}`,
  };
  const isHumanTurn = state.mode === "human" && color === "white";
  elements.turnIndicator.lastElementChild.textContent = isHumanTurn ? "Your move" : `${side} to move`;
  elements.turnIndicator.querySelector(".turn-dot").classList.toggle("black", color === "black");
  elements.gameStatus.textContent = messages[status] || messages.ongoing;
  elements.gameStatus.classList.toggle("terminal", isGameOver(state));
}

// Show the controls that match the selected mode and whether a retry is needed.
function renderControls(state, elements) {
  elements.humanControls.hidden = state.mode !== "human";
  elements.aiControls.hidden = state.mode !== "ai";
  const humanNeedsAi = state.mode === "human" && currentColor(state) === "black" && !isGameOver(state);
  elements.humanRunAi.hidden = !humanNeedsAi || (!state.aiPaused && !state.error);
  elements.humanRunAi.disabled = state.loading;
  elements.runAi.disabled = state.loading || isGameOver(state);
  elements.auto.disabled = isGameOver(state);
  elements.modeSummary.textContent = state.mode === "human" ? "Human vs AI" : "AI vs AI";
  // Format the selected engine for each side in the panel summary.
  const describe = (color) => `${color[0].toUpperCase()}${color.slice(1)} · ${algorithmName(state.algorithms[color])}`;
  elements.algorithmSummary.textContent = state.mode === "human" ? describe("black") : `${describe("white")}  /  ${describe("black")}`;
}

// Format the most recent AI move with the engine work report.
function renderAiSummary(state, elements) {
  if (!state.lastAi) {
    elements.lastAi.textContent = "No AI moves yet.";
    return;
  }
  const result = state.lastAi;
  const work = result.node_count !== undefined
    ? `${result.node_count.toLocaleString()} nodes · depth ${result.depth_completed}`
    : `${result.iteration_count} iterations`;
  elements.lastAi.textContent = `${result.color} · ${algorithmName(result.algorithm)} · ${result.move.from}–${result.move.to} · ${result.evaluation} cp · ${work} · ${result.time_seconds}s`;
}

// Return a readable algorithm label for controls and the result summary.
function algorithmName(algorithm) {
  return algorithm === "mcts" ? "MCTS" : "Alpha-Beta";
}

// Return to setup while preserving the current game in memory.
function showSetup(state, elements) {
  state.auto = false;
  state.selectedSquare = null;
  elements.gameScreen.hidden = true;
  elements.setupScreen.hidden = false;
  elements.gameMode.value = state.mode;
  elements.humanAlgorithm.value = state.algorithms.black === "human" ? "alphabeta" : state.algorithms.black;
  elements.whiteAlgorithm.value = state.algorithms.white === "human" ? "alphabeta" : state.algorithms.white;
  elements.blackAlgorithm.value = state.algorithms.black === "human" ? "alphabeta" : state.algorithms.black;
  elements.depthInput.value = state.depth;
  elements.iterationInput.value = state.iterations;
  updateSetupVisibility(elements);
}
