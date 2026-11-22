// Older saved generations may contain only a handful of headings. Expand only
// from their saved, cited chapter text; never invent missing lesson facts.
export function studyOutline(outline,sections=[]){
 if(!outline)return null
 const depth=node=>1+Math.max(0,...(node.children||[]).map(depth))
 if(depth(outline)>=3||!sections.length)return outline
 return {...outline,derived:'saved_sections',children:sections.map(section=>{
  const sentences=section.body.split(/(?<=[。！？])\s*|\n+/).map(s=>s.trim()).filter(Boolean)
  return {label:section.title,detail:section.body,segment_ids:section.segment_ids||[],children:sentences.slice(0,4).map(sentence=>({label:sentence.length>26?sentence.slice(0,25)+'…':sentence,detail:sentence,segment_ids:section.segment_ids||[],children:[]}))}
 })}
}
