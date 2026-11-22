"""Opt-in one-conversation provider test, isolated from the user's database."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

from fastapi.testclient import TestClient
from backend.main import app

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='zhixing-model-check-') as directory:
    os.environ['STUDY_DB_PATH']=str(Path(directory)/'learning.sqlite3')
    with TestClient(app) as client:
        space=client.post('/api/sessions',json={'course_id':'mathematics'}).json()
        response=client.post(f"/api/sessions/{space['id']}/chat",json={
            'message':'请使用工具读取当前讲义，用两句话解释为什么百分比需要先确认基准量。不要给练习答案。',
            'request_id':'live_model_check_20261102'})
        data=response.json()
        report={'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'isolated synthetic developer test; no real learner data',
                'http_status':response.status_code,'ok':response.status_code==200 and bool(data.get('content')),
                'model':data.get('model'),'tools':data.get('tools',[]),'sources':data.get('sources',[]),
                'reply':data.get('content',data.get('detail')),'seconds':data.get('seconds')}
        target=root/'test-reports'
        target.mkdir(exist_ok=True)
        (target/'live-model-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=True,indent=2))
        if not report['ok']:raise SystemExit(1)
