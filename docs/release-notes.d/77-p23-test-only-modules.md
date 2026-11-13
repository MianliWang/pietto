### The wheel no longer ships modules that only tests use

Twelve private modules under `pietto._project` that no command, the Python
compile API or `pietto.execution` imports, about 22,000 lines, now live
under `tests/` as test helpers: `package_graph`,
`package_graph_inspection`, `project_bag_null_oracle`,
`project_ir_inspection`, `project_ir_pipeline`, `project_ir_pure_boundary`,
`project_job_store_verification`, `project_phase62_inspection`,
`project_phase62_pure_boundary`, `project_result_contract_correspondence`,
`project_sql_emission_portable` and `project_sql_emission_pure_boundary`.
An installed Pietto refuses `import pietto._project.package_graph` and the
other eleven with `ModuleNotFoundError`. These modules were private, and no
command, diagnostic, JSON document or SQL output changes.
