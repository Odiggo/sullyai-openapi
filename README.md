# Sully.ai OpenAPI Spec

This repository contains the public OpenAPI definition for the Sully API.

## Transcription Notes

Some real-time streaming details are documented here because they are not fully represented in `openapi.yaml`.

- `POST /v2/audio/transcriptions` accepts optional multipart field `dictation`. Default: `false`.
- `/v1/audio/transcriptions/stream` accepts optional query parameter `dictation=true|false`.
- Malformed or non-audio websocket messages are ignored so later valid audio can still stream.
- Runtime stream errors may be surfaced to the client without always closing the session immediately.
