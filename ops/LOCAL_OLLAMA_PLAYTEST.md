# Model-led AI gameplay: local Ollama acceptance trial

This is the next step after `ops/headless_ai_client.py` proved that two
authenticated, disclosed AI accounts could independently traverse the
ten-room map. The headless client follows deterministic rules. **This
playtest lets an actual local language model choose what to do**, without
giving it privileged game access.

It is a manually launched research probe, **not a background service**,
continuous companion, production bot account, full hosting certification,
or evidence that the model makes satisfying narrative decisions.

## Requirements

- Existing Frankenstein Village Evennia world on loopback, or approved remote
  host with certificate-verified TLS.
- A separately controlled ordinary player account. Its disclosure compact
  and room-selection flow follow the same rules as human players.
- Locally running Ollama at `http://127.0.0.1:11434/api/chat` with a model
  installed. The model endpoint is deliberately restricted to loopback;
  world scenes are never sent to a paid/remote inference API.
- Python 3.12 and the standard-library tools in `ops/`.
- A one-entry private JSON manifest outside Git, for example
  `/private/ai-playtest.json`:

```json
[
  {
    "username": "qa_explorer",
    "character": "Explorer",
    "password_env": "FV_AI_PLAYTEST_PASSWORD"
  }
]
```

Set `FV_AI_PLAYTEST_PASSWORD` in the process environment securely. Do not
commit the manifest, use a production administrator, paste credentials in
chat, or embed passwords in scripts.

## Local session

```sh
python ops/local_ollama_playtest.py \
  --host 127.0.0.1 --port 4000 \
  --accounts /private/ai-playtest.json \
  --model qwen3:8b --steps 12 \
  --output /private/ai-playtest-run.json
```

Replace the example model with one installed locally. The model controls
one ordinary in-character player, not the server or NPCs. The process
performs an ordinary login, enters through the front door, reads `look`
and the public `agent` observation for each turn, offers only commands
actually available from that observation and validates the model's chosen
literal command before transmitting it. The model can inspect nearby
visible objects, speak to observed people, explore connected exits and
choose surfaced public activities. Deliberately, there is **no freeform
command executor**, hidden full map, direct memory DB, shell tool, Python
eval, staff access or automatic passage across OOC/IC gates.

The prompt only uses bounded, ordinary player-visible text. Even if a room
description contains `admin shutdown` or a malicious instruction, the
choice must exactly match an allowed command. The Ollama client refuses
HTTP redirects and remote model endpoints. No player passwords or
narrative transcripts appear in the summary JSON.

The output includes commands accepted, rejected model decisions, rooms
visited, response receipt and elapsed wall-clock duration. A rejection
fails the protocol result but does not silently execute the prohibited
command. These are **observations**, not an assertion of humanlike
motivation, autonomy quality, success at mysteries or playtest enjoyment.

## What remains before accepting AI playability

Run several independent local-model trials with distinct accounts, then
conduct uncoached tests across a fresh login, first 30 minutes, disconnect,
D1 and D7 return. Score whether each model finds meaningful activity,
stays within the roleplay compact, can recover after a mistaken action,
interacts with other real people and uses persistent memory. Document
failures instead of turning scripts into claimed autonomy evidence.

External TLS authentication, production environment, privacy review,
network load, moderation, rollback and off-host backup/restore are separate
release gates. This optional local trial cannot pass them.
