module.exports=async(page,assert)=>{
  const btn=page.locator('#target');
  assert.equal(await btn.evaluate(e=>e.disabled),true,'initially disabled');
  await page.evaluate(()=>{window.state.val=false;});
  await page.waitForTimeout(50);
  assert.equal(await btn.evaluate(e=>e.disabled),false,'enabled after state false');
  // ordinary attrs / events via van tags sanity in page context
  const ok=await page.evaluate(()=>{
    const b=window.van.tags.button({id:'x2',disabled:window.van.state(false),onclick:()=>window.__c=(window.__c||0)+1},'hi');
    document.body.append(b); b.click(); return !b.disabled && b.id==='x2' && window.__c===1;
  });
  assert.equal(ok,true);
};