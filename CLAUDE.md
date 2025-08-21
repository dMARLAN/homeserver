# The project primarily consists of modules in src/ + an experimental dir

# Notes

- Remember to read this guide when making LLM calls
- When finished making changes, make sure to run `make ci` to validate the changes, and fix any issues before you
  finish.
  - Make sure to run `make ci` in the root directory of the project.
- If you need to launch the application use `make up-dev`.

# Docker

- When using `docker-compose.sh` and you want to exclude a service, use the `--exclude` flag with the name of the file,
  for example `--exclude="compose.api.yaml"`.

# Frontend

- When adding new components, prefer using shadcn for components
- To add shadcn components correctly, use `npx shadcn@latest add` command from the frontend directory

# Python

- All Python code is using Python 3.12+
- Prefer using dataclasses or Pydantic models for structured data (avoid using dicts, tuples, etc. whenever possible)
- When adding dependencies use `uv add dep-name` do not manually configure the `pyproject.toml` file.
    - You will need to `cd` into the appropriate directory first, e.g. `cd src/db` or `cd src/api`.
- When running Python code use `uv run` command, e.g. `uv run src/api/src/main.py`.
- You can run tests by using `uv run make unit-tests`.
- Remember not to inline imports. They must be put at the top of the files.
- Type hints should use Python 3.12+ syntax.
    - Use `list` instead of `List`, `Foo | None` instead of `Optional[Foo]`, `Foo | Bar` instead of `Union[Foo, Bar]`,
      etc.
- Do not create `__init__.py` files unless it is necessary for initialization logic.
    - `__init__.py` files are not necessary after Python 3.3.
- Naming conventions:
    - Use `foo` for public functions, methods, variables, classes, modules, and packages.
    - Use `_foo` for protected functions, methods, variables, classes, modules, and packages.
    - Use `__foo` for private functions, methods, and variables.
- `@staticmethod` should be used for methods that do not require access to the instance or class.
- `@classmethod` should be used for methods that require access to the class but not the instance.
- Always use Pathlib for file and directory operations instead of os.path.
- Prefer importing specific functions or classes from modules instead of importing the entire module.
    - For example, use `from module import function` instead of `import module`.
- Use `Final` type-hint for constants and immutable variables.

# Bash

- Use `${var}` syntax for variables instead of `$var`.
- Use `${VAR}` syntax for environment variables or constants instead of `$VAR`.

# Readability

- Only use comments when necessary and add context. Code should be self-explanatory.
- "Perfect code" has zero comments, except for:
    - TODOs (not relevant for you)
    - "why" comments that explain the reasoning behind a decision that is unorthodox—this is not necessary for orthodox
      code
    - linking to external resources, documentation, references, or algorithms when necessary
- If a block of code is becoming complex, break it into (a) smaller function(s)/method(s) to encapsulate that logic
  with (a) helpful name(s) instead of comments.
- Do not use redundant comments that simply restate what the code is doing:
    - Bad: `# Create user` above `user = User(name="John")`
    - Bad: `# Get the data` or `# Initialize variables`
    - Good: `# This is a workaround for...` or `# This is a temporary solution until...`
