# Test Command

Run all tests and lints for the project.

## Steps

1. Run backend tests with pytest
2. Run frontend tests with vitest
3. Run frontend lint with svelte-check
4. Run backend lint with ruff

## Commands

```bash
uv run pytest tests/
```

```bash
cd frontend && npm run test -- --run
```

```bash
cd frontend && npm run lint
```

```bash
uv run ruff check . -fix
```
