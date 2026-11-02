import assert from 'node:assert/strict';
import {pageRows} from './app.mjs';
const data = [
 {id:1,status:'active'}, {id:2,status:'inactive'}, {id:3,status:'active'},
 {id:4,status:'inactive'}, {id:5,status:'active'}, {id:6,status:'active'},
];
try {
 const actual = pageRows(data, 'active', 2, 2);
 assert.deepEqual(actual.rows.map(r => r.id), [5,6]);
 assert.equal(actual.total, 4);
 console.log(JSON.stringify({status:'PASS', assertion:'active_page_2'}));
} catch (error) {
 if (error.code !== 'ERR_ASSERTION') throw error;
 console.log(JSON.stringify({status:'ASSERTION_FAILED',assertion:'active_page_2',message:error.message}));
 process.exitCode=1;
}
