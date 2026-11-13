### Package asset paths that start with a letter and a colon

A package manifest asset path of any kind whose first character is a
non-ASCII letter followed by a colon, such as `é:x.pietto`, is now refused
as `C:/x.pietto` is: `explain --project` reports `project_path`
`Package manifest assets[0].path is structurally invalid.` and exits 2.
In JSON output its `location` names the path as a `package_relative`
value, where the `C:/x.pietto` error has a `null` location.

A manifest with a lone `module_source` asset `é:x.pietto` used to pass,
and `explain --project` printed a Python `ValueError` traceback and exited
1. Manifests that were already refused now report this `project_path`
error in place of a `config_schema` error located at `pietto-package.toml`,
and still exit 2:

- a `data` asset `é:x.pietto`, which reported
  `Package manifest assets[0].kind must be module_source.`;
- a `module_source` asset `é:x.txt`, which reported
  `Package manifest assets[0].path must end with .pietto.`;
- two `é:x.pietto` assets, which reported one
  `Package manifest assets[1].path duplicates assets[0].path.` error and
  now report one `project_path` error for each asset.

No dependency path changed, and no diagnostic code or JSON shape was added.
