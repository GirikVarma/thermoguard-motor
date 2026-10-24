/* Executes the actual browser worker against independent Python reference values. */
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const model=JSON.parse(fs.readFileSync(path.join(root,'web/assets/model.json'),'utf8'));
const fixture=JSON.parse(fs.readFileSync(path.join(root,'tests/parity_fixture.json'),'utf8'));
let resolver,rejecter;
const context={Float32Array,Float64Array,Math,Number,Array,NaN,Promise,setTimeout,onmessage:null,
  postMessage(message){if(message.type==='error')rejecter(Error(message.message));if(message.type==='result')resolver(message);}};
vm.runInNewContext(fs.readFileSync(path.join(root,'web/engine.js'),'utf8'),context);
context.onmessage({data:{type:'init',model}});
async function main(){
 assert.equal(fixture.cases.length,7,'Training must export all seven parity scenarios.');
 let maxPrediction=0,maxScaledFeature=0,id=0;
 for(const test of fixture.cases){
  const promise=new Promise((a,b)=>{resolver=a;rejecter=b;});
  context.onmessage({data:{type:'run',id:++id,profile:{id:0,dt:2,rows:fixture.x.map(r=>r.concat([0,0,0,0]))},options:test.options,probeIndices:fixture.indices}});
  const result=await promise;
  for(let p=0;p<fixture.indices.length;p++){
   const probe=result.featureProbe[p];assert.equal(probe.i,fixture.indices[p]);
   for(let j=0;j<49;j++){const a=probe.features[j],b=test.features[p][j];maxScaledFeature=Math.max(maxScaledFeature,Math.abs(a-b)/(1+Math.abs(b)));}
   for(let k=0;k<4;k++)maxPrediction=Math.max(maxPrediction,Math.abs(probe.prediction[k]-test.prediction[p][k]));
  }
  assert(result.pred.every(Number.isFinite));assert(result.upper.every(Number.isFinite));
 }
 assert(maxPrediction<.03,`Prediction mismatch: ${maxPrediction} C`);
 assert(maxScaledFeature<.003,`Feature mismatch: ${maxScaledFeature}`);
 console.log(JSON.stringify({passed:true,scenarios:id,max_prediction_difference_c:maxPrediction,max_relative_feature_difference:maxScaledFeature}));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
