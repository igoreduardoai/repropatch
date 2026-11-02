// Independent fixture checks: not mounted or returned to the agent.
// Public in this distribution for inspectability, NOT a secret benchmark.
// For real runs, maintainer tests live outside target workspaces and are run
// only after finalization; never report fixture scores as real model scores.
import assert from 'node:assert/strict';
import {pageRows} from './app.mjs';
const rows = Array.from({length:11},(_,i)=>({id:100+i,status:i%3===0?'inactive':'active'}));
const tests=[];
for(const status of ['active','inactive']) {
 for(const page of [1,2,3,6]) {
  const want=rows.filter(r=>r.status===status);
  tests.push([`${status}_page_${page}`,()=>assert.deepEqual(pageRows(rows,status,page,2),
    {rows:want.slice((page-1)*2,page*2),total:want.length})]);
 }
}
const results=tests.map(([name,fn])=>{try{fn();return {name,passed:true}}catch{return {name,passed:false}}});
console.log(JSON.stringify({passed:results.filter(r=>r.passed).length,total:results.length,tests:results}));
process.exitCode=results.every(r=>r.passed)?0:1;
