# 知行伴学

面向自主学习与实训教学的跨学科 AI 伴学项目，连接课程任务、资料引用、学习记录、视频字幕和项目实践。

## 项目功能

- **学习伙伴林知**：读取实际学习上下文，按需检索材料、引用原文、建议下一步任务；支持发送、停止和失败重试。
- **个性化学习流程**：诊断、候选错因、针对性补救、换题复核；分别呈现独立表现、帮助程度、目标覆盖和保持依据。
- **课程广场**：编程、统计学、批判性阅读三条路线。当前内容包包含 46 个单元、224 个任务和 123 个检查目标，讲义与题目为项目自编，课程结构参考公开课程与教材目录。
- **知识空间**：检索材料、笔记、对话和学习记录；保留来源、段落与版本，学习记忆经用户确认后使用。
- **视频研学**：视频来源解析、字幕导入与检索、分页、时间点引用、总结及导图任务。平台是否允许读取字幕、模型及执行环境是否可用，以实际运行结果为准。
- **项目式学习 PBL**：基于 OpenMAIC 状态机适配七阶段流程，保存计划、代码、审阅和执行回执。
- **访问与用量控制**：预分配账号登录，无公开注册；付费 AI 操作受登录与每日用量限制保护。

这是共享单机学习工作区，账号访问保护不等同于完整多租户数据隔离。项目依据实际保存的学习行为提供帮助，不宣称已经证明长期提分效果。

## 目录

```text
app/src/                       Vue 前端
app/backend/                   FastAPI、学习证据、Agent、PBL 与视频服务
app/backend/resources/         自编内容包及判定规则（由后端使用）
app/public/assets/             网站图片和图标
app/integrations/openmaic/      状态机桥接及第三方许可证
app/vendor/openmaic-v1.4.0/     必需的上游状态机源码
app/deploy/                    Linux/Docker 部署与隔离执行器
app/tests/                     自动化测试
scripts/                       配置与内容校验工具
contest-video/                 参赛视频制作源码
promo-video/                   产品宣传片制作源码
```

仓库不包含 API 密钥、服务器登录信息、私有数据库、验证截图、视频音轨或导出成品。视频工程需要自行准备素材，参见 [视频制作说明](docs/VIDEO.md)。

## 本地运行

建议使用 Python 3.12 和 Node.js 24，在仓库根目录执行：

```powershell
Copy-Item .env.example .env.local
Set-Location app
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm ci
Set-Location ..
app\.venv\Scripts\python.exe scripts/create_local_account.py --username reviewer
```

在 `.env.local` 填入自己的 OpenAI 兼容模型接口、密钥与模型名称。需要启用 AI 和初始导学内容时，在启动的 PowerShell 中执行：

```powershell
$env:STUDY_AI_ENABLED = '1'
$env:STUDY_SEED_STARTER_CONTENT = '1'
$env:LLM_TIMEOUT_SECONDS = '240'
Set-Location app
.\Start-Study.ps1
```

访问前端 `http://127.0.0.1:5173/`，后端接口文档 `http://127.0.0.1:8765/docs`。若已有私有 `local-runtime.json`，启动脚本会读取其中的 AI 开关。初始导学仅创建课程目标和资料，不伪造作答、对话或掌握记录。

## 验证与部署

```powershell
Set-Location app
.\.venv\Scripts\python.exe -m pytest tests -q
node --test tests/*.test.mjs
npm run build
```

Linux 从源码部署使用 `app/deploy/server/compose.yml`；`compose.runtime.yml` 面向带有预构建前端和离线依赖的运行包。修改模型配置后需重新创建 API 容器以加载新环境变量，保留原有数据卷。配置存在不代表模型网络、额度或生成已经通过验证。

第三方组件沿用各自许可证，见 [第三方说明](docs/THIRD_PARTY.md)。
