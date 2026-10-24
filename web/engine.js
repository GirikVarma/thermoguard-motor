/* Local neural inference. Only the first seven measured columns enter the model. */
'use strict';
let cfg, activeRun=0;
function prepareModel(m){
  return {...m,mean:Float32Array.from(m.mean),scale:Float32Array.from(m.scale),
    layers:m.layers.map(l=>({...l,weight:l.weight.map(r=>Float32Array.from(r)),bias:Float32Array.from(l.bias),buffer:new Float32Array(l.bias.length)})),
    input:new Float32Array(m.mean.length)};
}
function predict(m,f,ambient){
  let v=m.input;
  for(let j=0;j<v.length;j++)v[j]=(f[j]-m.mean[j])/m.scale[j];
  for(const layer of m.layers){
    const out=layer.buffer;
    for(let j=0;j<out.length;j++){
      const w=layer.weight[j];let s=layer.bias[j];
      for(let k=0;k<v.length;k++)s+=w[k]*v[k];
      out[j]=layer.activation==='relu'?Math.max(0,s):s;
    }
    v=out;
  }
  return [v[0]*50+ambient,v[1]*50+ambient,v[2]*50+ambient,v[3]*50+ambient];
}
function stepFeatures(raw,index,state,options,dt){
  const values=raw.slice(0,7), mask=new Float32Array(7).fill(1);
  const t=index*dt, inside=t>=options.start&&t<options.start+options.duration;
  const ch=options.channel;
  if(inside){
    if(options.scenario==='dropout'){values[ch]=NaN;mask[ch]=0;}
    if(options.scenario==='combined'){values[5]=NaN;values[3]=NaN;mask[5]=0;mask[3]=0;}
    if(options.scenario==='bias'){
      const a=Math.floor(options.start/dt),b=Math.ceil((options.start+options.duration)/dt);
      values[ch]+=options.bias*(index-a)/Math.max(1,b-a-1);
    }
    if(options.scenario==='stuck')values[ch]=state.stuck;
  }
  if(index===Math.max(0,Math.floor(options.start/dt)-1))state.stuck=raw[ch];
  for(let j=0;j<7;j++){
    if(mask[j]&&Number.isFinite(values[j])){state.last[j]=values[j];state.age[j]=0;}
    else{state.age[j]+=dt;values[j]=state.age[j]<=20?state.last[j]:cfg.fallback[j];}
  }
  const base=values.concat([values[0]**2+values[1]**2,Math.abs(values[4]),Math.abs(values[0]*values[2]+values[1]*values[3])]);
  const f=new Float32Array(49);f.set(base);let offset=10;
  for(let a=0;a<cfg.taus.length;a++){
    const alpha=1-Math.exp(-dt/cfg.taus[a]);
    for(let j=0;j<cfg.history_indices.length;j++){
      const v=base[cfg.history_indices[j]];
      state.history[a][j]=index===0?v:alpha*v+(1-alpha)*state.history[a][j];
      f[offset++]=state.history[a][j];
    }
  }
  f.set(mask,34);
  for(let j=0;j<7;j++)f[41+j]=Math.min(state.age[j],900)/900;
  f[48]=Math.min(index*dt,3600)/3600;
  return f;
}
function makeState(){return{last:cfg.fallback.slice(),age:new Float64Array(7),history:cfg.taus.map(()=>new Float64Array(6)),stuck:0};}
function quantile(values,p){values.sort((a,b)=>a-b);const q=(values.length-1)*p,i=Math.floor(q);return values[i]+(values[Math.ceil(q)]-values[i])*(q-i);}
async function run(message){
  const token=++activeRun,{profile,options,id}=message,n=profile.rows.length,dt=profile.dt;
  const pred=new Float32Array(n*4),baseline=new Float32Array(n*4),upper=new Float32Array(n*4);
  const state=makeState();state.stuck=profile.rows[0][options.channel];
  const featureProbe=[];
  for(let i=0;i<n;i++){
    if(token!==activeRun)return;
    const row=profile.rows[i],f=stepFeatures(row,i,state,options,dt),amb=row[6];
    const b=predict(cfg.baseline,f,amb), members=cfg.members.map(m=>predict(m,f,amb));
    for(let k=0;k<4;k++){
      const mu=members.reduce((s,p)=>s+p[k],0)/members.length;
      const sd=Math.max(cfg.scale_floor_c,Math.sqrt(members.reduce((s,p)=>s+(p[k]-mu)**2,0)/members.length));
      pred[i*4+k]=mu;baseline[i*4+k]=b[k];upper[i*4+k]=mu+cfg.upper_q[k]*sd;
    }
    if(message.probeIndices?.includes(i))featureProbe.push({i,features:Array.from(f),prediction:predict(cfg.members[0],f,amb)});
    if(i%250===0){postMessage({type:'progress',id,progress:i/n});await new Promise(r=>setTimeout(r,0));}
  }
  const stats={robust:[],baseline:[]};
  for(let k=0;k<4;k++){
    for(const [name,arr] of [['robust',pred],['baseline',baseline]]){
      let ae=0,se=0,max=0,covered=0;const under=[];
      for(let i=0;i<n;i++){
        const e=profile.rows[i][7+k]-arr[i*4+k];ae+=Math.abs(e);se+=e*e;under.push(Math.max(e,0));max=Math.max(max,e);
        if(profile.rows[i][7+k]<=upper[i*4+k])covered++;
      }
      const summary={mae:ae/n,rmse:Math.sqrt(se/n),p95_under:quantile(under,.95),max_under:max};
      if(name==='robust')summary.coverage=covered/n;
      stats[name].push(summary);
    }
  }
  if(token===activeRun)postMessage({type:'result',id,pred,baseline,upper,stats,featureProbe},[pred.buffer,baseline.buffer,upper.buffer]);
}
onmessage=e=>{
  try{
    if(e.data.type==='init'){
      cfg=e.data.model;cfg.baseline=prepareModel(cfg.baseline);cfg.members=cfg.members.map(prepareModel);
      postMessage({type:'ready'});
    }else if(e.data.type==='run')run(e.data).catch(error=>postMessage({type:'error',id:e.data.id,message:error.message}));
  }catch(error){postMessage({type:'error',message:error.message});}
};
