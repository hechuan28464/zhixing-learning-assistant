import {requestId as newRequestId} from './requestId.js'
// One identity for retries of an unchanged write; edited content is a new intent.
export function prepareWrite(previous,payload){
  const signature=JSON.stringify(payload)
  return previous?.signature===signature?previous:{signature,key:newRequestId()}
}
