# Chess API request format

The API keeps no game state between requests. Send `start_position` and the full
`moves` list to `legal-moves` and `ai-move`; moves are replayed from a fresh board
and rejected with HTTP 400 if any one is illegal.

Use this standard start description:

```json
{"type": "standard"}
```

Custom starts use the actual piece placement rather than piece counts. The desktop
menu chooses counts and then places pieces randomly, so sending the resulting
squares makes that custom start reproducible. Each piece's `first_move` value
preserves castling rights. Pieces must have exactly one king per color and pawns
cannot start on the first or eighth rank.

```json
{
  "type": "custom",
  "turn": "white",
  "pieces": [
    {"type": "king", "color": "white", "square": "e1", "first_move": true},
    {"type": "king", "color": "black", "square": "e8", "first_move": true},
    {"type": "rook", "color": "white", "square": "h1", "first_move": true},
    {"type": "rook", "color": "black", "square": "h8", "first_move": true}
  ]
}
```

Moves are sent in order, for example `{"from":"e2","to":"e4"}`. A promotion
must include `"promotion":"Q"`, `"R"`, `"B"`, or `"N"`. Example request:

```json
{
  "start_position": {"type": "standard"},
  "moves": [{"from": "e2", "to": "e4"}, {"from": "e7", "to": "e5"}]
}
```

`new-game` accepts an optional `start_position` and returns it with an empty move
list and legal moves. Its default is the standard board. API responses use
`evaluation` in centipawns from White's point of view. The AI search result also
includes its completed depth or iteration count, work count, and elapsed seconds.
