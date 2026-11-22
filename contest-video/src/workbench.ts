import React from 'react';
import {Film,Shot,Caption,SHOTS,CAPTIONS,TOTAL} from './Film';
export const WORKBENCH={name:'知行伴学 · 参赛功能演示',fps:30,width:1920,height:1080,total:TOTAL,background:'#f6f8f4',revision:'20261110-contest-1',
 shots:SHOTS.map(s=>({id:s.id,label:s.title,from:s.from,duration:s.duration,component:Shot as React.FC<Record<string,unknown>>,props:{shotId:s.id,title:s.title,accent:'#225e59'},schema:[{type:'text',key:'title',label:'镜头标题',default:s.title},{type:'color',key:'accent',label:'强调色',default:'#225e59'}]})),
 transitions:[],overlays:[],captions:CAPTIONS.map((c,i)=>({id:'c'+i,label:c.text,from:c.from,duration:c.duration,component:Caption as React.FC<Record<string,unknown>>,props:{text:c.text},schema:[{type:'textarea',key:'text',label:'字幕',default:c.text}]})),
 sfx:[{from:0,duration:TOTAL,src:'audio/narration.wav',volume:.9}],bgm:[],order:['captions','overlays'],original:Film as React.FC<Record<string,unknown>>};
