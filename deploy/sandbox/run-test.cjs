process.env.PLAYWRIGHT_BROWSERS_PATH='/ms-playwright';
const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{
 let server=null;
 try {await fetch('http://127.0.0.1:4173');} catch {server=require('child_process').spawn('node',['/opt/repropatch/serve.cjs'],{cwd:process.cwd(),stdio:'ignore'}); for(let i=0;i<100;i++){try{await fetch('http://127.0.0.1:4173');break;}catch{await new Promise(r=>setTimeout(r,100));}}}
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:960,height:720}});let errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto('http://127.0.0.1:4173');await page.waitForTimeout(100);
  const test=require(process.argv[2]);await test(page,assert);
  if(errors.length)throw new Error('Browser runtime error: '+errors.join('; '));
  console.log('PASS');
 }catch(e){console.error(String(e));process.exitCode=e instanceof assert.AssertionError?1:2;}
 finally{await browser.close();if(server)server.kill();}
})().catch(e=>{console.error(String(e));process.exitCode=2;});
