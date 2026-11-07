# Innerscape Coach v0

A native Hermes plugin: persistent mood/energy check-ins, goals and habit marks,
a compact state brief on stuck/blocked/“where was I” signals, and one small
first-contact action quoted from the real Unstuck Coach protocol.

**Not medical care, diagnosis, therapy, or emergency support.** No clinical claims.
This is a new stdlib Python implementation, not the Innerscape TypeScript app.

## Install

Supported/tested Hermes source: `90d6b98fd86d20981ee06ddd5b7d93e4320f26a4`,
Python 3.14. No plugin runtime dependencies. Once Security has merged the PR,
replace `<AUTHORIZED_MAIN_SHA>` below with the authorized full main commit:

```sh
hermes plugins install KyaniteLabs/innerscape-coach --ref <AUTHORIZED_MAIN_SHA> --enable
```

For local development, copy this checkout (without `.git`, virtualenvs or caches)
to `$HERMES_HOME/plugins/innerscape-coach`, then
`hermes plugins enable innerscape-coach`. Restart your own Hermes session to load.
Never install unreviewed Python plugins into a trusted profile.

## API and slash commands

- `coach_checkin(mood, energy, note="")`: integers 1–5; optional note ≤500 chars.
- `coach_goal(action, title="", goal_id=null)`: `set` (title ≤200 chars),
  `complete` or `abandon` (positive integer ID). Only open goals transition;
  repeated terminal transitions and missing IDs are errors.
- `coach_habit(action, name="")`: `mark` (name ≤100 chars) or read-only `summary`
  (latest 20 distinct habits with lifetime counts; no streak scoring).
- `coach_unstuck(task="")`: read-only; task ≤200 chars. Returns the verbatim
  Task Initiation Protocol section, source revision, one next action and a proof
  question. It does not run scripts, infer clinical state, or implement every
  protocol in the bundled reference.
- `coach_brief()`: read-only latest check-in, three latest open goals and three
  habit counts, ordered by monotonic ledger IDs, not ambiguous timestamp ties.
- `/checkin 3 4 optional note`, `/unstuck release task`, `/coach-review`.

Tool responses are JSON envelopes (`ok/result` or `error`). Slash commands
return the same JSON, except malformed check-in syntax returns usage text.
Invalid input does not create a ledger. No import/register side effects.

`pre_llm_call` returns the supported `{"context": brief}` shape on matching
signals. Text is explicitly marked untrusted and JSON escaped. These labels are
prompt-injection defense in depth, not an LLM security boundary. `post_tool_call`
records only a validated tool name, UTC timestamp and allowlisted
`success/error/unknown`; never args, result bodies, exception text or secrets.
Logging is best-effort and disabled on nonlocal/unknown platforms by default.

## Persistence, privacy and platform policy

Ledger: `<get_hermes_home()>/plugin-data/innerscape-coach/ledger.db`, created
lazily on the first allowed write. SQLite transactions and constraints protect
writes. Read paths use SQLite `mode=ro` and do not initialize a database.

**One profile means one shared ledger. There is no per-user isolation.** Gateway
users sharing that profile can read its summaries; enable only in a trusted
single-user/private profile. Even when gateway writes are off, reads remain
available. The plugin has **no network, secrets, child processes or web endpoint**,
but briefs and tool results enter Hermes context and therefore **reach the
configured model provider**. “Local ledger” does not mean offline inference.
Do not enter sensitive notes. The database is plaintext, not encrypted; protect
profile filesystem permissions and backups. New data directories request 0700;
existing directory permissions and database file mode follow the host/umask.
Retention is unbounded in v0; no deletion/export tool, sleep log or import.

Writes require a host-bound `HERMES_SESSION_PLATFORM` of `cli`, `tui` or `desktop`,
or explicit plugin opt-in. Slash commands also accept host-provided `platform`;
a bound session platform wins. Unknown/empty platform is **not local**. For a
local CLI whose runtime does not bind platform, launch explicitly with
`HERMES_SESSION_PLATFORM=cli hermes`; do not set that on a gateway service.
Tool arguments cannot override platform policy. No process-global platform
cache is used. `/unstuck`, `/coach-review`, brief and habit summary are read-only.

To intentionally allow **all callers of this profile**, including unknown and
gateway platforms, to mutate the shared ledger:

```sh
hermes config set plugins.entries.innerscape-coach.settings.allow_gateway_writes true
```

Only boolean `true` enables it. Reset to `false` to revoke. This is the plugin's
own policy, not a sandbox or per-person authorization. Manifest `capabilities: []`
is truthful for Hermes' enforced capability IDs: no tool override, model/provider
override, side-question LLM call or platform action is requested. Filesystem state
and context injection are disclosed here and in the manifest description.

## Verify

CI pins Python 3.14 and the full Hermes revision above, using its locked dependency
resolution. Run with that runtime on `PYTHONPATH`:

```sh
HERMES_SOURCE=/path/to/hermes-agent python -m pytest -q
hermes plugins validate . --json
sha256sum -c protocol.sha256
```

Tests exercise SQLite persistence/constraints, tools, real Hermes hook dispatch,
real slash dispatcher, platform refusals, metadata sanitization and byte fidelity.
No model or gateway service is contacted. Local evidence is in `evidence/`;
remote CI on the PR is a separate gate.

## Removal / rollback

`hermes plugins disable innerscape-coach`, then restart the relevant session.
Remove the installed plugin directory after disabling; preserve the ledger to
roll back/reinstall. To erase notes permanently, first stop all users of that
profile and back up if required, then have the authorized owner remove
`plugin-data/innerscape-coach` (including any SQLite sidecars and backup copies).
Disabling does not delete data. v0 uses schema version 1, no migrations.

## Provenance and submission hold

Apache-2.0; see LICENSE and NOTICE. `skills/innerscape-coach/protocol.md` is
byte-for-byte upstream `rules.md` at
`5412d80df6d64ca853dfb804354029a26e1df952`; hash in `protocol.sha256`.
No MIT source copied. Bundled reference prose is data, never executable code.

The initial main base is an **empty commit only**, needed to open the first PR;
implementation is exclusively on `factory/t_7f546091-innerscape-coach`. Engineering
must not self-merge. Security reviews exposure/secrets/blast radius/rollback.
No catalog PR, release, package, tag or announcement is authorized here.
Simon must approve the entry before any catalog submission. A future catalog
entry must pin the authorized merged main SHA, never this unmerged branch.

Demo outline (under 90 seconds, Growth owns recording): set check-in and goal;
show stuck brief; `/unstuck release`; log another check-in; restart the session
and `/coach-review` to demonstrate persistence. Use synthetic, non-sensitive notes.
