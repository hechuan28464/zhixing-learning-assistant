# 视频制作源码

`contest-video` 用于参赛功能介绍，`promo-video` 保留产品宣传片工程。使用 Remotion，设计参考项目已有视觉与 video-shotcraft 镜头流程。

仓库保留分镜、组件和制作脚本，不包含真实会话截图、生成语音、录屏、最终视频及本机验证数据。制作前需要自行采集可公开的项目截图，并按工程清单准备 `public/` 素材。

```powershell
Set-Location contest-video
npm install
npx remotion studio src/index.ts
```

阿里云配音脚本读取仓库根目录 `.env.voice.local`，可由 `.env.voice.example` 复制生成。不要提交真实凭据。旁白采用语音合成，不冒充真人录音；字幕及音轨需完成实际校对。

片尾入口与登录信息通过 Remotion 输入属性 `reviewerUrl`、`reviewerUsername`、`reviewerPassword` 提供，源码仅显示占位值。需要写入成片时，将属性存入未跟踪的 `*.private.json`，渲染时使用 `--props 文件路径`；不要把该文件上传仓库。

制作过程产生的 `out/`、`recordings/`、`fresh-full/`、语音和模型回执均留在本地。部分历史采集脚本使用本机浏览器路径与测试地址，需要按实际环境配置后运行。
