# 知行伴学应用

安装、配置、功能与验证说明见仓库根目录 [README](../README.md)。

- 前端：`src/`；后端：`backend/`。
- 自编课程包：`backend/resources/contest-pack-v1/`。
- 本地启动：先创建 Python 环境并安装依赖，执行 `npm ci`，配置私有模型接口与分配账号，再运行 `Start-Study.ps1`。
- 自动化测试：`python -m pytest tests -q`；前端构建：`npm run build`。
- Linux 部署：`deploy/server/`；模型、账号和数据均由部署环境提供，不随代码提交。

实际服务是否可用以自检和真实请求为准，历史测试记录留在本机，不作为当前在线状态的保证。
