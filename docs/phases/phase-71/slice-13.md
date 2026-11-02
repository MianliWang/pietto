# Phase71 Slice13: flat Unnest vertical path

发布状态：`COMPLETED / PUBLISHED`（main 的 B4 批次）。批次 head
`9df0003f020c0d5e61fb32e4528cfd20d9125142`，tree
`fa5e45c8c794207a360b3a195474e738ac2f49e9`；自然 CI `41272976489`
attempt 1 的 19 个 job 均成功。
以下保留实施时的候选与检查记录；其中的待验证文字属于封存前时点。

封存前记录：candidate，未验证。本记录绑定当前 B4 S13 worktree base
`e169cb88f17d54234a96fc275766cb0995a2be37`；它不是 Gate 2 seal、发布记录或
自然 CI 结果。

本片只开放 PostgreSQL 的一个精确 `ProjectSQLUnnest` 路径：一个左输入的一个
Collect source port，经一个 CROSS、INNER 或 LEFT JOIN 展开为最终平面输出。source
emission 使用 `JOIN LATERAL ROWS FROM`，每个 child array 一个单参数
`pg_catalog.unnest` 调用；Collect carrier 不进入 JOIN 输出或 CTE header。

准入不用名称寻找关系或任意选择候选。它核对 plan 中的 `collect`、`source`、`join`、
`input` 和输出 suffix identity，要求左输入只有该一个 nested port、全局只有一个
Unnest、最终 exports 不含 nested 值。child 只准 Int、Bool、有限 Text；Float、Decimal
留给 S14，Date、Timestamp、UUID 留给 S15。MySQL、第二个 Unnest、nested sibling
carrying、普通 parent reader、R2、sink、relay、storage 与 IPC 不因最终输出平面而放宽。

开发 focused 与 source SDK 结果记录在 B4 证据账中，均不构成 Gate 2 或发布。最终验收必须以
真实 source plan、compiled build/load/lowering、source-free bundle 和 public
`postgres_rows` preflight 覆盖 CROSS/INNER/LEFT、presence/empty、nullable child、父
ORDER/LIMIT 与 corruption matrix；不能把旧 SQL graft witness 当作纵向验收。


## Current source-free and public closure

The private v6 Unnest record becomes a typed compiled semantic IR operator
immediately before its consuming JOIN. It is not a SQL CTE or a schema
`RELATIONS` unit. Child facts retain their exact Collect-child provenance;
unknown grain and no key/FD claim prevent child identity from becoming global.
The logical collection slot survives only as the exact hidden JOIN port.
Description, retained-source, IR, plan and emitted-AST readers rederive this
edge and reject a scalar read of it. Source and compiled admission require one
Collect and one Unnest.

The strict data-only public reader parses the typed array expansion, retains
the hidden logical requirement, and requires flat physical columns and exact
CROSS/INNER/LEFT scope, child order, provenance and null-extension evidence.
The existing PostgreSQL API native family now contains U1/U2/U4/U5, a project-deleted
bundle case and a max_rows=64 preflight refusal against the FULL seed's 6*11
upper bound. These are validation inputs; no native/Gate 2/publication result
is asserted by this note.

Source admission rejects authored aliases, module transfers, post-Unnest filters,
extra JOINs and parameters retained to S16. The compiled verifier rederives the
serialized semantic boundary: one selected JOIN, a direct Collect-parent carrier
in the same module, projection-only consuming row stages, and no consuming block
read. Authored alias spellings have already been erased before this wire form;
compiled checks do not infer them from SQL names. The Collect parent may have
ORDER/LIMIT before expansion; post-Unnest ORDER/LIMIT remains with S16.
Parent-only flat projections and basic captured Collect remain admitted.
