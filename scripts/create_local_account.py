"""Create an assigned local account without committing or printing passwords."""
import argparse,getpass,hashlib,json,os,secrets,tempfile
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',required=True)
    parser.add_argument('--config',type=Path,default=Path(__file__).resolve().parents[1]/'app/data/private/auth-users.json')
    args=parser.parse_args();username=args.username.strip()
    if not 1<=len(username)<=80:parser.error('Username must contain 1–80 characters.')
    path=args.config.resolve();data=json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {'users':[],'daily_model_limit':20}
    if any(u.get('username')==username for u in data.get('users',[])):parser.error('Account already exists; existing credentials were preserved.')
    password=getpass.getpass('Password (hidden): ')
    if len(password)<8:parser.error('Use a password with at least 8 characters.')
    if password!=getpass.getpass('Repeat password (hidden): '):parser.error('Passwords do not match.')
    salt=secrets.token_bytes(16)
    data.setdefault('users',[]).append({'username':username,'salt':salt.hex(),'password_hash':hashlib.pbkdf2_hmac('sha256',password.encode(),salt,260000).hex(),'disabled':False})
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.account-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf8') as stream:json.dump(data,stream,ensure_ascii=False,indent=2)
        os.chmod(temp,0o600);os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    print('Assigned account created. Password and hashes were not printed.')

if __name__=='__main__':main()
