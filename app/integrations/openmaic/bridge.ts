import {readFileSync} from 'node:fs';
import {projectSchema} from '../../vendor/openmaic-v1.4.0/domain/project/project-schema';
import {startOrchestration,completeTeaching,submitDecision,recordArtifact,completeArtifactReview,completeCurrentStage,recordEvaluation,recordQuiz,completeRecap,allowedStudentActions} from '../../vendor/openmaic-v1.4.0/domain/orchestration/transition';

// This program executes fixed upstream state-machine code, never learner code.
try {
  const raw=readFileSync(0,'utf8');
  if(Buffer.byteLength(raw)>1_000_000)throw new Error('Contract input too large');
  const input=JSON.parse(raw),project=projectSchema.parse(input.project);
  let state=input.state,events:any[]=[];
  const apply=(result:any)=>{state=result.state;events.push(...result.events)};
  switch(input.command){
    case 'start':apply(startOrchestration(project));break;
    case 'inspect':break;
    case 'teaching':apply(completeTeaching(project,state));break;
    case 'decision':apply(submitDecision(project,state,input.payload));break;
    case 'artifact':apply(recordArtifact(project,state,input.payload));break;
    case 'review':apply(completeArtifactReview(project,state,input.payload.kind));break;
    case 'next':apply(completeCurrentStage(project,state));break;
    case 'evaluation':apply(recordEvaluation(project,state,input.payload,{remediationId:input.payload.id+'-repair'}));break;
    case 'quiz':apply(recordQuiz(project,state,input.payload));break;
    case 'recap':apply(completeRecap(project,state));break;
    default:throw new Error('Unsupported contract operation');
  }
  process.stdout.write(JSON.stringify({ok:true,state,events,actions:allowedStudentActions(project,state)}));
}catch(error:any){process.stdout.write(JSON.stringify({ok:false,error:'PBL_TRANSITION_REJECTED',detail:String(error?.message||error).slice(0,1000)}));process.exitCode=1}
