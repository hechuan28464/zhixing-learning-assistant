"""Run on the user's Linux server; secrets are entered locally, never printed."""
import getpass,os,secrets
from pathlib import Path
from urllib.parse import urlparse
root=Path(__file__).resolve().parent
destination=root/'.env.server'
if destination.exists():raise SystemExit('已有 .env.server，保留现有配置，不会覆盖。')
base=input('模型 API HTTPS 地址：').strip().rstrip('/')
if urlparse(base).scheme!='https':raise SystemExit('请使用HTTPS模型服务地址。')
model=input('模型名称：').strip()
key=getpass.getpass('模型 API 密钥（不会回显）：').strip()
if not model or not key:raise SystemExit('模型名称和密钥不能为空。')
def quote(value):return "'"+value.replace("'","\\'")+"'"
values={'LLM_BASE_URL':base,'LLM_API_KEY':key,'LLM_MODEL':model,'LLM_ENABLE_THINKING':'false','STUDY_PBL_RUNNER_TOKEN':secrets.token_urlsafe(48),'PBL_RUNNER_IMAGE':'python:3.12-slim'}
descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(descriptor,'w',encoding='utf-8') as stream:stream.write('\n'.join(name+'='+quote(value) for name,value in values.items())+'\n')
print('私有配置已保存。下一步按 README.md 启动服务。')
