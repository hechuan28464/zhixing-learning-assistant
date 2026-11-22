// Real learner records determine the layout. Catalog entries never pad this section.
export function buildHomeCards(sessions = [], query = '') {
  const term = query.trim().toLowerCase()
  const matches = item => [item.title, item.goal, item.domain, item.tag, item.subtitle]
    .filter(Boolean).join(' ').toLowerCase().includes(term)
  return sessions.filter(matches).slice(0, 3).map(item => ({ ...item, cardType: 'space' }))
}

export function buildNextActions(sessions = [], materials = [], currentId = null) {
  const current = sessions.find(item => item.id === currentId) || sessions[0]
  if (!current) return [{ id:'create',kind:'create',title:'从一个想解决的问题开始',detail:'写下目标，再一起决定怎么学。',icon:'plus',label:'第一步',reason:'先知道你希望做到什么，才能给出适合你的建议。' }]
  const base={id:'next-step',sessionId:current.id,target:current.title,domain:current.domain,label:'建议下一步'}
  if(current.next?.task_id)return [{...base,kind:current.next.kind,taskId:current.next.task_id,lessonId:current.next.lesson_id,icon:'book-open',title:current.next.title,detail:current.next.purpose==='diagnostic'?'先做一道诊断':'从当前任务继续',reason:current.next.reason}]
  if (!current.course_id) {
    const draft=current.plan?.draft, active=current.plan?.active
    return [{...base,kind:'route',icon:'network',title:draft?'检查并确认路线草案':active?'回到已确认的学习路线':'把目标拆成几个小步骤',
      detail:draft?'先看看这些步骤是否符合你的目标。':active?'选择一个适合现在开始的步骤。':'按已有基础和可用时间组织路线。',
      reason:draft?'当前有一份尚未确认的草案，你可以检查、调整后再使用。':active?'你的路线已经保留，不需要重新从头规划。':'当前目标还没有路线，先把“想学会”变成一个能开始的小步骤。'}]
  }
  const observed=current.states?.[current.current_lesson]
  if (observed?.status==='assisted') return [{...base,kind:'review',icon:'circle',title:'换一道新题，核对理解',detail:'不重复刚刚得到帮助的原题。',reason:'最近的完成包含帮助，换一道新题能更清楚地观察当前理解。'}]
  if (observed?.status==='pending_review') return [{...base,kind:'space',icon:'file-text',title:'回看作答标准与自己的依据',detail:'开放作答已保存，可以逐项对照。',reason:'当前作答仍待复核，不把提交本身当作已经掌握。'}]
  if (observed?.status==='independent') return [{...base,kind:'space',icon:'book-open',title:'选择下一步，继续探索',detail:'回到课程，查看其他单元或已有记录。',reason:'当前单元已有独立新题表现，后续学习仍由你选择。'}]
  return [{...base,kind:'space',icon:'book-open',title:observed?.attempts?'从反馈中找到下一小步':'用一道练习，看看哪里已经懂了',
    detail:observed?.attempts?'核对上次作答，再决定是否需要帮助。':'先观察具体表现，不急着给自己打分。',
    reason:observed?.attempts?'已经有真实作答记录，建议从具体反馈继续，而不是重复整段讲解。':'当前单元还缺少作答证据，一次小练习比猜测掌握程度更有帮助。'}]
}
