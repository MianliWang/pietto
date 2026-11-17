### Faster `import pietto.execution`

`import pietto.execution` now loads only its seven access, input, premise
and limit classes: `PostgresAccess`, `MySQLAccess`, `DuckDBArrowInput`,
`SQLiteFileInput`, `PostgresDeploymentPremise`, `MySQLDeploymentPremise` and
`ExecutionLimits`. Every other name, from `compile_query` and `execute` to
`R2SourceInput` and the error and result classes, imports its owner, and
with it the project compiler and `hashlib`, when it is first read, as the
saved-result names already did.
`__all__`, the names and the objects they read as are unchanged. See the
[effects of execution](../execution.md#effects).
