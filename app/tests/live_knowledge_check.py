"""Opt-in: one actual provider call, isolated learner database, no credentials in output."""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from backend.main import app
from backend import knowledge


def main():
    with tempfile.TemporaryDirectory(prefix='zhixing-knowledge-') as folder:
        os.environ['STUDY_DB_PATH']=str(Path(folder)/'isolated.sqlite3')
        with TestClient(app) as client:
            sid=client.post('/api/sessions',json={'title':'引用讨论联调','goal':'检查事实、观点与证据的连接'}).json()['id']
            mid=client.post('/api/materials',json={'title':'引用联调材料','text':'社区阅读室本月新增了20个座位。这是可通过记录核查的事实。“它是全市最好的阅读室”需要说明评价标准。','source':'自编联调文本','session_id':sid}).json()['id']
            response=client.post('/api/sessions/'+sid+'/chat',json={'message':'我希望先看一个具体例子。请结合引用说明事实和观点的区别。','request_id':'live-knowledge-reference-001','reference_ids':['material:'+mid]})
            if response.status_code!=200:raise RuntimeError('Live discussion failed with status '+str(response.status_code))
            reply=response.json()
            memories=client.get('/api/knowledge',params={'kind':'memory'}).json()
            report={'ok':bool(reply.get('content')) and bool(reply.get('sources')) and memories['total']>=1,'actual_provider_call':True,'database':'temporary isolated database; formal learner data untouched','model':reply.get('model'),'seconds':reply.get('seconds'),'reply_characters':len(reply.get('content','')),'source_citation_present':any(s['title']=='引用联调材料' for s in reply.get('sources',[])),'memory_candidates':memories['total'],'pending_not_in_confirmed_context':not knowledge.confirmed_memories(sid)}
            target=ROOT/'test-reports/live-knowledge-check.json';target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=True))
            if not report['ok']:raise RuntimeError('Live validation failed')


if __name__=='__main__':main()
