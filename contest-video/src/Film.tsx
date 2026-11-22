import React from 'react';
import {AbsoluteFill,Audio,Easing,Img,Sequence,interpolate,staticFile,useCurrentFrame,getInputProps} from 'remotion';
import timeline from './timeline.json';
import media from './media.json';
import {PageCam,CamKey} from './lib/PageCam';

export const SHOTS=timeline.shots, TOTAL=timeline.total,CAPTIONS=timeline.captions;
const ease=Easing.bezier(.33,0,.15,1);
const clamp={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
const B={ink:'#174d4d',teal:'#225e59',paper:'#f6f8f4',line:'#d7e5dc',muted:'#657e76',apricot:'#e7b77f'};
const headings:Record<string,string>={home:'从当前目标\n继续',courses:'课程有目录\n任务有目标',diagnostic:'先找出这一次\n的混淆',remedy:'补救衔接\n换题复核',evidence:'四维依据\n各有出处',agent:'林知先读记录\n再给行动',knowledge:'带着原文\n与林知讨论',memory:'学习记忆\n由你确认',video:'把视频原句\n变成学习材料',pbl:'从理解走到\n可检查的实践',graph:'知识结构\n来自实际记录'};
// Cursor geometry and leading-hand camera timing adapted from CursorFlyover.tsx.
const info:Record<string,string[]>={
 home:['继续已有目标','看见推荐依据','与林知讨论'],courses:['Python / 统计 / 阅读','对齐公开课程目录','自编讲义与任务'],
 diagnostic:['50 增加 20%','候选解释：把新量当基准','进入对应补救'],remedy:['200 → 220，再下降 10%','每次变化重新找基准','换题检查理解'],
 evidence:['独立表现 · 帮助程度','目标覆盖 · 保持','每项依据都可回看'],agent:['读取学习记录','读取真实下一步','打开对应课程任务'],
 knowledge:['搜索学习材料与记录','原文、段落与来源','引用随问题保留'],memory:['建议保留原话来源','确认后使用','支持撤回'],
 video:['Harvard CS50 · Functions','122 条官方字幕','每页 10 条 · 时间点引用'],pbl:['七个连续学习阶段','计划与代码分别保存','版本绑定真实检查回执'],
 graph:['实际保存的节点','课程结构与路线关系','学习证据可核查']
};
const poseNames:Record<string,string[]>={remedy:['补救：重新找基准','复核：换题检查'],evidence:['四维学习依据','实际作答记录'],agent:['保存的问题与回复','展开本次工具回执','跳转到对应任务'],knowledge:['知识空间检索','围绕来源讨论'],video:['官方原始字幕','搜索 input','第 13 页 · 最后两条'],pbl:['项目学习七阶段','已保存的计划审阅','历史 Linux 真实回执']};
const seqIndex=(s:typeof SHOTS[number],f:number)=>{
 if(s.id==='agent'){const a=s.audio;return f<(a[1].from-s.from)?0:f<(a[3].from-s.from)?1:2;}
 if(s.id==='pbl'||s.id==='video'){const a=s.audio;return f<(a[1].from-s.from)?0:f<(a[2].from-s.from)?1:2;}
 if(s.id==='evidence')return f<s.audio[2].from-s.from?0:1;
 if(s.images.length>1)return f<(s.audio[Math.min(1,s.audio.length-1)].from-s.from)?0:1;
 return 0;
};
export const Caption:React.FC<{text?:string}>=({text=''})=><div style={{position:'absolute',left:80,right:80,bottom:20,height:160,display:'flex',justifyContent:'center',alignItems:'center',fontSize:56,lineHeight:1.2,fontWeight:500,color:'#fff',padding:'12px 25px',textAlign:'center',background:'#173e39f5',borderRadius:14,fontFamily:'Microsoft YaHei',boxSizing:'border-box'}}>{text}</div>;

// Adapted from the exact brand-ink-open demo: glyph delays 10+i*3,
// 12-frame press, 6px→0 blur, full-brand 33f hold, seven-frame exit.
const Brand:React.FC=()=>{const f=useCurrentFrame();const t=Math.min(f,96);const out=interpolate(f,[97,104],[0,1],clamp);return <AbsoluteFill style={{background:B.paper,justifyContent:'center',alignItems:'center'}}>
 <Img src={staticFile('hero.png')} style={{position:'absolute',width:2100,height:700,objectFit:'cover',right:-250,bottom:-120,opacity:.48}}/>
 <div style={{textAlign:'center',opacity:1-out,transform:`translateY(${-40*out}px) scale(${1-.12*out})`}}>
 <Img src={staticFile('logo.png')} style={{width:130,height:130,objectFit:'contain',marginBottom:30}}/>
 <div style={{display:'flex',justifyContent:'center',fontFamily:'SimSun',fontWeight:700,fontSize:130,color:B.ink}}>{'知行伴学'.split('').map((c,i)=>{const p=interpolate(t,[10+i*3,22+i*3],[0,1],{...clamp,easing:Easing.bezier(.2,.7,.25,1)});return <span key={i} style={{opacity:p,transform:`scale(${1.6-.6*p})`,filter:`blur(${(1-p)*6}px)`,transformOrigin:'center bottom'}}>{c}</span>})}</div>
 <div style={{fontFamily:'Microsoft YaHei',fontSize:40,color:B.muted,marginTop:30,letterSpacing:5}}>{'跨学科个性化学习 Agent'.slice(0,Math.max(0,Math.floor((f-28)/.7)))}</div>
 </div>
 </AbsoluteFill>};
export const Shot:React.FC<{shotId?:string;title?:string;accent?:string}>=({shotId='home',title,accent=B.teal})=>{
 const s=SHOTS.find(x=>x.id===shotId)!;const f=useCurrentFrame();const titleText=title&&title!==s.title?title:headings[s.id]||s.title;const enter=interpolate(f,[0,42],[0,1],{...clamp,easing:ease});
 const mode='mode' in s?s.mode:undefined;
 const accessProps=getInputProps();
 const access={url:String(accessProps.reviewerUrl||'http://127.0.0.1:5173/'),username:String(accessProps.reviewerUsername||'请配置评审账号'),password:String(accessProps.reviewerPassword||'请配置评审密码')};
 if(s.id==='intro')return <AbsoluteFill style={{background:B.paper}}>{f<104?<Brand/>:<><Img src={staticFile('hero.png')} style={{width:1920,height:1080,objectFit:'cover'}}/><div style={{position:'absolute',left:110,top:190,color:B.ink,fontFamily:'SimSun',fontSize:94,lineHeight:1.5,fontWeight:700}}>围绕一个目标，<br/>把学习过程连起来。</div></>}</AbsoluteFill>;
 if(mode==='outro')return <AbsoluteFill style={{background:B.paper,color:B.ink,fontFamily:'Microsoft YaHei',padding:'160px 180px',boxSizing:'border-box'}}>
 <Img src={staticFile('hero.png')} style={{position:'absolute',right:-500,bottom:-150,width:1800,height:800,objectFit:'cover',opacity:.35}}/>
 <div style={{zIndex:1,opacity:enter,transform:`translateY(${(1-enter)*24}px)`}}><div style={{display:'flex',alignItems:'center',gap:28}}><Img src={staticFile('logo.png')} style={{width:125,height:125,objectFit:'contain'}}/><div style={{fontFamily:'SimSun',fontSize:108,fontWeight:700}}>知行伴学</div></div>
 <div style={{fontSize:36,color:B.muted,margin:'35px 0 42px'}}>让好奇，慢慢成为能力。</div><div style={{fontSize:32,letterSpacing:4,color:B.muted,marginBottom:24}}>智能体体验入口</div><div style={{fontSize:64,fontWeight:650}}>{access.url}</div><div style={{fontSize:56,lineHeight:1.65,marginTop:28}}>评审账号：{access.username}<br/>登录密码：{access.password}</div></div>
 </AbsoluteFill>;
 if(mode==='application')return <AbsoluteFill style={{background:B.paper,padding:100,boxSizing:'border-box',fontFamily:'Microsoft YaHei',color:B.ink}}><div style={{fontSize:26,letterSpacing:4,color:B.muted}}>应用与扩展</div><h1 style={{fontFamily:'SimSun',fontSize:82,margin:'40px 0 75px'}}>从一个课程组开始</h1><div style={{display:'flex',gap:28}}>{[['课程组试点','任务完成 · 来源追溯','教师复核 · 单次成本'],['服务形态','自主学习 · 实训教学','班级席位 · 课程内容包'],['扩展边界','教学与资料检索','视频处理 · 隔离代码检查']].map((a,i)=><div key={a[0]} style={{flex:1,padding:40,borderRadius:22,background:i===1?B.teal:'#e9f1eb',color:i===1?'#fff':B.ink,opacity:interpolate(f,[i*16,42+i*16],[0,1],clamp),transform:`translateY(${(1-interpolate(f,[i*16,42+i*16],[0,1],{...clamp,easing:ease}))*35}px)`}}><div style={{fontSize:22,opacity:.55,marginBottom:48}}>0{i+1}</div><div style={{fontSize:44,fontWeight:600,marginBottom:35}}>{a[0]}</div><div style={{fontSize:29,lineHeight:1.9}}>{a[1]}<br/>{a[2]}</div></div>)}</div><div style={{marginTop:50,fontSize:24,color:B.muted}}>拟议应用路径，以实际试点持续验证</div></AbsoluteFill>;
 const idx=Math.min(seqIndex(s,f),s.images.length-1),image=s.id==='graph'?'graph-full.png':s.images[idx];const m=media[image as keyof typeof media];
 const pageH=m?.pageH||1080;const fit=Math.min(1,850/pageH);const initial=fit*.96;const centerY=pageH/2;
 const start=(s.audio[Math.min(idx,s.audio.length-1)]?.from||s.from)-s.from;
 const local=Math.max(0,f-start);let keys:CamKey[]=[{frame:0,cx:960,cy:centerY,zoom:initial},{frame:54,cx:960,cy:centerY,zoom:fit},{frame:Math.max(55,s.duration),cx:960,cy:centerY,zoom:fit}];
 if(s.id==='home')keys=[{frame:0,cx:960,cy:540,zoom:.9},{frame:72,cx:960,cy:650,zoom:1.2},{frame:172,cx:960,cy:650,zoom:1.2},{frame:212,cx:1340,cy:730,zoom:1.7},{frame:312,cx:1340,cy:730,zoom:1.7},{frame:352,cx:1340,cy:400,zoom:1.7},{frame:s.duration,cx:1340,cy:400,zoom:1.7}];
 if(s.id==='graph')keys=[{frame:0,cx:960,cy:600,zoom:.86},{frame:90,cx:960,cy:600,zoom:.86},{frame:s.duration-90,cx:960,cy:Math.max(600,pageH-600),zoom:.86},{frame:s.duration,cx:960,cy:Math.max(600,pageH-600),zoom:.86}];
 const notes=info[s.id]||[];const historical=s.id==='pbl'&&idx>0||s.id==='memory';
 return <AbsoluteFill style={{background:B.paper,fontFamily:'Microsoft YaHei',color:B.ink}}>
 <div style={{position:'absolute',inset:0,background:'radial-gradient(ellipse at 92% 10%,#dbece44d,transparent 65%)'}}/>
 <div style={{position:'absolute',left:65,top:40,display:'flex',alignItems:'center',gap:14}}><Img src={staticFile('logo.png')} style={{width:48,height:48,objectFit:'contain'}}/><span style={{fontSize:27,fontWeight:600}}>知行伴学</span></div>
 <div style={{position:'absolute',right:70,top:47,fontSize:32,color:B.muted}}>{s.eyebrow}</div>
 <div style={{position:'absolute',left:70,top:185,width:365,opacity:enter,transform:`translateY(${(1-enter)*22}px)`}}><div style={{width:42,height:4,background:B.apricot,marginBottom:30}}/><div style={{fontFamily:'SimSun',fontSize:56,lineHeight:1.5,fontWeight:700,whiteSpace:'pre-line'}}>{titleText}</div><div style={{marginTop:45,display:'grid',gap:18}}>{notes.map((text,i)=><div key={text} style={{fontSize:32,lineHeight:1.5,display:'flex',gap:12,color:i===1?B.ink:B.muted}}><span style={{fontSize:32,color:accent}}>0{i+1}</span><span>{text}</span></div>)}</div></div>
 <div style={{position:'absolute',left:490,top:145,width:1360,height:690,borderRadius:18,overflow:'hidden',border:'1px solid #d7e5dc',background:'#fff',boxShadow:'0 18px 65px #174d4d0d'}}>
 <div style={{height:56,background:'#edf4ef',display:'flex',alignItems:'center',padding:'0 24px',gap:8,color:B.muted,fontSize:32}}>{[0,1,2].map(x=><i key={x} style={{width:7,height:7,borderRadius:9,background:'#a2b9ae'}}/>)}<span style={{marginLeft:17}}>{poseNames[s.id]?.[idx]||'真实网页界面'}</span><span style={{marginLeft:'auto',fontSize:28}}>{historical?'历史验收画面':s.id==='agent'?'已保存回复':'实际功能演示'}</span></div>
 <div style={{position:'absolute',top:56,left:0,width:1360,height:634,overflow:'hidden'}}><div style={{width:1920,height:1080,transform:'scale(0.7083333333)',transformOrigin:'0 0',position:'absolute',top:-66}}><PageCam key={image} src={'textures/focus/'+image} pageH={pageH} keys={keys} frame={local} /></div></div>
 </div>
 <div style={{position:'absolute',left:70,bottom:225,display:'flex',gap:7}}>{SHOTS.filter(x=>!['intro','outro'].includes(x.id)).map(x=><span key={x.id} style={{width:x.id===s.id?31:7,height:7,borderRadius:7,background:x.id===s.id?accent:'#c8d9ce'}}/>)}</div>
 </AbsoluteFill>;
};
export const Film:React.FC=()=> <AbsoluteFill style={{background:B.paper}}>
 {SHOTS.map(s=><Sequence key={s.id} from={s.from} durationInFrames={s.duration}><Shot shotId={s.id}/></Sequence>)}
 {CAPTIONS.map((c,i)=><Sequence key={'c'+i} from={c.from} durationInFrames={c.duration}><Caption text={c.text}/></Sequence>)}
 <Audio src={staticFile('audio/narration.wav')} volume={.9}/>
 </AbsoluteFill>;
