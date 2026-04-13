# Vendored library

This directory is populated by `scripts/sync_library.sh` from
[pts211/whirlpool-sixth-sense](https://github.com/pts211/whirlpool-sixth-sense).
Do not hand-edit files under `whirlpool_aws/` — any local changes will be
overwritten on the next sync.

The integration's `__init__.py` adds this directory to `sys.path` before any
`whirlpool_aws` imports, so the bundled copy is used instead of whatever
Home Assistant's built-in `whirlpool` integration would otherwise pull in.

The file `.source-ref` records the exact repo, ref, and commit SHA of the
last sync for auditability.
