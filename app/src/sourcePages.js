// Preserve original paragraph numbers when a long paragraph spans pages.
export function sourcePages(text,{maxChars=600,maxParagraphs=4}={}){
 const paragraphs=String(text||'').split(/\n\s*\n/).map(s=>s.trim()).filter(Boolean)
 const pages=[];let page=[],size=0
 const budget=Math.max(120,maxChars)
 paragraphs.forEach((text,index)=>{
  const chars=Array.from(text),parts=Math.ceil(chars.length/budget)
  for(let part=0;part<parts;part++){
   const value=chars.slice(part*budget,(part+1)*budget).join('')
   if(page.length&&(size+value.length>budget||page.length>=maxParagraphs)){pages.push(page);page=[];size=0}
   page.push({text:value,number:index+1,part:part+1,parts});size+=value.length
  }
 })
 if(page.length)pages.push(page)
 return pages.length?pages:[[]]
}
export function sourcePageForParagraph(pages,number){return Math.max(0,pages.findIndex(rows=>rows.some(row=>row.number===number)))+1}
