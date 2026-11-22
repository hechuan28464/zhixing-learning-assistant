import React from 'react';
import {Composition} from 'remotion';
import {Film,Shot,SHOTS,TOTAL} from './Film';
export const Root:React.FC=()=> <>
 <Composition id="ZhixingContest" component={Film} durationInFrames={TOTAL} fps={30} width={1920} height={1080}/>
 {SHOTS.map(s=><Composition key={s.id} id={'Shot-'+s.id} component={Shot} defaultProps={{shotId:s.id}} durationInFrames={s.duration} fps={30} width={1920} height={1080}/>)}
</>;
