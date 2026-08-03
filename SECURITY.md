# Security Policy

## Reporting a vulnerability

VOXD is a local-first application. Security issues should be reported privately
to the maintainers (open a GitHub Security Advisory or contact the maintainers
directly). Do **not** file a public issue for sensitive vulnerabilities.

## Design principles

VOXD follows these security invariants:

1. **Local-first by default.** Audio is captured, transcribed, and typed on the
   user's machine. No audio, transcripts, or usage telemetry are transmitted
   anywhere unless the user explicitly enables an opt-in cloud feature.
2. **No secrets.** The application requires no API keys or accounts. The setup
   flow only downloads models/builds open-source code over pinned HTTPS URLs.
3. **Least privilege.** The daemon runs as the invoking user (never root).
   Temporary audio files use secure `mkstemp` and are deleted after use.
4. **Command safety.** `subprocess` calls use argument lists (`shell=False`);
   model/whisper paths are validated, never passed through a shell.

## Threat model

- **Local adversary** — a user on the same machine cannot read another user's
  audio because temp files are created with user-private permissions and the
  socket is user-owned (`srw-------`).
- **Network** — VOXD makes no network connections at runtime. The only
  network activity is user-initiated model downloads during `voxd setup`.
- **Untrusted transcripts** — Whisper output is typed as keyboard input, not
  executed. Cleanup strips control characters.

## Scope

- `app/`, `scripts/`, `installers/` — in scope.
- Bundled/third-party components (`whisper.cpp`, Qt) — subject to their own
  upstream security processes.

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | ✅ |
| < 1.0 | ❌ |

## Disclosure

Please allow 30 days for a coordinated fix before public disclosure.
