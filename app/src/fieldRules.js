export function requiredText(label,limit){return value=>{
 const text=String(value??'')
 if(!text.trim())return `请填写${label}，不能只输入空白。`
 if(text.length>limit)return `${label}最多 ${limit} 个字符。`
 return true
}}
