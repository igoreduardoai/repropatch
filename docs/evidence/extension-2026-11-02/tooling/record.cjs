process.env.PLAYWRIGHT_BROWSERS_PATH='/ms-playwright';
const {chromium}=require('/opt/repropatch/node_modules/playwright');
const steps={
 'vanx-truncate-915':async p=>{await p.waitForTimeout(1500);await p.click('#keep2');await p.waitForTimeout(2500);await p.click('#clear');await p.waitForTimeout(2500);},
 'van-setter-161':async p=>{await p.waitForTimeout(1500);await p.click('#render-icon');await p.waitForTimeout(3000);},
 'vanx-compact-063':async p=>{await p.waitForTimeout(1500);await p.locator('#points li').nth(1).locator('button').click();await p.waitForTimeout(1500);await p.click('#export');await p.waitForTimeout(3000);},
 'vanx-replace-c93':async p=>{await p.waitForTimeout(2000);await p.click('#sort');await p.waitForTimeout(3500);},
 'vanx-funcfield-5d9':async p=>{await p.waitForTimeout(2500);await p.click('#formal');await p.waitForTimeout(3000);},
 'vanx-raw-356':async p=>{await p.waitForTimeout(4500);},
 'vanx-poplen-fc3':async p=>{await p.waitForTimeout(2000);await p.click('#done');await p.waitForTimeout(2000);await p.click('#done');await p.waitForTimeout(2500);},
 'vanx-replacelen-acb':async p=>{await p.waitForTimeout(2000);await p.click('#top2');await p.waitForTimeout(3000);},
 'vanx-proxyarg-1c5':async p=>{await p.waitForTimeout(2000);await p.click('#add');await p.waitForTimeout(3000);},
 'van-propgc-84f':async p=>{await p.waitForTimeout(1500);await p.click('#tick');await p.waitForTimeout(1200);await p.click('#close');await p.waitForTimeout(1200);for(let i=0;i<3;i++){await p.click('#tick');await p.waitForTimeout(900);}await p.waitForTimeout(1500);},
};
(async()=>{
 const server=require('child_process').spawn('node',['/opt/repropatch/serve.cjs'],{cwd:'/workspace/repo',stdio:'inherit'});
 for(let i=0;i<100;i++){try{await fetch('http://127.0.0.1:4173');break;}catch{await new Promise(r=>setTimeout(r,100));}}
 const b=await chromium.launch({headless:true,args:['--no-sandbox']});
 const ctx=await b.newContext({viewport:{width:960,height:540},recordVideo:{dir:'/out/raw',size:{width:960,height:540}}});
 const p=await ctx.newPage();await p.goto('http://127.0.0.1:4173');
 await p.evaluate(()=>{document.body.style.font='20px sans-serif';document.body.style.margin='24px'});
 await steps[process.argv[2]](p);
 await ctx.close();await b.close();server.kill();
})().catch(e=>{console.error(e);process.exit(1)});
