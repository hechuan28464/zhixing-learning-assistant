"""Opt-in authenticated live PBL role check, isolated from saved learner records."""
import argparse,getpass,json,os,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from backend.main import app

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
 if not args.execute:parser.error('Live model requests require --execute')
 password=getpass.getpass('Local account password (hidden): ')
 names=['STUDY_DB_PATH','STUDY_AUTH_DB_PATH','STUDY_AUTH_FILE','STUDY_AI_ENABLED','STUDY_REQUIRE_LOGIN'];old={key:os.environ.get(key) for key in names}
 try:
  with tempfile.TemporaryDirectory(prefix='zhixing-pbl-live-') as folder:
   os.environ.update(STUDY_DB_PATH=str(Path(folder)/'records.sqlite3'),STUDY_AUTH_DB_PATH=str(Path(folder)/'auth.sqlite3'),STUDY_AUTH_FILE=str(ROOT/'data/private/auth-users.json'),STUDY_AI_ENABLED='1',STUDY_REQUIRE_LOGIN='1')
   with TestClient(app) as client:
    login=client.post('/api/auth/login',json={'username':'hechuan','password':password});assert login.status_code==200;password=None
    study=client.post('/api/pbl/studies',json={'request_id':'live-pbl-role-check-01'}).json()
    def act(kind,**fields):
     nonlocal study
     response=client.post('/api/pbl/studies/'+study['id']+'/commands',json={'kind':kind,'expected_revision':study['revision'],'request_id':'live-role-action-'+str(study['revision']),**fields})
     response.raise_for_status();study=response.json()
    act('next',text='读取每条记录，按topic累计minutes。')
    act('decision',chosen='使用字典列表',rationale='两个字段分别保存主题和时长。')
    act('next');act('plan',text='逐条读取记录；创建新字典，按主题累计时长；空列表返回空字典；使用公开输入保证，不修改records；检查重复主题、零分钟和空输入。')
    response=client.post('/api/pbl/studies/'+study['id']+'/chat',json={'request_id':'live-role-review-01','message':'请按公开契约审阅当前版本，不增加题面之外的要求。','review_kind':'plan','artifact_sha':study['artifacts']['plan']['sha256']})
    response.raise_for_status();study=response.json();answer=study['messages'][-1]
    assert '林知你好' not in answer['content'] and '你好，林知' not in answer['content']
    data={'ok':study['reviews']['plan'],'model':answer['metadata']['model'],'reply':answer['content'],'usage':answer['metadata']['usage'],'stage':study['stage'],'actual_execution':False,'scope':'isolated temporary database, real model, authored learner'}
    path=ROOT/'test-reports/buddy-live-20261108/pbl-role-recheck.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False))
 finally:
  for key,value in old.items():
   if value is None:os.environ.pop(key,None)
   else:os.environ[key]=value
if __name__=='__main__':main()
