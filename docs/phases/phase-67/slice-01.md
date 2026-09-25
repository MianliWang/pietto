# Phase67 Slice01：CI workload governance 与 Arrow readiness

这是 joint foundation/experiment Slice，不是仅规划或仅 CI 交付。基线 e0d02247，继承完成的 Phase66
审计、Interlude V S1–S3 与 R1。只有全部本地/发布/自然 CI 链成功后才是 COMPLETED / PUBLISHED。

## 自足执行边界

材料：[brief](brief.md)、[路线](slices.md)、[规划](planning-notes.md)、
[Phase66 J01–J06](../../spec/phase66-completion-audit-phase67-handoff-v1.md#phase66-retrospective-and-engineering-lessons)、
[CI governance](../../architecture/ci-workload-governance-v1.md)、[工程教训](../../references/engineering-lessons.md)。
代码 owners：ci/workloads.toml、scripts/ci_workloads.py（import-only）、scripts/ci_validation.py、
现有 acquisition helper 的 canonical-store-only observer、现有 CI tests 与本 Slice principal。
实验 owners：ci/phase67-arrow-compatibility-requirements.txt 和 tests/_pietto_phase67_arrow_compatibility_probe.py。
精确27路径冻结与累计 ledger 在外部 evidence；不得扩写或改 src、core lock、pins、native receipt。

做法：full U → item requirement resolution → placement → actual reports/managed productions →
independent reconciliation → health/Job Summary/history → reviewed maintenance decision。history 永不加载配置或执行代码。
隔离 Arrow 安装 → fresh subprocess probe → 完整 case validation → private decisions → Slice02 readiness。

不得实现 Slice02 vertical、public arrow extra、executor、GPU、native pointer fabrication、持续 timing service。
使用现有 CPython3.12/3.13，环境在精确外部根；core .venv 保持无 Arrow。每 case≤32 rows、process admitted
buffers≤8MiB；不为超限测试做巨大分配。PyArrow-to-PyArrow 协议通过不等于独立 C 实现认证。

## 命令与必需验证

普通 collection 不安装 Arrow、不 skip readiness。CI 的两 compiler/package jobs 各运行真实 probe 并验证
完整 case IDs/context/pin/script/requirements；两 Python completion 需要该 evidence。probe可在 fresh process 中运行：

```bash
/path/to/isolated/bin/python tests/_pietto_phase67_arrow_compatibility_probe.py --report /fresh/readiness.json
```

本地既有 guard 包装所有 heavy commands；统一 launcher 固定已核验项目解释器。一次等价 rehearsal 包含
五 static gates、独立 full U、四新鲜分区依次执行、coverage/descriptors/production/health 对账、generated/
golden/installed各一次以及两解释器真实 Arrow evidence。不得追加 monolithic validator 或 cold matrix。
小型 real xdist 验证 marker resolution、worker agreement 和 native load；depth-one检查 copied candidate imports。

## 三层验收

可观察：新 ordinary/marked tests 被正确安排；hard违规不能靠绿摘要隐藏；slow正确结果仍成功且给 advisory；
自然 CI UI/Job Summary/history 可见；真实 Arrow 实验解决委派选择，core仍无Arrow。
已存在：registry、coverage v2/health v1、hash-locked probe及耐久文档。
已连接：规范与 advisory 分离的完整 CI消费链、隔离安装至设计决策的实验链；自动改workflow刻意不连接。

## 外部参考处置（2026-09-25 snapshot）

| 组 | 问题／identity／layer／算法与界面 | 验证、代价、采纳／不复制／owner |
| --- | --- | --- |
| pytest/xdist | item marks 是要求；native load/loadfile 是 placement，不改 node ID | locked3.8.0＋tiny real workers；保留collection一致性；不复制custom scheduler；CI owner |
| GitHub Actions | current run与trusted main history分域；artifact raw bytes有size/digest/context | bounded GET、30日/10候选/3eligible、escaped Job Summary；不下载执行/自动改YAML；CI owner |
| Arrow/PyPI | Arrow type/buffer/capsule/stream不等于Pietto语义或SQL完成；released25.0.1 | 两runtime小实验；copy/borrow/EOS成本显式；不复制未知native pointer/GPU/全Table要求；Slices02/07/09/10/12/13 |

参考：[markers](https://docs.pytest.org/en/stable/how-to/mark.html)、
[distribution](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)、
[Job Summary](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands)、
[artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)、
[PyPI25.0.1](https://pypi.org/project/pyarrow/25.0.1/)、
[PyCapsule](https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html)、
[C stream](https://arrow.apache.org/docs/format/CStreamInterface.html)、
[IPC](https://arrow.apache.org/docs/format/Columnar.html)。

## 实验与完成记录

已真实观察：Linux x86-64/WSL，CPython3.12.13与3.13.13，PyArrow25.0.1；探索与最终rehearsal各一次fresh subprocess，
九组cases全部通过。两released manylinux_2_28 wheels共100,206,889 bytes，按官方SHA-256逐份核验，
在两个精确外部venvs以hash-locked/offline方式安装；core环境identity与无Arrow状态保留。
Windows/macOS仅有上游availability信息，没有Pietto测试支持承诺；不推测后续版本范围。

| case ID | 实测事实／规则／备选与局限 | next consumer |
| --- | --- | --- |
| types | int16/32/64、Bool/NULL、finite Float64及signed zero、Unicode、Decimal128(9,2)/256(65,3)、timestamp(us,无timezone)精确类型/值；不经float转Decimal | Slices02/04–08；Timestamp/UUID upstream meaning仍由Slice07先补witness |
| carriers | zero rows与typed all-null通过；duplicate labels可按位置保存；schema默认忽略metadata而显式比较可区分；nullable=False仍接受真实NULL，Pietto须独立检查 | Slices02/08；PIE-S2305不变 |
| adaptation | int16保持；显式safe→int64保值；超域narrowing拒绝 | Slice04；不宣称产品adapter完成 |
| strings | string与large_string不同类型，slice offset=1保留；metadata可保留/移除 | Slice05默认string；large_string只经显式binding，不按样本猜类型 |
| capsules | public schema/array/reader协议实际调用；释放exporter/reader后retained batch仍有效 | Slice10；仅PyArrow-backed CPU，不是独立C实现认证 |
| alias | 外部array backing变更可改变borrowed Arrow values；显式owned copy不受影响 | Slice10：owned为默认；合法capsule transferred由importer保留release责任；borrowed显式承诺lifetime/non-mutation |
| finite | empty batch后仍有数据，rechunk后有序值/NULL/multiplicity完全一致 | Slice09；normal finalization不是executor success，后者Phase68 |
| ipc | tiny roundtrip通过；mid-message截断拒绝；完整message边界截断被接受且只返回2/3行 | Slices09/12必须显式绑定预期完成/分母；不能靠Arrow EOF证明SQL result完整 |
| device | is_cpu与有效CPU buffers真实观察；C device API和Device类存在，无GPU执行 | Slice10保留device边界；synthetic非CPU拒绝仅policy negative |

UUID extension在本pin的C/PyCapsule及IPC均保持，因此选canonical Arrow UUID extension；explicit binary(16)
已作备选carrier witness但不作为隐式fallback。若以后pin改变此性质，需reviewed明确binding决策。
合同身份独立于任何buffer所有权/Arrow metadata；这些实验不实现ResultContract或producer adapter。

执行性CI/health/coverage验收与完整联合rehearsal仍须完成；最终publication事实只由Git、自然CI与外部seal/ledger给出。


## Gate2 实测与分项成本

一次完整CPython3.13.13等价rehearsal：16230 collected/selected/terminal，
全部passed、0 skips；shared-acquisition=315、plan-portability=3、emission-portability=3、general-runtime=15909。基线16,183个IDs全部保留，共增加47个CI/治理/lifecycle回归节点。
static五gates、generated/golden/installed均通过；四分区串行总campaign wall为826.439s，
这是本地serial范围，不能等同parallel hosted wall。guard on，无resource abort/recovery。

canonical shared store实测16个唯一cell，其余三分区0；所有worker观察完整，wheel/relocation preparation
单独计时，memo/synthetic stores不计入生产。health真实生成；本地无eligible hosted history，
输出INSUFFICIENT_EVIDENCE并保留current WATCH，不能补造旧样本。real xdist小套件20节点全量对账，
同文件的module/function/parameter一致marks在三个workers重叠执行。depth-one导入来自复制候选，
所有基线节点保留；integrated author/Ponytail review1＋follow-up1，重要finding已关闭。

| 已记录command wall范围 | 秒 | 说明 |
| --- | ---: | --- |
| CI-governance专属 | 5.697 | 四个tiny runtime invocations及独立collection；不是全部CI开发成本 |
| Arrow-readiness专属 | 9.479 | 两外部环境、hash-locked安装、两runtime探索及最终probe；每解释器2次 |
| joint-validation | 894.147 | 共用focused/static/shallow/review/full/auxiliary；不重复拆分计费 |

下载100,206,889 bytes／512MiB上限；下载墙钟未单独仪表化，不能记成0。源码阅读/作者时间不是上表command wall。
预算使用（publication前）：diagnostic2/6、focused9/12、correction3/6、full1/2、review/follow-up1/1、
environments2/2、Arrow3.12/3.13各2/3。首次focused失败和静态修正均保留在ledger，不重置计数。
本地DB/Docker、agents、detached heavy jobs、extra cold/heavy portability campaign均0。

三层Slice01本地证据闭合；最终普通commit/FF push、自然exact-head attempt1全15jobs及25份current raw
artifacts的事实，由Git/CI与外部终态ledger判定，不由此文档替代。core和native target inputs保持不变。
