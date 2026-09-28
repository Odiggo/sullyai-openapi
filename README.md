# Sully.ai OpenAPI Spec

[`openapi.yaml`](openapi.yaml) is the canonical public contract for the Sully API,
reference documentation, and TypeScript/Python SDK generation. It uses OpenAPI 3.1.

When changing the public API in `sullyai-copilot/apps/api-server`, open a separate,
linked PR here and verify it against the server routes, validators, response mappers,
and authentication middleware. The server PR and spec PR should link to each other.
Automatic Express/Zod export is optional future work and does not block SDK releases.

## Contract maintenance

- Keep existing `operationId` values and component names stable: generators use them
  for public methods and types. Give new request/response models explicit names.
- Optional fields may be omitted. Allow null only where the server accepts or emits
  it, using JSON Schema types/unions/constraints; never use `nullable` from OpenAPI 3.0.
- Standard routes require **both** `X-API-Key` and `X-Account-Id` in one security
  requirement. OpenAI-compatible routes also document their supported Bearer forms.
- Audit multipart field names, MIME types, required fields, HTTP statuses, and error
  envelopes against the implementation. Auth errors can have a different shape.
- Review [the 0.3.0 migration notes](compatibility/0.3.0.md) before regenerating existing
  SDKs. A successful HTTP-contract diff does not prove SDK source compatibility.

## Validation and generation smoke checks

Use Python 3.12+, Node 22+, Java 21, and [oasdiff 1.32.1](https://github.com/oasdiff/oasdiff/releases/tag/v1.32.1).

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/validate.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/check_breaking.py origin/main
.venv/bin/python scripts/sdk_smoke.py typescript
.venv/bin/python scripts/sdk_smoke.py python
```

The smoke script downloads checksum-pinned OpenAPI Generator 7.25.0, generates from
`openapi.yaml` into a fresh temporary directory, builds TypeScript and a Python wheel,
and checks wire serialization/imports without contacting a live API. Python runtime
versions and TypeScript's compiler are pinned. `JAVA_BIN` and `--jar` can select an
existing runtime/JAR; `OASDIFF_BIN` selects an existing oasdiff executable. Logs and the
breaking-change report are written under the ignored `.sdk-smoke/` directory.

CI runs these checks on PRs and main. Undocumented breaking findings fail the gate.
The 0.3.0 manifest allows only its enumerated correction fingerprints against the exact
old spec checksum; it cannot suppress findings once that base changes. Review changes
in the manifest together with the migration/version decision, never as a blanket bypass.

The retired Stainless workflow has been removed: the organization has migrated to
`stlc`, and its hosted builds return HTTP 401. The existing required `build` check for
`main` now aggregates `contract`, `sdk-smoke (typescript)`, and `sdk-smoke (python)`
from this repository's validation workflow. It fails if any dependency fails, is
cancelled, or is skipped. Cross-repository dispatch and SDK publishing are separate work.

## Generator notes

- TypeScript keeps wire property names (`modelPropertyNaming: original`). Python maps
  the legacy camelCase template aliases to distinct `*_legacy` attributes; serialization
  preserves both original wire spellings.
- Null-only chat response fields use `type: [string, 'null']` with `const: null`, which
  still permits only null. Standalone `type: 'null'` properties crash the pinned Python
  generator. Message content parts use equivalent conditional object constraints to
  avoid a broken nested-union import in the TypeScript generator.
- Server-only validations such as trimmed-string lengths, unique V3 section titles,
  combined text budgets, and maximum template heading depth are documented in schema
  descriptions. Do not assume generated clients enforce every JSON Schema constraint.
- SSE is a wire stream, with named chunk/error schemas referenced by
  `x-sse-event-schema`. Generated JSON methods alone are not an SSE client; a streaming
  helper must handle comments, chunks, error frames, cancellation and `[DONE]`.
- The smoke Python transport is synchronous `urllib3`. Async transport, polling,
  retries, timeout defaults, and compatibility with existing SDK interfaces belong
  to the SDK implementation stage.

## Transcription notes

- Upload one binary file in the `audio` multipart field with its supported audio MIME
  type. Maximum size is 100 MiB. Send multipart booleans as `true` or `false`.
- `POST /v2/audio/transcriptions` accepts optional `dictation`, defaulting to false.
- V1 also supports JSON base64 uploads with `audio`, `encoding: base64`, and `filename`.
- `/v1/audio/transcriptions/stream` accepts optional query `dictation=true|false`.
- Malformed or non-audio WebSocket messages are ignored so later valid audio can stream.
- Runtime stream errors can be surfaced without immediately closing the session.
