# Contributing to `skodaconnect/homeassistant-myskoda`

Thank you for considering contributing to the `homeassistant-myskoda` project! This guide covers how to set up your development environment, follow code standards, and submit high-quality pull requests.

---

## 🛠️ Development Setup

We use [**uv**](https://github.com/astral-sh/uv) as our preferred Python package manager for its performance and simplicity.

### Step 1: Install `uv`

**MacOS/Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Step 2: Create and activate a virtual environment

**MacOS/Linux**

```bash
uv venv
source .venv/bin/activate
```

**Windows**

```bash
uv venv
source .venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
uv sync --all-extras
```

---

## ✅ Code Quality and Pre-commit

We use [pre-commit](https://pre-commit.com) to enforce code formatting and linting standards.

### Install and enable pre-commit hooks

```bash
uv pip install pre-commit
pre-commit install
```

### Run checks manually

```bash
uv run pre-commit run --hook-stage manual --all-files
```

This will run tools like ruff, pyright and others before each commit to ensure your code meets our standards.

---

## 🧪 Running Tests

There are no automated or unit tests included in this project.

We expect you to test changes on a local/dev Home Assistant instance and document the results in your pull request.

To set up a local Home Assistant development environment following the guide in the [Home Assistant Developer Docs](https://developers.home-assistant.io/docs/development_environment/).

---

## ✍️ Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard.

### Format

```
<type>(optional scope): <short description>
```

### Examples

- `feat: add support for new vehicle endpoint`
- `fix: resolve VIN decoding crash`
- `docs: update README example for login flow`

### Allowed Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation-only changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code changes that don't fix bugs or add features
- `test`: Adding or updating tests
- `chore`: Build tasks, dependency management, etc.

Using Conventional Commits ensures clarity and enables automated changelog generation.

---

## 🤖 Automated Code and AI Usage

We want **all** submissions to respect our [AI Policy](AI_POLICY.md).

---

## 🚀 Submitting a Pull Request

When you're ready to contribute:

1. Make sure **all tests pass**.
2. Run **pre-commit checks**.
3. Use **Conventional Commit** messages.
4. Open a PR against the `main` branch.
5. Provide a **clear description** of the changes and rationale.

We’ll review your pull request and may request changes or clarification. Thanks for helping improve the project!

---

## 🤝 Questions or Feedback?

If you have questions or ideas, feel free to [open an issue](https://github.com/skodaconnect/homeassistant-myskoda/issues) or start a discussion on [our Discord](https://discord.gg/t7az2hSJXq)

Thanks again for contributing to `skodaconnect/homeassistant-myskoda`!
