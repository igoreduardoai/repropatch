const http=require('http');const esbuild=require('esbuild');
const fs=require('fs');
const server=http.createServer(async(req,res)=>{
 try{
 if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end('<!doctype html><html><head><meta charset="utf-8"></head><body><h1>ReproPatch public bug reproduction</h1><script src="/app.js"></script></body></html>');return;}
 if(req.url==='/app.js'){
  const result=await esbuild.build({entryPoints:[process.cwd()+'/demo.mjs'],bundle:true,write:false,format:'iife',alias:{'vanjs-core':process.cwd()+'/src/van.js'},logLevel:'silent'});
  res.setHeader('Content-Type','text/javascript');res.end(result.outputFiles[0].text);return;
 }
 res.statusCode=404;res.end('Not found');
 }catch(e){res.statusCode=500;res.end('Build error');console.error(String(e));}
});server.listen(4173,'127.0.0.1');
