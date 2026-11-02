// Public development checks. These may be shown to the developer/agent.
import assert from 'node:assert/strict';
import {pageRows} from './app.mjs';
const data = [
 {id:1,status:'active'}, {id:2,status:'inactive'}, {id:3,status:'active'},
 {id:4,status:'inactive'}, {id:5,status:'active'}, {id:6,status:'active'},
];
const tests=[
 ['inactive_still_works',()=>assert.deepEqual(pageRows(data,'inactive',1,2).rows.map(r=>r.id),[2,4])],
 ['empty_result',()=>assert.deepEqual(pageRows(data,'missing',1,2),{rows:[],total:0})],
 ['total_before_pagination',()=>assert.equal(pageRows(data,'active',3,2).total,4)],
];
const results=tests.map(([name,fn])=>{try{fn();return {name,passed:true}}catch(e){return {name,passed:false}}});
console.log(JSON.stringify({passed:results.filter(r=>r.passed).length,total:results.length,tests:results}));
process.exitCode=results.every(r=>r.passed)?0:1;
