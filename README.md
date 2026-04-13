# Whirlpool Appliances (AWS IoT) — HACS Custom Integration

Test integration for the [whirlpool-sixth-sense](https://github.com/abmantis/whirlpool-sixth-sense) AWS IoT branch. Clones the official [Whirlpool integration](https://www.home-assistant.io/integrations/whirlpool/) and adds microwave support via the AWS IoT MQTT transport.

## Installation

1. Add this repository as a custom repository in HACS (Integration type)
2. Install "Whirlpool Appliances (AWS IoT)"
3. Restart Home Assistant
4. Add the integration via Settings > Integrations > Add Integration > "Whirlpool Appliances (AWS IoT)"

## Supported Appliances

All appliances supported by the official integration (aircon, washer, dryer, oven, refrigerator) plus:

- **Microwave** (via AWS IoT): cavity state, cook timer, hood fan, hood light, cavity light, control lock, quiet mode, sabbath mode, start/cancel cook

## Vendored library

The `whirlpool-sixth-sense` library is bundled under `custom_components/whirlpool_aws/_vendor/` instead of being installed via pip. Home Assistant's built-in `whirlpool` integration pins its own copy of that library, and bundling sidesteps the dependency clash. The integration's `__init__.py` adds `_vendor/` to `sys.path` at load time so the bundled copy is always used.

`custom_components/whirlpool_aws/_vendor/.source-ref` records the exact repo, ref, and commit SHA of the last sync. Treat the contents of `_vendor/whirlpool_aws/` as generated — never hand-edit.

### Refreshing the vendored library

Use `scripts/sync_library.sh` to pull a new version of the library into the vendor tree:

```bash
# Pull the default branch tip (pts211/whirlpool-sixth-sense @ aws_iot-scaffolding)
./scripts/sync_library.sh

# Pin to a specific commit for reproducibility
./scripts/sync_library.sh --ref <commit-sha>

# Sync from a different fork/branch
./scripts/sync_library.sh --repo someone-else/whirlpool-sixth-sense --ref their-branch

# Force resync even if the lockfile records the same SHA
./scripts/sync_library.sh --force
```

Flags:

| Flag | Default | Purpose |
|---|---|---|
| `--repo` | `pts211/whirlpool-sixth-sense` | Accepts `owner/name` or a full git URL |
| `--ref` | `aws_iot-scaffolding` | Branch name, tag, or commit SHA |
| `--source-dir` | `whirlpool` | Top-level library dir in the source repo. Use `whirlpool_aws` if the upstream branch hasn't reverted the rename yet. |
| `--force` | off | Sync even when the lockfile already records the resolved SHA |

After syncing, review the diff and commit both `_vendor/` and the lockfile.
