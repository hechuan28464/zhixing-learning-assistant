"""Private single-host runner. Learner source only executes inside disposable containers."""
import base64,hashlib,hmac,json,os,secrets,threading
from fastapi import FastAPI,Header,HTTPException
from pydantic import BaseModel,ConfigDict,Field
import docker
import requests
from docker.types import LogConfig,Ulimit

app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
admission=threading.BoundedSemaphore(1)
IMAGE=os.getenv('PBL_RUNNER_IMAGE','python:3.12-slim')
OWNER=hashlib.sha256(os.getenv('STUDY_PBL_RUNNER_TOKEN','').encode()).hexdigest()[:16]
HARNESS='''import base64,json,os,types
source=base64.b64decode(os.environ.pop("PBL_SOURCE")).decode("utf-8")
records=json.loads(base64.b64decode(os.environ.pop("PBL_INPUT")))
before=json.dumps(records,ensure_ascii=False,sort_keys=True)
module=types.ModuleType("learner")
exec(compile(source,"src/main.py","exec"),module.__dict__)
fn=module.__dict__.get("summarize")
if not callable(fn):raise ValueError("summarize function is missing")
value=fn(records)
print("PBL_RESULT:"+json.dumps({"value":value,"input_unchanged":before==json.dumps(records,ensure_ascii=False,sort_keys=True)},ensure_ascii=False))
'''

def authorize(token):
    expected=os.getenv('STUDY_PBL_RUNNER_TOKEN','')
    if len(expected)<32 or not token or not hmac.compare_digest(expected,token):raise HTTPException(403,'Runner access denied')

class Job(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source:str=Field(min_length=1,max_length=20000)
    inputs:list[list[dict]]=Field(min_length=1,max_length=4)

@app.on_event('startup')
def cleanup_own_orphans():
    if len(os.getenv('STUDY_PBL_RUNNER_TOKEN',''))<32:return
    try:
        client=docker.from_env(timeout=3)
        for container in client.containers.list(all=True,filters={'label':['zhixing.runner=pbl-v1','zhixing.owner='+OWNER]}):
            container.remove(force=True)
        client.close()
    except Exception:pass

@app.get('/health')
def health(x_runner_token:str|None=Header(default=None)):
    authorize(x_runner_token)
    try:
        client=docker.from_env(timeout=3);client.ping();client.images.get(IMAGE);client.close()
        return {'available':True,'mode':'restricted-local-docker'}
    except Exception:return {'available':False,'reason':'Docker或课程运行镜像尚未准备好。'}

@app.post('/execute')
def execute(body:Job,x_runner_token:str|None=Header(default=None)):
    authorize(x_runner_token)
    if not admission.acquire(blocking=False):raise HTTPException(429,'Runner is busy')
    client=None;results=[]
    try:
        client=docker.from_env(timeout=8);client.images.get(IMAGE)
        for records in body.inputs:
            if len(json.dumps(records).encode())>16000:raise HTTPException(422,'Input too large')
            container=None
            try:
                container=client.containers.run(IMAGE,['python','-I','-c',HARNESS],detach=True,
                    name='zhixing-pbl-'+secrets.token_hex(8),network_disabled=True,read_only=True,
                    user='65534:65534',cap_drop=['ALL'],security_opt=['no-new-privileges:true'],
                    mem_limit='128m',memswap_limit='128m',nano_cpus=500_000_000,pids_limit=32,
                    tmpfs={'/tmp':'rw,noexec,nosuid,size=16m'},init=True,
                    environment={'PBL_SOURCE':base64.b64encode(body.source.encode()).decode(),'PBL_INPUT':base64.b64encode(json.dumps(records,ensure_ascii=False).encode()).decode()},
                    log_config=LogConfig(type='json-file',config={'max-size':'64k','max-file':'1'}),
                    ulimits=[Ulimit(name='nofile',soft=64,hard=64)],labels={'zhixing.runner':'pbl-v1','zhixing.owner':OWNER},use_config_proxy=False,
                    **({'runtime':os.environ['PBL_CONTAINER_RUNTIME']} if os.getenv('PBL_CONTAINER_RUNTIME') else {}))
                status=container.wait(timeout=6)
                logs=container.logs(stdout=True,stderr=False,tail=10)
                if len(logs)>65536:results.append({'status':'failed','reason':'output_limit'});continue
                lines=[line[11:] for line in logs.decode('utf-8',errors='replace').splitlines() if line.startswith('PBL_RESULT:')]
                if status.get('StatusCode')==0 and len(lines)==1:
                    try:results.append({'status':'completed',**json.loads(lines[0])})
                    except ValueError:results.append({'status':'failed','reason':'invalid_output'})
                else:results.append({'status':'failed','reason':'execution'})
            except docker.errors.ImageNotFound:results.append({'status':'infrastructure','reason':'image_missing'})
            except docker.errors.APIError:results.append({'status':'infrastructure','reason':'docker_unavailable'})
            except requests.exceptions.ReadTimeout:
                try:
                    container.reload()
                    results.append({'status':'failed','reason':'timeout'} if container.status=='running' else {'status':'infrastructure','reason':'unknown_outcome'})
                except Exception:results.append({'status':'infrastructure','reason':'unknown_outcome'})
            except Exception:results.append({'status':'infrastructure','reason':'unknown_outcome'})
            finally:
                if container is not None:
                    try:container.remove(force=True)
                    except Exception:pass
        return {'results':results,'mode':'restricted-local-docker'}
    except HTTPException:raise
    except Exception:raise HTTPException(503,'Execution infrastructure unavailable') from None
    finally:
        if client:client.close()
        admission.release()
