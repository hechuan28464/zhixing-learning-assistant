"""Private runner client. The host never runs learner code as a subprocess."""
import json,os,urllib.request,urllib.error
def status():
    url=os.getenv('STUDY_PBL_RUNNER_URL','').rstrip('/')
    token=os.getenv('STUDY_PBL_RUNNER_TOKEN','')
    if not url or not token:return {'available':False,'label':'执行环境尚未连接','mode':'local-docker','reason':'可先保存计划和代码，部署Linux执行服务后再运行测试。'}
    try:
        request=urllib.request.Request(url+'/health',headers={'X-Runner-Token':token})
        with urllib.request.urlopen(request,timeout=3) as response:data=json.load(response)
        return {'available':data.get('available') is True,'label':'本机隔离执行已连接' if data.get('available') else '执行服务暂时不可用','mode':'local-docker','reason':data.get('reason','')}
    except Exception:return {'available':False,'label':'执行服务暂时不可用','mode':'local-docker','reason':'请检查服务器上的执行服务，学习草稿仍会保留。'}

def execute(source,inputs):
    url=os.getenv('STUDY_PBL_RUNNER_URL','').rstrip('/')
    token=os.getenv('STUDY_PBL_RUNNER_TOKEN','')
    if not url or not token:raise RuntimeError('执行环境尚未连接，未执行代码。')
    payload=json.dumps({'source':source,'inputs':inputs},ensure_ascii=False).encode()
    request=urllib.request.Request(url+'/execute',data=payload,headers={'Content-Type':'application/json','X-Runner-Token':token})
    try:
        with urllib.request.urlopen(request,timeout=35) as response:return json.load(response)
    except Exception:raise RuntimeError('执行服务没有返回完整结果，未记录为测试失败。') from None
