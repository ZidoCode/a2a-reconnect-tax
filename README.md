# a2a-reconnect-tax

**Measure the token cost of SSE reconnect replays. Dumb math, honest numbers, zero dependencies.**

[![Tests](https://img.shields.io/badge/tests-14%20passed-brightgreen)]() [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)]()

Third in the a2a-tax family: [a2a-tax](https://github.com/ZidoCode/a2a-tax) (the polling tax), [a2a-stream-tax](https://github.com/ZidoCode/a2a-stream-tax) (the streaming tax), and now the **reconnect tax**.

When an A2A `message/stream` connection drops, the client resubscribes — and the server may **replay events the client already received**. Replay semantics are left open in [A2A issue #1635](https://github.com/a2aproject/A2A/issues/1635). Every replayed event is a token billed twice: the client pays for it in the original segment and again in the replayed one. Mobile clients on flaky networks can reconnect a dozen times per task.

Nobody measures the waste. a2a-reconnect-tax does.

## Install

```bash
pip install a2a-reconnect-tax   # or: copy the three .py files
```

## Usage

```bash
$ a2a-reconnect-tax audit stream.jsonl
reconnects            : 1
events_total          : 38
events_replayed       : 4
tokens_replayed       : 238
replay_pct            : 9.7

$ a2a-reconnect-tax report stream.jsonl

  tokens replayed (wasted) :      238 tok  (~$0.0007)
  TOTAL billed             :    2,461 tok
  replay share             :     9.7% of the bill is double-billing

  the fix:
    client: remember Last-Event-ID, discard duplicates on resume (free)
    server: honor Last-Event-ID, replay nothing (protocol)

$ a2a-reconnect-tax simulate https://agent.example.com --drops 3 --stream-len 200
tokens_total          : 18,531
tokens_replayed       : 4,200
replay_pct            : 22.7
```

## Stream format

One JSON event per line (same as [a2a-stream-tax](https://github.com/ZidoCode/a2a-stream-tax)), with a `---` line at each reconnect:

```
{"jsonrpc":"2.0","id":1,"result":{"kind":"status-update",...}}
{"jsonrpc":"2.0","id":1,"result":{"kind":"artifact-update",...}}
---
{"jsonrpc":"2.0","id":1,"result":{"kind":"status-update",...}}   ← replayed?
```

Capture one: run your client, note each reconnect (or just record the whole session and mark `---` where the SSE connection re-opened). Two events count as the same **only if their full semantic payload is identical** — a status event with new text is progress, not waste.

## The fix

1. **Client** — remember the `Last-Event-ID`, discard duplicate events on resume. Costs one line, saves 100% of the replay.
2. **Server** — honor `Last-Event-ID` and replay nothing. Until the spec settles (issue #1635), measure what your agent actually does.

## Honest numbers

Deterministic estimates (`chars/4`), identical output on identical input, no model calls. Prices via `--price-per-mtok` (default $3.00). The point is the **shape**: how much of your reconnecting session is double-billing.

MIT license.
