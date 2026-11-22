"""Subject-specific adaptation of OpenMAIC's goal/evidence/pacing principles."""
PROFILES={
 'mathematics':('数学思维','先明确量、关系与条件，围绕当前单元给一个具体例子；检查推理过程和基准量。运算由可核对步骤支撑，不从一次答案推断长期掌握。'),
 'reading':('阅读与思考','先定位当前原文，再区分事实、判断与推断。围绕主张、证据和限制给反馈；保留引用来源。开放论证按公开标准讨论，不把模型意见当作客观能力认证。'),
 'programming':('编程与智能','按当前教材章节讨论输入输出、类型、控制、函数、文件、对象、数据处理与验证。普通单元检查代码阅读与结果预测；项目学习另按保存阶段与实际执行记录说明。Tkinter与Pygame需要桌面环境，NumPy/Pandas/sklearn需要相应依赖，不能声称网页执行器已运行未配置的库。不把读懂示例或生成代码等同于独立掌握。')}
def instruction(course_id):
 label,text=PROFILES.get(course_id,('跨学科探索','先回应具体问题，明确所需资料和可观察的产物，再建议一个可检查的小步骤。'))
 return '当前学科教学策略：'+label+'。'+text+' 教学节奏采用目标→解释→学习者回应→下一步；已经清楚回答的内容予以认可，求助时先解释，不重复盘问。'
