export interface Run {
 id:string;title:string;method:'W0'|'W1';mode:'fixture'|'live';status:string;
 created_at:string;updated_at:string;case_id:string;result:Result|null;
 payload:{expected_behavior:string;video_id?:string|null};
 events?:RunEvent[];artifacts?:Artifact[];
}
export interface RunEvent {id:number;at:string;stage:string;kind:string;message:string;data:Record<string,unknown>}
export interface Artifact {id:string;name:string;sha256:string;size:number;content_type:string}
export interface Result {
 source:string;benchmark_eligible:boolean;model_calls:number;verified:boolean;method:string;
 reproduced:boolean;false_success:boolean;regressions:number;patch:string;cost_usd:number;
 duration_ms:number;frozen_test_sha256:string;candidate_sha256:string;
 independent?:{passed:number;total:number};evaluation?:{independent?:{passed:boolean};public_regressions?:{passed:boolean};frozen_reproduction?:{outcome:string}};limitation:string;reason?:string;operator_interventions?:number;
}
export interface Config {model:string;live_enabled:boolean;run_cap_usd:number;batch_cap_usd:number;reason:string;live_cases?:{case_id:string;title:string;expected_behavior:string;base_commit:string}[]}
export interface Budget {cap_usd:number;committed_usd:number;settled_usd:number;halted:string|null;scope:string}
let token='';
export function setToken(value:string){token=value}
export async function request<T>(path:string,options:RequestInit={}):Promise<T>{
 const headers=new Headers(options.headers);headers.set('Authorization','Bearer '+token);
 if(options.body && !(options.body instanceof FormData))headers.set('Content-Type','application/json');
 const response=await fetch('/api'+path,{...options,headers});
 if(!response.ok){
  let detail=`Request failed (${response.status})`;
  try{const data=await response.json();detail=typeof data.detail==='string'?data.detail:detail}catch{/* retain status */}
  throw new Error(detail);
 }
 return response.json() as Promise<T>;
}
export async function download(runId:string,artifact:Artifact){
 const response=await fetch(`/api/runs/${runId}/artifacts/${artifact.id}`,{headers:{Authorization:'Bearer '+token}});
 if(!response.ok)throw new Error('Artifact download failed');
 const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');
 a.href=url;a.download=artifact.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
