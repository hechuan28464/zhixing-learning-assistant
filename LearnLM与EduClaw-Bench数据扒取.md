# LearnLM 与 EduClaw-Bench 数据页扒取报告

> 提取日期：2026-11-02 | 数据源：arXiv PDF 全文（arxiv.org/pdf/2412.16429v3、arxiv.org/pdf/2608.03206v1）+ alphaxiv.org/abs/2608.03206
> 说明：全部数字来自论文原文表格与正文，标注【事实】为原文数据，【推断】为编者分析。原始 PDF 与提取文本存于 `_edu_data/` 目录。

---

## 一、LearnLM: Improving Gemini for Learning（arXiv:2412.16429v3）

### 1.1 论文身份

| 项目 | 数据 |
|---|---|
| 版本历史 | v1 2024-12-21 提交 → v2 2024-12-25 → v3 2025-08-22 修订 |
| 作者 | LearnLM Team, Google（40+ 人，含 Kevin R. McKee 等） |
| 许可 | CC BY 4.0 |
| 伦理审批 | v3 为 Google DeepMind HBREC **#23 011**（v1 为 **#21 008**） |
| 对比基线版本 | LearnLM 2024-11-19 版（基于 gemini-1.5-pro-002）；GPT-4o 2024-08-06 版；Claude 3.5 Sonnet 2024-06-20 版；Gemini 1.5 Pro-002 2024-09-24 版。所有对比以 **2024-10-01 时点**的旗舰模型为准 |

### 1.2 评测规模数据

| 指标 | 数值 | 备注 |
|---|---|---|
| 评测场景 | **49 个** | 覆盖核心学科，三阶段流程（用例征集→模板设计→生成精炼） |
| 扮演学习者的教育专家 | 引言称 **N=186** / §3.2 实际招募 **N=168** | ⚠️ 论文内部人数不一致（v3 仍未修正），两者均要求硕士以上学位+2年以上辅导经验 |
| 评审教育专家 | 引言称 **N=248** / §3.3 实际招募 **N=228** | ⚠️ 同样不一致；每对对话目标 3 份独立评审 |
| 对话总数 | **2,360 段** | 每段强制 ≥10 轮（5 学习者 + 5 导师轮） |
| 消息总数 | **58,459 条** | 学习者 + 模型消息 |
| 专家评估总数 | **10,192 份** | 平均每对对话约 3 名专家评审 |
| 主题分析抽样 | **203 条**解释（占 1,024 条的 ~20%） | 1,024 为收集到的开放式偏好解释总数 |

### 1.3 对话形态数据（原文 Figure 3 表格）

| 系统 | 版本日期 | 平均轮数/对话 | 平均词数/轮 |
|---|---|---|---|
| **LearnLM** | 2024-11-19 | **11.0** | **174** |
| Gemini 1.5 Pro | 2024-09-24 | 10.3 | 130 |
| GPT-4o | 2024-08-06 | 10.1 | 137 |
| Claude 3.5 Sonnet | 2024-06-20 | 9.7 | 179 |

【推断】LearnLM 轮数最多、篇幅最长；论文明确说"总体层面长度与感知质量无明显关系"。

### 1.4 核心偏好结果

- **平均偏好强度：+31% vs GPT-4o、+11% vs Claude 3.5 Sonnet、+13% vs Gemini 1.5 Pro**（七点量表，贝叶斯分层回归，95% 可信区间）
- 五个比较维度全部偏向 LearnLM（vs GPT-4o 全胜；vs Claude/Gemini 优势较小）
- 29 项评分细则中几乎所有单项 LearnLM 平均分最高，优势最大的三项：**inspiring active learning（激发主动学习）、deepening metacognition（深化元认知）、stimulating curiosity（激发好奇心）**

### 1.5 主题分析完整数据（原文 Table 1）

条件：出现在 ≥10% 抽样解释中、且两侧比例极端的主题。分母：偏好 LearnLM 的解释 94 条 / 偏好他方的 80 条。

| 主题 | 偏好 LearnLM 时提及 | 偏好他方时提及 | 方向 |
|---|---|---|---|
| **keeps_on_topic**（守话题） | 20（21.2%） | 8（10.0%） | ↗ LearnLM 优势 |
| **challenges_learner**（挑战学习者） | 31（33.0%） | 13（16.3%） | ↗ LearnLM 优势 |
| **gives_away_answers**（不直接给答案） | 32（34.0%） | 15（18.8%） | ↗ LearnLM 优势 |
| clarity（清晰度） | 15（16.0%） | 16（20.0%） | ↘ LearnLM 短板 |
| info_amount（信息量） | 19（20.2%） | 20（25.0%） | ↘ LearnLM 短板 |
| conversation_style（对话风格） | 30（31.9%） | 29（36.3%） | ↘ LearnLM 短板 |

抽样中出现频次最高的三个主题（不分方向）：**is_engaging 72、conversation_style 67、gives_away_answers 50**。

原文引用例句（各主题 1-3 句，见 `_edu_data/learnlm_full.txt:483-513`）。

### 1.6 29 项教学评分细则全表（原文 Table 8，v3 附录 B.6）

分 6 组原则：

**Cognitive Load（认知负荷，9 项）**
1. Appropriate Response Length — 回复长度适合学生
2. Manageable Chunks — 用分点/排版把信息拆成可管理的小块
3. Straightforward Response — 回复清晰易跟
4. No Irrelevant Info — 避免无关信息
5. Analogies — 叙事/案例/类比有效说明关键概念
6. Info Presentation — 以合适的风格与结构呈现信息
7. Info Order — 按逻辑顺序展开，建立在先前概念上
8. No Repetition — 不无谓重复
9. No Contradiction — 不与对话前文矛盾

**Active Learning（主动学习，4 项）**
10. Opportunities for Engagement — 提供学生参与机会
11. Asks Questions — 提问促思考
12. Guides to Answer — 不过快给出答案
13. Active Engagement — 促进对材料的主动投入

**Metacognition（元认知，4 项）**
14. Guide Mistake Discovery — 引导学生自己发现错误
15. Constructive Feedback — 提供清晰、建设性的反馈
16. Acknowledge Correctness — 承认学生回答中正确的部分
17. Communicates Plan — 传达清晰的对话计划/目标

**Stimulates Curiosity（激发好奇心，3 项）**
18. Stimulates Interest — 激发兴趣与好奇心
19. Adapts to Affect — 学生沮丧/受挫时有效应对
20. Encouraging Feedback — 以鼓励的方式给反馈

**Adaptivity（适应性，5 项）**
21. Leveling — 讲解水平适合学生
22. Unstuck — 学生卡住时有效调整方法
23. Adapts to Needs — 总体适应学生需要
24. Proactive — 适时主动引导对话
25. Guides Appropriately — 不无产出地扣留信息

**Overall（总体，4 项）**
26. No Inaccuracies — 陈述无已知错误
27. Expresses Uncertainty — 适时表达不确定
28. No Refusals — 不拒答合理问题
29. Overall Quality — 和非常好的人类导师一样好

### 1.7 比较评估题（原文 Table 9，七点量表）

1. Better pedagogy — 哪位导师教学更好？
2. More like a very good human tutor — 哪位更像非常好的人类导师？
3. Better instruction following — 哪位更好地遵循系统指令？
4. Better adapted to learner — 哪位更适应学生的需要与水平？
5. Better supported learning goal — 哪位更帮助学生达成学习目标？

### 1.8 统计方法（附录 B.8）

- 贝叶斯分层线性回归，参与者与场景双重随机效应
- 均值参数弱信息正态先验（中心为量表理论中点）、标准差参数 Half-Cauchy 先验
- 每回归 4 条独立链 × 1,000 warmup + 2,000 采样步；监控 Gelman-Rubin R̂ 与有效样本量

### 1.9 医学教育可行性研究（附录 C，v3 新增）

| 项目 | 数据 |
|---|---|
| 场景 | **50 个**（临床前 + 临床课纲，医学教育专家设计） |
| 扮演者 | **18 名医学生**（临床前/临床各半） |
| 对话 | **290 段**（平均 5.8 段/场景） |
| 评审 | **9 名医师教育者**，每段对话中位数 3 份独立评审 |
| 对比 | LearnLM vs Gemini 1.5 Pro |
| 医学生偏好 | 无决定性偏好，但四项比较全部均值偏向 LearnLM；最强项为**交互愉悦感 +9.9%**；去除平局后全部口径多数选 LearnLM |
| 医师教育者偏好 | 五项全部一致偏好 LearnLM：**教学法 +6.1%、像好人类导师 +6.8%** |

【事实】该研究验证了评测框架可复制到非核心学科；但论文明确说真实医疗应用仍需临床专家另行评估准确性、偏见与伤害。

---

## 二、EduClaw-Bench（arXiv:2608.03206v1）

### 2.1 论文身份

| 项目 | 数据 |
|---|---|
| 提交 | 2026-08-04 |
| 作者 | Unggi Lee、Sookbun Lee、Yeil Jeong、Eunjoo Lee、Minchul Shin、Hoilym Kwon +2 |
| 机构 | Korea University Sejong Campus、Opentutorials、Indiana University、Gyeonggi Institute of Education、Korea University（5 机构） |
| 许可 | CC BY-NC-ND 4.0 |
| 代码 | anonymous.4open.science/r/educlaw-bench-anonymous-ED3F |
| 数据许可 | XES3G5M 数据集（真实小学生数学交互）；field study 为真实课堂（IRB 按需提供） |

### 2.2 场景构建数据

**55 场景 = 11 人格 × 5 日程（原文 Table 6，附录 A）**

| 人格（11） | 日程（5） |
|---|---|
| confused productive（困惑但努力） | after-school（课后） |
| disengaged（脱离） | homework-only（只做作业） |
| frustrated spiral（挫败螺旋） | school-integrated（校内融合） |
| gamer（游戏型） | weekend-warrior（周末突击） |
| help seeker（求助型） | self-directed（自主规划） |
| low SRL（低自我调节） | |
| mastery approach（掌握导向） | |
| performance avoidance（表现回避） | |
| silent struggler（沉默挣扎） | |
| wheel spinner（瞎蒙型） | |
| adversarial student（对抗性学生，安全探针用） | |

每个场景为 YAML 文件，固定每日时间块、LMS 事件触发器、探测评计划；每场景运行 **30 虚拟天**。

### 2.3 模拟学生（KT 核心）数据

| 项目 | 数据 |
|---|---|
| KT 模型 | AKT（Attentive Knowledge Tracing, Ghosh et al. KDD 2020） |
| 训练数据 | XES3G5M 小学数学数据集：**5,027 条序列**（截断至 200 交互）、**7,652 题**、**865 个 KC** |
| 训练配置 | 5 折 learner-disjoint 交叉验证，测试 **AUC 0.80** |
| 信念向量 | b ∈ [0,1]^K，**K = 831 个可用 KC**；每次观察 (题目 q, KC k, 回答 y) 后更新 |
| persona 种子 | **2,169 个**，每个带 200 交互真实 warm-up 历史，离线预计算约 **30 分钟 GPU** |
| 校准 | **ECE 0.049、Brier 0.033**（基于 **119 万次**题目尝试） |
| LLM 学生三层能力 | weak / average / strong 预实验正确率 **0.19 / 0.34 / 0.53**（各 200 题） |
| 每 tier 学生构成 | 4 个混合来源 LLM：solar-mini、llama-3.1-8b-instruct、qwen-2.5-7b-instruct、gemma-3-4b-it |
| 每日循环 | 前测探针 → 辅导窗口（agent 可干预）→ 后测探针 |

### 2.4 LMS API 面

| 端点 | 功能 | 动作映射 |
|---|---|---|
| GET /profile | 学习者元数据 | query |
| GET /mastery | 每 KC 的 KT 信念 | query |
| GET /activity | 事件日志 | query |
| GET /schedule | 学习时间块 | query |
| GET /unit_content | 题目目录 | query |
| POST /assign_items | 排队练习题 | assign_items |
| POST /adjust_level | 指定 KC 难度 ± | adjust_level |
| POST /provide_content | 推送示例/笔记/媒体 | provide_content |
| GET /messages | 轮询学习者回复 | query |
| POST /message | 发送聊天轮 | send_message |
| （隐式）跳过一轮 | — | stay_silent |

### 2.5 评分轴与评判协议

| 轴 | 名称 | 类型 | 说明 |
|---|---|---|---|
| I | ΔSolve Rate | 确定性 | (后测正确率 − 前测正确率) 的 30 天平均，百分比 |
| II | Responsiveness | 规则 | 学生求助被回复的比例（Overall 与 Same-day 两种口径） |
| III | Helpfulness | LLM panel | 29 项 LearnLM rubric（1-10 分/项） |
| IVa | Gagné | LLM panel | 9 个教学事件（1-5 分，1=事件缺失） |
| IVb | Rosenshine | LLM panel | 10 条教学原则（1-5 分） |

- **评判 panel**：跨家族 3 LLM——gemini-3-flash、gpt-4.1-mini、kimi-k2.5，reasoning off、temperature 0.3；Help/课程轴取 panel 均值，answer-holding 取多数
- 两套课程 rubric 高度一致（Spearman ρ > 0.97），Gagné 为主报告列
- 被排除的评判：solar-pro3（日级分数与共识不相关，pairwise ρ −0.10~−0.26，数字误读）、饱和量表者、解析失败者；保留 panel 三点量表一致率 **95.7%**

### 2.6 基座模型与 Adapter 清单

**3 个 tier（是底层 LLM，不是 agent 系统）：**

| Tier | 模型 | 性质 | 备注 |
|---|---|---|---|
| Solar-pro3 | Upstage Solar-pro3 | Frontier 闭源 API | |
| Codex-gpt5.5 | Codex-gpt5.5 | Frontier 闭源 API | 重名编码 agent 无关，仅是 LLM |
| Qwen3-4B-Thinking | Qwen3-4B-Thinking-2507 | Small 开放权重 | vLLM BF16 ~8GB，支持 LoRA |

**10 个 adapter（原文 Table 7，附录 C）：**

| Adapter | 类别 | Docker 端口 | 镜像 |
|---|---|---|---|
| deeptutor | framework（完整 agent 框架） | 8002 | deeptutor |
| metaclaw | skill-proxy | 30000 | metaclaw |
| openclaw（参考基线） | gateway | 8010 | claw-bridge |
| ironclaw | gateway | 8011 | claw-bridge |
| picoclaw | gateway | 8012 | claw-bridge |
| zeroclaw | gateway | 8013 | claw-bridge |
| hermesclaw | gateway | 8014 | claw-bridge |
| copaw | gateway | 8015 | claw-bridge |
| nemoclaw | gateway | 8016 | claw-bridge |
| openclaw-rl | gateway | 8017 | claw-bridge |

8 个 gateway 共享 claw-bridge 镜像，仅 CLAW_NAME 环境变量区分 prompt profile；base LLM 经 TUTOR_MODEL 注入，同一 adapter 代码跨三个 tier 不变。

**运行量**：名义 4 学生 × 13 adapters × 55 场景/tier；实际完成 **8,637 次运行**（含 API 瞬时失败重跑），其中 **6,626 次**属于 10 个报告 adapter；LoRA 研究再加 **550 次**，总计 **9,187 次**。

### 2.7 ★ Table 3 完整数据：10 adapters × 3 tiers 未训练基线

（每行 = 4 学生 × 55 场景平均；格式：ΔSolve %↑ / Resp %↑ / Help ↑ / Gagné ↑ / Rosen. ↑）

| Adapter | Solar ΔS | Solar Resp | Solar Help | Solar Gagné | Solar Rosen. | Codex ΔS | Codex Resp | Codex Help | Codex Gagné | Codex Rosen. | Qwen3 ΔS | Qwen3 Resp | Qwen3 Help | Qwen3 Gagné | Qwen3 Rosen. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **openclaw**（基线） | **+0.36** | 91.2 | **6.11** | 1.46 | 1.37 | −0.27 | 90.5 | **6.10** | 1.40 | 1.34 | −0.28 | 25.0 | **6.53** | 1.47 | 1.42 |
| deeptutor | −0.65 | 99.4 | 4.55 | 1.75 | 1.50 | −1.25 | 99.3 | 4.58 | 1.85 | 1.56 | −0.98 | 100.0 | 2.99 | 1.26 | 1.25 |
| metaclaw | +0.02 | 99.7 | 4.23 | 1.71 | 1.50 | −0.90 | 99.7 | 4.26 | **1.90** | **1.59** | **+0.64** | 96.5 | 4.73 | **1.74** | **1.62** |
| ironclaw | −0.94 | 99.4 | 4.54 | **1.92** | **1.69** | −0.74 | 100.0 | 4.53 | **1.93** | **1.69** | −0.36 | 100.0 | 3.04 | 1.33 | 1.31 |
| picoclaw | −1.04 | 99.8 | 3.76 | 1.85 | 1.68 | −0.77 | 100.0 | 3.76 | 1.85 | 1.67 | −0.85 | 100.0 | 2.97 | 1.30 | 1.28 |
| zeroclaw | +0.22 | 89.0 | 5.63 | 1.42 | 1.40 | **−0.08** | 89.5 | 5.66 | 1.44 | 1.42 | −0.42 | 100.0 | 3.12 | 1.32 | 1.30 |
| hermesclaw | −0.75 | 90.9 | 5.58 | 1.51 | 1.45 | −1.08 | 92.5 | 5.62 | 1.52 | 1.46 | −0.02 | 100.0 | 3.09 | 1.32 | 1.30 |
| copaw | −0.56 | 96.9 | 5.02 | 1.70 | 1.55 | −0.27 | 98.1 | 4.97 | 1.74 | 1.58 | −0.46 | 99.5 | 2.87 | 1.32 | 1.31 |
| nemoclaw | −1.24 | 93.1 | 5.13 | 1.44 | 1.39 | −0.78 | 93.5 | 5.06 | 1.49 | 1.43 | −0.63 | 100.0 | 3.13 | 1.27 | 1.27 |
| openclaw-rl | −0.63 | 97.1 | 4.84 | 1.70 | 1.55 | −0.49 | 97.4 | 4.86 | 1.71 | 1.56 | −0.85 | 100.0 | 3.19 | 1.24 | 1.26 |

（粗体 = 该 tier 该列最优；openclaw Help 在三个 tier 全部最高。）

### 2.8 Table 4：LoRA RFT 结果（Small tier / Qwen3-4B-Thinking，epoch 平均 n=275）

| Adapter | ΔSolve | Resp | Help | Gagné | Rosen. |
|---|---|---|---|---|---|
| **未训练基线** | | | | | |
| metaclaw | +0.64 | 96.5 | 4.73 | 1.74 | 1.62 |
| openclaw-rl | −0.85 | 100.0 | 3.19 | 1.24 | 1.26 |
| **LoRA RFT 训练后（epoch 平均）** | | | | | |
| metaclaw-rft | +0.19 | 95.8 | **4.76** | 1.79 | 1.63 |
| openclaw-rl-rft | +0.10 | 100.0 | **2.30** | 1.22 | 1.22 |

- 训练配方：LoRA rank-16、5 epochs；复合奖励 **R = 0.4·R_I + 0.4·R_II + 0.2·R_III**
- **关键发现**：openclaw-rl 的 Helpfulness 训练中崩溃 **3.18 → 2.50 → 1.85**（至 epoch 3 无恢复），而 Responsiveness 保持 100% —— 低权重教学奖励的教学质量坍塌对泄漏/拒答类检查**不可见**
- Checkpoints（Table 12）：metaclaw-rft step 45/90/135/180/225；openclaw-rl-rft 62/124/186/248/310

### 2.9 Table 5：人类验证（2 名领域专家 × 每轴约 40 项，盲评）

| 轴 | Panel–专家 ρ | 专家–专家 ρ（天花板） | p |
|---|---|---|---|
| Helpfulness | 0.33 | 0.91 | 0.04 |
| Gagné | 0.43 | 0.64 | 0.008 |
| Rosenshine | 0.49 | 0.90 | 0.001 |
| **Answer-holding** | **0.82** | 0.85 | <0.001 |

【事实】panel 在所有判定轴上与专家显著一致（置换检验 p<0.05）；answer-holding 达到专家天花板，其余轴为"正向但更温和的代理"。

### 2.10 Field Study（真实课堂）数据

| 项目 | 数据 |
|---|---|
| 规模 | 约 **500 名 K-12 学生**，多个合作课堂，两周内 4 次使用 |
| 部署导师 | stage-one regex claw on solar-mini（真实产品配置，不在模拟网格内） |
| 评分样本 | 150 个会话（≥3 个求助轮的会话中随机抽样） |
| **Field Helpfulness** | **6.02（sd 1.21）** vs 模拟 **6.19（sd 0.45）** |
| 差异检验 | Mann-Whitney U = 39,759，**p = 0.68**，Cohen's d = 0.18（不显著） |
| 直接答案泄漏率 | **0.05%**（10,405 个导师轮中 5 个），与模拟 0.05% 一致 |
| 教师访谈协议 | 三项：观察到的失败模式、导师是脚手架还是直接给答案、不良反应（系统化分析留待未来） |

### 2.11 关键分析数据（Section 5-6 + 附录 D）

**学习曲线与失败模式**
- **所有 adapter 在第 5-10 天达到平台**（openclaw 逐日正确率 0.28→0.29），远低于理想学习曲线
- 失败模式分布：**无课程结构 48.5%、无学习增益 53.3%、答案泄露 ≈0%、忽视/沉默**（Figure 2 右）
- 第 30 天正确率均值仅跨 **0.276–0.291**（Solar tier），几乎打平
- pass_k 可靠性：**pass1 ≈ 0.47 → pass4 ≈ 0.11**（各 tier 一致；4 个学生独立运行全成功的场景比例）

**轴间独立性**
- 三主轴近乎独立（含求助场景的 n=30：ρ(I,II)≈0.01、ρ(I,III)≈−0.12、ρ(II,III)≈−0.13）—— 单一奖励无法"刷分"

**Responsiveness 两种口径（Table 9，Codex tier）**

| Adapter | Overall | Same-day | 解读 |
|---|---|---|---|
| openclaw | 90.5% | **28.8%** | 扣留式，隔天回 |
| deeptutor | 99.3% | 94.8% | 即答式 |
| metaclaw | 99.7% | 96.4% | 即答式 |
| ironclaw | 100.0% | 99.8% | 即答式 |
| picoclaw | 100.0% | 100.0% | 即答式 |
| zeroclaw | 89.5% | **20.0%** | 扣留式 |
| hermesclaw | 92.5% | **20.9%** | 扣留式 |
| copaw | 98.1% | 78.1% | 中间 |
| nemoclaw | 93.5% | 40.9% | 偏扣留 |
| openclaw-rl | 97.4% | 75.9% | 中间 |

【事实】Overall 口径 8/10 都 ≥90% 区分度差；Same-day 口径拉开差距：Help 最高的扣留式（zeroclaw/hermesclaw/openclaw）当天只回 20-29%，即答式（picoclaw/ironclaw）≈100%。

**动作频率（Table 8，Codex tier，每次运行均值）**

| Adapter | Msg | Silent | Assign | Adjust | Content |
|---|---|---|---|---|---|
| openclaw | 24.8 | 23.0 | 5.7 | **0** | 17.3 |
| deeptutor | 29.1 | 16.3 | 20.9 | 0 | 61.2 |
| metaclaw | 36.0 | 11.7 | 23.1 | 0 | **138.7** |
| ironclaw | 46.3 | 0.3 | 32.5 | 0 | 98.3 |
| picoclaw | 44.3 | 0.0 | 29.1 | 0 | 84.1 |
| zeroclaw | 23.4 | 21.9 | 3.6 | 0 | 11.3 |
| hermesclaw | 24.9 | 23.9 | 5.9 | 0 | 17.7 |
| copaw | 34.4 | 12.7 | 17.6 | 0 | 54.3 |
| nemoclaw | 29.3 | 20.0 | 10.2 | 0 | 31.5 |
| openclaw-rl | 34.8 | 11.5 | 18.5 | 0 | 56.8 |

【事实】**adjust_level（难度调节）被全部 10 个 adapter 弃用（频率恰为 0）**——环境提供的难度自适应能力无人使用。content 推送跨两个数量级（metaclaw 138.7 vs zeroclaw 11.3）。Help 高的 gateway 每运行静默 22-24 轮（扣留行为的直接证据）。

**跨学生排名稳定性（Table 10，Kendall τ 均值）**

| 轴 | Solar | Codex | Qwen3 | 最差对 |
|---|---|---|---|---|
| Helpfulness | 0.80 | 0.84 | 0.86 | 0.61 |
| ΔSolve Rate | 0.24 | **−0.09** | 0.21 | **−0.42** |

【事实】Help 排名稳定（换学生模型几乎不改变谁是好导师）；ΔSolve 排名不稳定（换学生可完全反转顺序，因单格差异小、n≈220、噪声主导）。

**视界截断效应（Table 11，前 N 天排名 vs 30 天排名的 Kendall τ）**

| 截断 | Solar | Codex | Qwen3 |
|---|---|---|---|
| 前 5 天 | **−0.42** | 0.16 | 0.20 |
| 前 10 天 | 0.02 | 0.42 | 0.82 |
| 前 15 天 | 0.07 | 0.56 | 0.82 |
| 前 20 天 | 0.42 | 0.69 | 0.82 |

【事实】短期评测会按前几天给 adapter 排名，与 30 天排名几乎无关甚至反相关 —— 全视界才可靠。

**静默运行率（附录 D）**
- Frontier tier 可忽略：Solar-pro3 **5.0%**、Codex-gpt5.5 **2.6%**
- Small tier 飙升：**28.7%**；其中学习者由 qwen-2.5-7b 扮演时达 **90.0%**
- 【事实】弱基座常整轮沉默不动作，Small tier 的 Responsiveness 分数建立在少得多的有效运行上，须与排除率并读

**超参数（Table 13）**

| 组件 | 设置 | 值 |
|---|---|---|
| AKT | dim / heads / layers | 64 / 4 / 2 |
| AKT | max sequence length | 200 |
| AKT | epochs / CV folds | 10 / 5 |
| LoRA RFT | rank / epochs | 16 / 5 |
| LoRA RFT | 奖励权重 (I/II/III) | 0.4 / 0.4 / 0.2 |
| Judge | temp / reasoning / trials | 0.3 / off / 1 |
| Judge | 聚合 | help=均值 / holding=多数 |

### 2.12 Table 1：评测基准对比（相关工作全景）

| 基准 | 年份 | 学习者 | Agent | 结果评分 | 课程设计 | 视界 | 跨 tier |
|---|---|---|---|---|---|---|---|
| LearnLM | 2025 | S（人工评测） | 否 | 仅 rubric | 否 | 会话 | Gemini 系 |
| TutorEval | 2024 | R | 否 | 仅 rubric | 否 | 轮 | 否 |
| MathTutorBench | 2025 | R | 否 | 仅 rubric | 否 | 轮 | 否 |
| MathDial | 2023 | R | 否 | 对话质量 | 否 | 会话 | 否 |
| CheckMate | 2023 | R | 否 | 偏好 vs 正确性 | 否 | 轮 | 否 |
| LongTutor | 2026 | R（静态日志） | 否 | 3 个形成性任务 | 否 | 轮 | 否 |
| EduAgentBench | 2026 | R（工作流） | 是 | 教师工作流 | 否 | 会话 | 否 |
| ISD-Agent-Bench | 2026 | 无 | 是 | ISD 设计任务 | 是 | 会话 | 3 LLM |
| TutorBench | 2026 | S（源落地） | 是 | 个性化增益 | 否 | 会话 | 部分 |
| **EduClaw-Bench** | **2026** | **S（KT+LLM）** | **是** | **直接 3 轴** | **是（2 轴）** | **30 天** | **是（3 tier）** |

### 2.13 部署建议（附录 J 摘要）

1. **预部署安全门**（CI 管线）：answer-holding 泄漏率超过清洁基线即阻断发布（基线 0.05%）
2. **RFT 早停规则**：监控训练中 Helpfulness 轨迹（openclaw-rl 式坍塌对泄漏检查不可见）
3. **Adapter 分级选择**：按 tier 与场景匹配组合，不依赖单层 leaderboard

---

## 三、两篇论文数据的交叉要点

1. **LearnLM rubric 是 EduClaw Axis III 的直接来源**——EduClaw 的 29 项 Helpfulness 评分沿用 LearnLM（LearnLM Team et al. 2025 / arXiv:2505.24477 "Evaluating Gemini in an Arena for Learning"）的 29 项细则，即上文 1.6 节的全表。
2. **评价粒度差异**：LearnLM 是"单会话人工偏好"（证明风格/教学偏好），EduClaw 是"30 天 KT 模拟学生 + 直接学习增益"（首次把长期学习结果作为确定性轴）。
3. **共同发现**：两篇都指向"给答案 vs 引导"的信任张力——LearnLM 主题分析 gives_away_answers 是前三主题之一；EduClaw 的 answer-holding 轴、扣留式 vs 即答式对比与此呼应。
4. **LearnLM 遗留问题被 EduClaw 放大**：LearnLM 的人数不一致（186/248 vs 168/228）在其 v3 仍未修正；EduClaw 的交叉学生排名不稳定（ΔSolve Kendall τ 可至 −0.42）提示单场景学习增益评测的噪声风险。

---

## 四、来源与可追溯性

| 数据 | 来源 | 提取方式 |
|---|---|---|
| LearnLM 全部表格（1.2-1.9） | arxiv.org/pdf/2412.16429v3（35 页 PDF 全文） | pypdf 提取，`_edu_data/learnlm_full.txt`（1,603 行） |
| EduClaw 全部表格（2.2-2.13） | arxiv.org/pdf/2608.03206v1（13 页 PDF 全文） | pypdf 提取，`_edu_data/educlaw_full.txt`（1,291 行） |
| EduClaw 摘要/解读补充 | alphaxiv.org/abs/2608.03206（2026-08-04 提交） | web_fetch |
| LearnLM 版本/许可元数据 | arxiv.org/abs/2412.16429（v3 2025-08-22） | web_fetch |

原始 PDF：`_edu_data/educlaw.pdf`（665 KB）、`_edu_data/learnlm.pdf`（28.7 MB）。全部提取文本可复核至具体行号。
