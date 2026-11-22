"""Preassigned access to metered AI operations; no public registration."""
import hashlib,hmac,json,os,re,secrets,sqlite3,time
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from pathlib import Path
from fastapi import APIRouter,Request,Response,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from .store import database_path
from contextvars import ContextVar
REQUEST_USER=ContextVar('request_user',default=None)

router=APIRouter(prefix='/api/auth')
COOKIE=os.getenv('STUDY_AUTH_COOKIE','zhixing_session')
PAID=re.compile(r'^/api/(?:sessions/[^/]+/(?:chat|plan)|pbl/studies/[^/]+/chat|videos/[^/]+/generate)$')
EXECUTION=re.compile(r'^/api/pbl/studies/[^/]+/(?:run|evaluate)$')

def required():return os.getenv('STUDY_REQUIRE_LOGIN','1')!='0'
def ai_enabled():return os.getenv('STUDY_AI_ENABLED','0')=='1'
def config():
 path=Path(os.getenv('STUDY_AUTH_FILE',str(database_path().parent/'auth-users.json')))
 try:return json.loads(path.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {'users':[]}

@contextmanager
def db():
 path=Path(os.getenv('STUDY_AUTH_DB_PATH',str(database_path().parent/'auth.sqlite3')))
 path.parent.mkdir(parents=True,exist_ok=True)
 c=sqlite3.connect(path,timeout=5);c.row_factory=sqlite3.Row
 c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA busy_timeout=5000')
 c.executescript('''CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,username TEXT NOT NULL,expires REAL NOT NULL,credential_version TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS failures(bucket TEXT PRIMARY KEY,started REAL NOT NULL,count INTEGER NOT NULL);
 CREATE TABLE IF NOT EXISTS usage(username TEXT NOT NULL,day TEXT NOT NULL,count INTEGER NOT NULL,PRIMARY KEY(username,day));''')
 try:yield c;c.commit()
 except Exception:c.rollback();raise
 finally:c.close()

def account(username):return next((u for u in config().get('users',[]) if u.get('username')==username and not u.get('disabled')),None)
def version(user):return hashlib.sha256((user.get('salt','')+user.get('password_hash','')).encode()).hexdigest()
def current_user(request):
 token=request.cookies.get(COOKIE,'')
 if not token or len(token)>256:return None
 with db() as c:r=c.execute('SELECT * FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
 if not r or r['expires']<=time.time():return None
 user=account(r['username'])
 return user['username'] if user and hmac.compare_digest(r['credential_version'],version(user)) else None

def protected(path):return bool(PAID.fullmatch(path) or EXECUTION.fullmatch(path) or re.fullmatch(r'/api/sessions/[^/]+/chat/cancel',path) or path.startswith('/api/videos'))
def check_operation(request):
 if not required():return None
 username=current_user(request)
 if not username:return {'status':401,'body':{'code':'login_required','detail':'登录后即可使用这项功能。'}}
 if PAID.fullmatch(request.url.path):
  if not ai_enabled():return {'status':503,'body':{'code':'ai_disabled','detail':'AI 服务暂未开启，可以继续浏览课程、阅读资料和练习。'}}
  limit=int(config().get('daily_model_limit',20));day=datetime.now(timezone(timedelta(hours=8))).date().isoformat()
  with db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT count FROM usage WHERE username=? AND day=?',(username,day)).fetchone()
   if row and row['count']>=limit:return {'status':429,'body':{'code':'ai_daily_limit','detail':'今天的 AI 使用次数已达上限，可以继续阅读和练习。'}}
   c.execute('INSERT INTO usage VALUES(?,?,1) ON CONFLICT(username,day) DO UPDATE SET count=count+1',(username,day))
 return None

class Login(BaseModel):
 model_config=ConfigDict(extra='forbid')
 username:str=Field(min_length=1,max_length=80)
 password:str=Field(min_length=1,max_length=200)
 remember:bool=False

@router.get('/session')
def status(request:Request):
 user=current_user(request) if required() else None
 return {'login_required':required(),'authenticated':bool(user),'username':user,'ai_enabled':ai_enabled()}

@router.post('/login')
def login(body:Login,request:Request,response:Response):
 username=body.username.strip();ip=request.client.host if request.client else 'unknown'
 bucket=hashlib.sha256((ip+'|'+username).encode()).hexdigest();stamp=time.time()
 with db() as c:
  c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM failures WHERE bucket=?',(bucket,)).fetchone()
  if r and stamp-r['started']<300 and r['count']>=5:raise HTTPException(429,'尝试次数较多，请五分钟后再试。')
  c.execute('INSERT INTO failures VALUES(?,?,1) ON CONFLICT(bucket) DO UPDATE SET started=CASE WHEN ?-started>=300 THEN ? ELSE started END,count=CASE WHEN ?-started>=300 THEN 1 ELSE count+1 END',(bucket,stamp,stamp,stamp,stamp))
 user=account(username)
 salt=bytes.fromhex(user['salt']) if user else b'zhixing-dummy-salt'
 calculated=hashlib.pbkdf2_hmac('sha256',body.password.encode(),salt,260000).hex()
 if not user or not hmac.compare_digest(calculated,user['password_hash']):raise HTTPException(401,'账号或密码不正确，请重新填写。')
 token=secrets.token_urlsafe(48);ttl=7*86400 if body.remember else 12*3600
 with db() as c:
  c.execute('DELETE FROM failures WHERE bucket=?',(bucket,));c.execute('DELETE FROM failures WHERE started<?',(stamp-600,));c.execute('DELETE FROM sessions WHERE expires<?',(stamp,))
  c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),username,stamp+ttl,version(user)))
 response.set_cookie(COOKIE,token,httponly=True,secure=request.url.scheme=='https',samesite='strict',max_age=ttl if body.remember else None,path='/')
 response.headers['Cache-Control']='no-store'
 return {'authenticated':True,'username':username,'login_required':required(),'ai_enabled':ai_enabled()}

@router.post('/logout')
def logout(request:Request,response:Response):
 token=request.cookies.get(COOKIE,'')
 with db() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
 response.delete_cookie(COOKIE,path='/');response.headers['Cache-Control']='no-store'
 return {'authenticated':False,'username':None,'login_required':required(),'ai_enabled':ai_enabled()}
