import hashlib,json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import auth,agent

@pytest.fixture
def client(tmp_path,monkeypatch):
 monkeypatch.setenv('STUDY_DB_PATH',str(tmp_path/'learning.sqlite3'))
 monkeypatch.setenv('STUDY_REQUIRE_LOGIN','1');monkeypatch.setenv('STUDY_AI_ENABLED','0')
 p=tmp_path/'auth-users.json';salt=b'test-fixture-salt'
 p.write_text(json.dumps({'daily_model_limit':2,'users':[{'username':'fixture','salt':salt.hex(),'password_hash':hashlib.pbkdf2_hmac('sha256',b'fixture-pass',salt,260000).hex()}]}))
 with TestClient(app) as c:yield c

def login(c,**extra):return c.post('/api/auth/login',json={'username':'fixture','password':'fixture-pass',**extra})

@pytest.mark.parametrize('path',['/api/sessions/missing/chat','/api/sessions/missing/plan','/api/pbl/studies/missing/chat','/api/pbl/studies/missing/run'])
def test_anonymous_metered_actions_rejected_before_validation_or_model(client,monkeypatch,path):
 def forbidden(*args,**kwargs):raise AssertionError('model must not be called')
 monkeypatch.setattr(agent,'call_model',forbidden)
 r=client.post(path,json={});assert r.status_code==401 and r.json()['code']=='login_required'
 assert client.get('/api/catalog/mathematics').status_code==200

def test_password_cookie_persistence_logout_and_tamper(client):
 assert client.post('/api/auth/login',json={'username':'fixture','password':'wrong'}).status_code==401
 r=login(client,remember=True);assert r.status_code==200
 cookie=r.headers['set-cookie'];assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Max-Age=604800' in cookie
 assert client.get('/api/auth/session').json()['username']=='fixture'
 token=client.cookies.get(auth.COOKIE)
 other=TestClient(app);other.cookies.set(auth.COOKIE,token+'x');assert not other.get('/api/auth/session').json()['authenticated']
 assert client.post('/api/auth/logout').status_code==200
 other.cookies.set(auth.COOKIE,token);assert not other.get('/api/auth/session').json()['authenticated']

def test_logged_in_still_cannot_use_disabled_ai(client,monkeypatch):
 login(client)
 monkeypatch.setattr(agent,'generate_plan',lambda *_:pytest.fail('AI off must be absolute'))
 r=client.post('/api/sessions/missing/plan');assert r.status_code==503 and r.json()['code']=='ai_disabled'

def test_daily_cap_and_restart_stability(client,monkeypatch):
 login(client);monkeypatch.setenv('STUDY_AI_ENABLED','1')
 monkeypatch.setattr(agent,'generate_plan',lambda *_:{'fixture':True})
 assert client.post('/api/sessions/fixture/plan').status_code==200
 assert client.post('/api/sessions/fixture/plan').status_code==200
 assert client.post('/api/sessions/fixture/plan').status_code==429
 with TestClient(app) as c:
  c.cookies.set(auth.COOKIE,client.cookies.get(auth.COOKIE))
  assert c.get('/api/auth/session').json()['authenticated']
  assert c.post('/api/sessions/fixture/plan').status_code==429

def test_login_throttling_and_cross_origin(client):
 for _ in range(5):assert client.post('/api/auth/login',json={'username':'fixture','password':'wrong'}).status_code==401
 assert login(client).status_code==429
 assert client.post('/api/auth/login',json={'username':'fixture','password':'fixture-pass'},headers={'Origin':'https://other.invalid'}).status_code==403

def test_changed_password_revokes_existing_session(client,tmp_path):
 login(client);p=tmp_path/'auth-users.json';v=json.loads(p.read_text());v['users'][0]['password_hash']='0'*64;p.write_text(json.dumps(v))
 assert not client.get('/api/auth/session').json()['authenticated']
