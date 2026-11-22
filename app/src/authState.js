import {reactive} from 'vue'
export const authSession=reactive({authenticated:false,username:null,login_required:true,ai_enabled:false,open:false,busy:false,error:''})
let pending=null
export async function refreshAuthentication(){
 try{const r=await fetch('/api/auth/session',{cache:'no-store'});if(r.ok)Object.assign(authSession,await r.json())}catch{}
}
export function showLogin(){authSession.error='';authSession.open=true}
export function requestLogin(){
 showLogin()
 if(!pending){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});pending={promise,resolve,reject}}
 return pending.promise
}
export function cancelLogin(){
 if(authSession.busy)return
 authSession.open=false;authSession.error=''
 const prior=pending;pending=null;prior?.reject(new Error('已取消登录，刚才输入的内容已保留。'))
}
export async function signIn(username,password,remember){
 if(authSession.busy)return
 authSession.busy=true;authSession.error=''
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000)
 try{
  const r=await fetch('/api/auth/login',{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password,remember})})
  const data=await r.json();if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:'请核对账号与密码。')
  Object.assign(authSession,data,{open:false});const prior=pending;pending=null;prior?.resolve()
 }catch(e){authSession.error=e.name==='AbortError'?'登录等待时间较长，请重试。':e instanceof TypeError||e instanceof SyntaxError?'暂时无法连接登录服务，请稍后重试。':e.message}
 finally{clearTimeout(timeout);authSession.busy=false}
}
export async function signOut(){
 const r=await fetch('/api/auth/logout',{method:'POST'});if(r.ok)Object.assign(authSession,await r.json())
}
