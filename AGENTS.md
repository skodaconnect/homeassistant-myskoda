# AGENTS.md

This file gives repository-specific guidance to coding agents working in `homeassistant-myskoda`.

## Scope

- Applies to the whole repository.
- Follow this file before making changes.
- There is no existing `AGENTS.md`; this file is the canonical agent guide.

## Instruction Sources

- CI definitions are in `.github/workflows/lint.yaml` and `.github/workflows/validate.yaml`.
- Local developer helpers are in `scripts/`.

## Repository Shape

- Main integration code lives in `custom_components/myskoda/`.
- Runtime docs live in `README.md` and `docs/design.md`.
- Home Assistant dev config lives in `config/`.
- This is a Home Assistant custom integration, not a generic Python library or web app.
- There is no dedicated build pipeline that creates distributable artifacts.

## Tooling Snapshot

- Python is declared in `pyproject.toml` as `>=3.13.2`.
- Dependency management uses `uv` and a committed `uv.lock`.
- Linting and formatting use Ruff.
- Type checking uses Pyright.
- Pre-commit is the main CI entrypoint.
- CI also runs HACS validation and Hassfest validation.

## Environment Setup

- Preferred setup: `uv sync --all-extras`
- Install pre-commit if needed: `uv pip install pre-commit`
- Create or refresh the lockfile only when dependencies change: `uv lock`
- The devcontainer currently calls `scripts/setup`, but that script references `requirements.txt`, which is not present in this repo.
- For agents, prefer `uv` commands over `scripts/setup`.

## Main Commands

- Install dev environment: `uv sync --all-extras`
- Run all lint/type hooks exactly like CI: `uv run pre-commit run --hook-stage manual --all-files`
- Run Ruff linter only: `uv run ruff check .`
- Run Ruff with autofix: `uv run ruff check . --fix`
- Run formatter check: `uv run ruff format . --check`
- Format code: `uv run ruff format .`
- Run Pyright directly: `uv run pyright`
- Refresh lockfile: `uv lock`

## Local Runtime Commands

- Start Home Assistant dev instance with helper script: `scripts/develop`
- Equivalent manual command requires `PYTHONPATH` to include `custom_components/`.
- The helper script creates `config/` if missing and starts `hass --config ./config --debug`.
- Use runtime verification when changing config flow, coordinator behavior, or entity registration.

## Test Status

- There is currently no `tests/` directory in this repository.
- There is no pytest configuration in `pyproject.toml`.
- There is no CI job running automated unit tests today.
- Do not claim that tests passed unless you actually added and ran them.

## Single-Test Guidance

- If you add pytest-based tests, use the normal Home Assistant pattern via `uv run pytest`.
- Run all tests: `uv run pytest`
- Run one file: `uv run pytest tests/test_something.py`
- Run one test by node id: `uv run pytest tests/test_something.py::test_specific_case`
- Run a filtered subset: `uv run pytest tests/test_something.py -k "specific_case"`
- Because the repo currently has no tests, treat these as the expected command shape for new tests rather than an established workflow.

## Validation Guidance

- Minimum validation for most Python changes: `uv run ruff check .` and `uv run pyright`
- Preferred full validation before finishing substantial work: `uv run pre-commit run --hook-stage manual --all-files`
- For behavior changes, also smoke test with `scripts/develop` when feasible.
- HACS and Hassfest are important, but are currently expressed only in GitHub Actions.

## High-Level Architecture

- `__init__.py` handles integration setup, unload, migration, auth bootstrap, and platform forwarding.
- `coordinator.py` is the core state manager for vehicle/user data, MQTT events, and scheduled refresh.
- Platform files such as `sensor.py`, `button.py`, `lock.py`, and `climate.py` define entities.
- `entity.py` provides the shared base entity with VIN-based unique IDs and device metadata.
- `utils.py` centralizes supported-entity registration from coordinators.
- `error_handlers.py` centralizes HTTP-to-Home-Assistant error mapping.
- `issues.py` creates Home Assistant issue registry entries for T&C and S-PIN problems.

## Coding Style

- Keep module docstrings at the top of Python files.
- Use `from __future__ import annotations` in files that benefit from postponed evaluation; many modules already do.
- Follow Ruff formatting; do not hand-format against it.
- Use 4-space indentation and keep whitespace conventional.
- Keep imports grouped: stdlib, third-party/Home Assistant/myskoda, then local imports.
- Let Ruff manage import ordering instead of manual micro-tuning.
- Prefer explicit imports over wildcard imports.
- Keep one blank line between import groups and two blank lines between top-level definitions.

## Types

- Add type hints for public functions, async functions, properties, and important locals when clarity helps.
- Match the codebase's modern typing style, including `list[str]`, `dict[str, Any]`, and `X | None`.
- This repo already uses Python 3.13-era typing features such as `type Alias = ...`; preserve that style where helpful.
- Use Home Assistant typing aliases such as `ConfigFlowResult`, `AddEntitiesCallback`, and typed `ConfigEntry` aliases.
- Small pyright suppressions are acceptable when Home Assistant typing stubs require them; keep them narrow and inline.
- Avoid introducing untyped helper APIs when the surrounding module is typed.

## Naming

- Use `snake_case` for functions, methods, variables, constants keys, and module filenames.
- Use `PascalCase` for classes.
- Keep constants in `UPPER_SNAKE_CASE` and place shared constants in `const.py`.
- Follow Home Assistant async naming conventions: `async_setup_entry`, `async_unload_entry`, `async_step_user`, etc.
- Entity classes should use descriptive nouns like `BatteryPercentage`, `DoorLock`, or `ServiceEvent`.
- Translation-facing entity keys should stay stable once released.

## Entity Conventions

- Prefer subclassing `MySkodaEntity` for shared coordinator and vehicle access.
- Set `entity_description` as a class attribute.
- Use `translation_key` and stable `key` values for entity descriptions.
- Gate entity creation with `required_capabilities()` and `forbidden_capabilities()` instead of scattered checks.
- Use `add_supported_entities()` in platform setup functions to keep coordinator iteration consistent.
- Keep VIN-based unique IDs stable; avoid migrations unless necessary.
- Respect Home Assistant concepts like `available`, `device_class`, `state_class`, and `entity_category`.

## Error Handling

- Prefer catching specific MySkoda, aiohttp, and Home Assistant exceptions.
- Reuse `handle_aiohttp_error()` for `ClientResponseError` paths instead of duplicating logic.
- Raise `ConfigEntryAuthFailed` for auth failures during setup or migration.
- Raise `ConfigEntryNotReady` for temporary startup problems that should trigger retry.
- Raise `UpdateFailed` for coordinator refresh failures.
- Raise `ServiceValidationError` for invalid user-triggered operations such as readonly mode or missing S-PIN.
- Broad `except Exception` blocks are tolerated only at integration boundaries where the code logs and degrades safely.
- Log meaningful context with `_LOGGER`, but do not log secrets, passwords, refresh tokens, or S-PINs.

## Async and State Rules

- Favor async Home Assistant APIs throughout the integration.
- Do not block the event loop with synchronous I/O.
- Coordinator state should remain the source of truth for entities.
- When mutating state in response to MySkoda events, update the coordinator and call `async_set_updated_data()`.
- Keep MQTT retry and refresh behavior centralized in `coordinator.py`.
- Preserve the pattern of disabling entities/buttons during long-running operations to prevent overlap.

## Change Discipline

- Keep changes narrowly scoped to the feature or bug being addressed.
- Avoid large refactors unless they clearly reduce duplication or fix a real problem.
- Preserve backward compatibility for config entry versions, entity unique IDs, and option names.
- If you change config entry data or entity IDs, update migration logic in `__init__.py`.
- If you add user-visible entities or options, make sure translations and documentation stay coherent.

## Agent Notes

- Prefer `uv`-based commands in instructions, scripts, and new documentation.
- Mention when a helper script appears stale or inconsistent with current tooling.
- If you add tests, document the exact `uv run pytest ...` command you used.
- If you cannot run a validation step, say so plainly and explain why.
