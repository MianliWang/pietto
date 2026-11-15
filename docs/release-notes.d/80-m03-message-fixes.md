### Message fixes

- `emit-sql --project ... --format text` writes a diagnostic that has no
  source path as `CODE severity: message`, without a location, as it
  already writes such a blocker; earlier releases wrote `None` as its path.
  A diagnostic with a path keeps its `path:line:column` prefix, and the
  JSON documents are unchanged.
- The `ModuleNotFoundError` that a `pietto.interop` function raises when its
  extra is not installed quotes the requirement it names, for example
  `to_pandas needs pandas: install "pietto[arrow,interop-pandas]"`, so the
  command can be pasted into a shell that expands brackets. Its `name` is
  still the missing library.
