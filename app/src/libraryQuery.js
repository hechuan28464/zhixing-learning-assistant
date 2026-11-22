// Read metadata in bounded server windows; the UI renders ten records at a time.
export async function readLibraryMetadata(api,params={}){
 const items=[];let offset=0,total=0
 do{
  const page=await api('/knowledge?'+new URLSearchParams({...params,limit:'100',offset:String(offset)}))
  items.push(...page.items);total=page.total;offset+=page.items.length
  if(!page.items.length)break
 }while(offset<total)
 return {items:[...new Map(items.map(item=>[item.key,item])).values()],total}
}
