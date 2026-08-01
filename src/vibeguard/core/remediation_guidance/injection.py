"""Remediation guidance for SQL/NoSQL/OS command injection."""

GUIDANCE = (
    "Use the database driver's own parameterized-query placeholder syntax "
    "(e.g. `cursor.execute(query, params)` with `%s`/`?` placeholders, or "
    "the ORM's query builder) to pass user-controlled values. Never build "
    "a query by string concatenation or f-string/format interpolation, "
    "even with manual escaping or quoting -- escaping is not a substitute "
    "for parameterization. For shell commands, use `subprocess.run([...], "
    "shell=False)` with arguments as a list, never a shell string built "
    "from user input."
)
