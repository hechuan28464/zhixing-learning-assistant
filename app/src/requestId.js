// Request deduplication IDs also work on an HTTP IP origin (randomUUID requires HTTPS).
export function requestId(){
 if(globalThis.crypto?.randomUUID)return globalThis.crypto.randomUUID()
 const bytes=new Uint8Array(16)
 if(globalThis.crypto?.getRandomValues)globalThis.crypto.getRandomValues(bytes)
 else for(let i=0;i<bytes.length;i++)bytes[i]=Math.floor(Math.random()*256)
 bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128
 const value=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')
 return `${value.slice(0,8)}-${value.slice(8,12)}-${value.slice(12,16)}-${value.slice(16,20)}-${value.slice(20)}`
}
