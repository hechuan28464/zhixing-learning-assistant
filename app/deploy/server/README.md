> 2026-11-08更新：当前交付入口为服务器IP http://82.156.213.51/ 。预分配账号配置只在数据卷`/data/auth-users.json`，仅含盐和PBKDF2-SHA256哈希；登录会话及每日用量在`/data/auth.sqlite3`，与学习库分开。无注册接口。`STUDY_REQUIRE_LOGIN=1`、`STUDY_AI_ENABLED=0`，模型密钥保留为空。登录后仍不执行模型调用；后续启用需用户明确要求、填写有效配置并重建API容器。默认每日20次AI操作，可在私有账号配置的`daily_model_limit`调整。登录口令错误5次后限流五分钟，Cookie为HttpOnly/SameSite=Strict。当前IP为HTTP，账号传输不具备HTTPS加密，不能描述为加密登录。

# Linux竞赛部署与运行

实际站点：https://xl.888456.xyz/ 。服务器Ubuntu22.04，2核/2GB；Docker27.0.3与Compose2.28.1。项目部署在`/opt/zhixing-competition-20261107`，保留原1panel应用。

## 当前验收

web、api、runner均已运行，域名由既有CDN提供HTTPS，回源80。39任务内容包已加载，schema版本2。真实Docker执行、错误/超时处理、7阶段状态机和重启持久化已在独立库验证。教学审阅在执行器验收中使用明确标注的夹具；真实模型服务返回HTTP402，完整真实AI闭环仍待有效普通API凭据。

## 使用已构建运行包

将`zhixing-runtime-20261107.zip`解压到项目目录，保留`app/`与`scripts/`相对路径。首次部署在`app/deploy/server`使用`python3 prepare.py`创建私有`.env.server`，不要把凭据写入源码。实际已部署服务器保留现有配置，不重复执行prepare。

```sh
cd /opt/zhixing-competition-20261107/app/deploy/server
docker pull python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54
docker compose -p zhixing-competition --env-file .env.server -f compose.runtime.yml config --quiet
docker compose -p zhixing-competition --env-file .env.server -f compose.runtime.yml up --build -d
```

运行包包含已构建Vue文件、OpenMAIC状态机桥和对应Linux CPython3.12依赖wheelhouse。Docker构建离线安装Python依赖；基础镜像仍需已拉取或能够访问镜像仓库。镜像digest与wheelhouse manifest固定了此次验证版本。

`compose.runtime.yml`发布80与本机8080。CDN已有域名回源80；API通过nginx同源代理，响应不缓存。runner不发布端口，api不挂载Docker socket。站点不发布设计预览或素材画廊。

## 常用操作

```sh
# 查看容器状态
docker compose -p zhixing-competition --env-file .env.server -f compose.runtime.yml ps
# 单纯重启，不读取新的env_file
docker compose -p zhixing-competition --env-file .env.server -f compose.runtime.yml restart api
# 修改模型配置后重新创建API容器，保留数据卷
docker compose -p zhixing-competition --env-file .env.server -f compose.runtime.yml up -d --force-recreate api
```

`.env.server`权限为600，绝不打印完整Compose配置或环境变量。修改模型后必须小额真实测试；health中的configured只是配置存在，不代表余额、网络或生成可用。

## 数据与任务

SQLite保存在`zhixing-competition_learning-data`卷的`/data/learning.sqlite3`。升级前使用SQLite备份API生成一致性备份，迁移事务失败不会留下半成品。不得通过删除卷来排错。独立Linux验收库位于同卷的`/data/qa/`，不作为真实学生记录。

PBL运行先返回202/job_id，状态为pending/running/passed/failed/unknown/cancelled。停止等待后不采用迟到结果；执行容器仍按限额结束。服务重启将未完成任务标记unknown，不自动再次执行。

运行器将每份学习代码放入临时容器：非root、禁网络、只读根目录、不挂载宿主目录、去除capabilities、128MB内存、0.5CPU、32进程、64文件描述符、单用例6秒。执行后清理容器。模型密钥没有传给执行服务或学习容器。

该产品按竞赛方案使用共享单机空间，未实现账号或多租户隔离；完整OpenMAIC Next.js/PostgreSQL/E2B平台没有整体部署。不能把测试夹具、容器检查或短期作答描述为真实模型成功或长期学习效果。

更多证据：`app/test-reports/implementation-v2-20261107/REPORT.md`；模型配置说明位于工作区`实施方案附件/百炼模型配置说明_20261107.md`。
