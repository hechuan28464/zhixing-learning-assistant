// Keep stable machine locators in receipts and show readable locations in the UI.
export function displayLocator(source={}) {
  const paragraph=Number(source.paragraph)||Number(String(source.locator||'').match(/#p(\d+)$/)?.[1])
  if(Number.isInteger(paragraph)&&paragraph>0)return `第${paragraph}段`
  const raw=String(source.locator||'')
  if(/^(material|note|record|conversation):/.test(raw))return '来源原文'
  return raw||'来源原文'
}
