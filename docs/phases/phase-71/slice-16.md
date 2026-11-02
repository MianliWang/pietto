# Phase71 Slice16: retained collections through composed queries

状态：candidate，未封存或发布。基线提交 `61a4ce4e05c190ea49e2eb93afd31e6fbdee7e29`，树 `da72b5412f4ecb087c508b9bd8204bf811a6e955`；R5 自然 CI `41362408512` attempt 1 全部 19/19 成功。

本片按 D71.09 与已有 D71.01–D71.12 决定，完成并列子表、命名/跨模块、普通 JOIN whole-group carry、上游分组和参数过滤，以及展开一项仍保留另一 collection。单个查询仍最多一个 Unnest；collection 不作 scalar operand、group/order key。已有保存/R1/R2/relay 和 ADBC/MySQL nested 停点不变。

Whole-group carry 复用 count/arrays；source 和 compiled verifier 保留 exact producer、child terminal、use/port 身份及外连接 nullability。Row authored reference 只覆盖 count token，transport 不伪造 expression。分组结果不需要伪造原始 source field：Unnest child 由其精确 terminal 与已验证 realization 描述，Decimal 参数另与 child semantic fact 对照。

所有者于 2026-11-01 批准公开 R27 producer 关联：每个 generated `collect_lateral.evidence` 精确记录 use、producer、terminal、ordered children。v1/v2 格式名不变，旧严格 reader 必须升级。列 producer 与该关联双向核对，单边篡改仍拒绝；这是一致性证据，不声称外部认证。

资源预检分别保存 canonical producer 和最终 retained occurrence：物理 source count 可共用，各 JOIN edge 和重复输出仍逐项计入。Outer JOIN 包含缺失容器的 NULL carrier 成本；所有乘加饱和，未知图或界限失败关闭。过滤不能假装缩小结构上界。

产品见证由既有 plan/SQL/compiled/result/execution owners承接。实际原生验收须包括完整 PG 目标清单的 `L_retained_collection` 两项，以及同一 exact wheel 的 API retained bundle、outer NULL、grouped parameter-filter bundle；独立输出 oracle 区分 BAG 外层行与有序 child list。focused、安装包、D71.11、Gate 2 与自然 CI 分开记录，尚未完成的步骤不作通过声明。
