import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../public/script.js", import.meta.url), "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const { indexToSquare, makeGamePayload, squareToIndex } = await import(moduleUrl);

// Verify the client uses the same square indexing as the Python board.
assert.equal(squareToIndex("a8"), 0);
assert.equal(squareToIndex("e2"), 52);
assert.equal(squareToIndex("h1"), 63);
assert.equal(indexToSquare(0), "a8");
assert.equal(indexToSquare(52), "e2");
assert.equal(indexToSquare(63), "h1");

// Verify each request gets the exact start and complete move history.
const moves = [{ from: "e2", to: "e4" }];
const payload = makeGamePayload({ type: "standard" }, moves);
assert.deepEqual(payload, { start_position: { type: "standard" }, moves });
assert.notEqual(payload.moves, moves);

console.log("Web logic tests passed.");
