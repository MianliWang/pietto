# CI Workload Governance v1

## 分类、placement与规范覆盖

ci/workloads.toml 是小型versioned registry；class、family、acquisition/affinity group、dependency profile
描述要求，placement才指定shard与native scheduler。支持shared-acquisition、process-portability、
general-runtime；默认ordinary无需逐node注册。当前profile core不安装Arrow。新依赖/affinity在入域前review，
没有placement就actionable fail，不能自动装包/改workflow/遗漏测试。

普通pytest通过pytest.ini注册ci_workload marker，不改变discovery/addopts/selection。例如：

```python
@pytest.mark.ci_workload("process-portability", family="plan")
def test_new_portability_case():
    ...
```

module/function/parameter marks全部参与；完全相同声明只形成一个effective requirement，任意矛盾拒绝，
不是nearest/last-wins。legacy file与exact-node compatibility规则显式列在registry；只有写明父file规则的
exact-node例外可覆盖它。重复同precedence、stale required file、现有六mode缺失/额外mode、marker矛盾均拒绝。
新family只需注册要求与placement，不往runner加Phase-number分支。

full U从所有collected items独立产生，再解析要求；registry不是U。coverage v2以compact descriptor
table/indices绑定policy/placement identity、full collection、actual selection与setup/call/teardown。
每worker必须一致；逐runtime非空disjoint union=U；failed/skipped/missing prerequisite不能被报告掩盖。
v1只作历史，不允许宽松fallback。coverage仍≤8MiB，所有旧semantic node IDs/断言保持。

| shard | requirement | scheduler |
| --- | --- | --- |
| shared-acquisition | compiler-differential cohort／named group | loadfile |
| plan-portability | process-portability / plan | load |
| emission-portability | process-portability / emission | load |
| general-runtime | general-runtime / default | loadfile |

每job资源选择≤4workers，无嵌套池。checks/runtime/targets独立启动；共15realized jobs；保留两个Python
completion contexts与strict target aggregate。共享lock/Ruff、双Pyright/generated/golden/installed和pins不变。
小Arrow实验是两compiler/package jobs中的required隔离step，core全量测试不靠缺依赖skip。

## managed locality与观察

同primary/runtime-domain、assurance purpose、group、child interpreter/seed/mode、input identity只允许
一次canonical managed-store production，并且在approved shard。memo/重复读取不重复计数；另一个primary
runtime及明确standalone/forward/reverse/native目的不是重复。只有acquisition()创建的run-owned store启用
可选passive observer；synthetic unit stores不计数。原locks、rotation、返回值、exception与semantic bytes保留。
所有worker必须提交完整observer状态；未观测是unknown，不是零。wheel/relocation可在jobs间重复并单独记成本。

## advisory health、历史与信任

health v1每份≤1MiB、30日retention，独立于coverage/receipts。包含context、policy/topology、patch、
实际可用child-domain、runner image/OS/arch、worker数、node/group counts、scheduler、elapsed/startup、
worker phase sums/finish spread、bounded slow nodes/groups、managed production与完整性。可选CPU/memory缺失为null。
phase时长包含等待/child/preparation，不当CPU；finish spread只筛查，必须同时呈现粒度和任务数。

初始thresholds在registry可审查配置：longest/median>1.25 WATCH、>1.50 review候选；finish-spread/elapsed>0.30；
startup/elapsed>0.25；单node>partition0.40且>60s；可比critical path增长>25%；sum增长>20%且wall改善<15%。
slow正确结果不失败。current mandatory report畸形/缺失是report failure。输出HEALTHY/WATCH/
REVIEW_RECOMMENDED/INSUFFICIENT_EVIDENCE、reason codes和review actions，不产生可执行YAML。

最终aggregate以job级contents:read/actions:read读取最多30日内10候选run、最多3eligible同repo、push/main、
completed success、attempt1的health。PR不入trusted history。raw长度/digest/schema/context先验证；不执行、
不加载其配置；过期/失败则记录不足证据，不循环抓取。首轮无history正常；R1仅标记旧reference，不伪造v1health。
数值历史建议至少最近3个可比样本中2个；structural observation可立即建议review。policy/topology/runner/
patch/child-domain差异与test-set/group drift显式呈现，不能虚构按节点数归一化。

job elapsed、test elapsed、依赖关键路径、queue与job sum分开；当前run尚未结束或API不可用时cost为partial，
不能用已完成jobs之和假装完整成本。历史完整run可由只读API补足真实job成本。所有Markdown/labels escaped，
不输出credentials或任意environment values。维护只能通过普通reviewed commit，health不改U、不调worker、不retry。

新测试清单：ordinary或special；family/profile/group；估算成本/资源影响；扩展的既有assurance；可执行正反例。
不要求精确时间目标。phase start消费eligible health与适用lesson，midpoint/closeout评价alerts；没有alert就不新增CI维护。
