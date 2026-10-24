'use strict';
const $=id=>document.getElementById(id);
const names=['Rotor magnet','Stator winding','Stator tooth','Stator yoke'];
const shortNames=['Rotor magnet','Winding','Tooth','Yoke'];
const signalNames=['d-axis current','q-axis current','d-axis voltage','q-axis voltage','Motor speed','Coolant temperature','Ambient temperature'];
const state={model:null,profiles:[],profile:null,result:null,component:0,index:0,focus:true,playing:false,worker:null,runId:0,options:null,warn:[85,115,95,85],stop:[105,135,115,105],lastTick:0};
const number=(v,n=1)=>Number.isFinite(v)?v.toFixed(n):'—';
const clock=s=>`${Math.floor(s/60).toString().padStart(2,'0')}:${Math.floor(s%60).toString().padStart(2,'0')}`;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));

async function getJSON(path){
  if(window.THERMO_ASSETS){if(!(path in window.THERMO_ASSETS))throw Error(`Missing embedded asset: ${path}`);return window.THERMO_ASSETS[path];}
  const r=await fetch(path);if(!r.ok)throw Error(`Cannot load ${path} (HTTP ${r.status}).`);return r.json();
}
function setStatus(text,progress=null){
  $('status-text').textContent=text;$('status').classList.toggle('complete',progress===null);
  if(progress!==null)$('progress').style.width=`${progress*100}%`;
}
function error(message){$('error').textContent=message;$('error').hidden=false;$('run').disabled=false;setStatus('Experiment could not complete.');}
function options(){
  const dt=state.profile.dt,total=(state.profile.rows.length-1)*dt;
  return{scenario:$('scenario').value,channel:Number($('channel').value),start:Math.round(total*Number($('start').value)/100/dt)*dt,duration:Number($('duration').value),bias:Number($('bias').value)};
}
function updateControls(){
  $('start-label').textContent=$('start').value+'%';$('duration-label').textContent=$('duration').value+' s';
  const unit=Number($('channel').value)===5?' °C':' V';
  $('bias-label').textContent=(Number($('bias').value)>=0?'+':'')+$('bias').value+unit;
  $('bias-controls').hidden=$('scenario').value!=='bias';
  const clean=$('scenario').value==='clean',combined=$('scenario').value==='combined';
  if(combined)$('channel').value='5';
  $('channel').disabled=clean||combined;$('start').disabled=clean;$('duration').disabled=clean;
}
function setDirty(){updateControls();if(state.result)setStatus('Settings changed. Run experiment to apply.');}
async function initWorker(){
  const source=window.THERMO_ENGINE||(await(await fetch('engine.js')).text());
  const blob=new Blob([source],{type:'text/javascript'}),url=URL.createObjectURL(blob);
  state.worker=new Worker(url);URL.revokeObjectURL(url);
  await new Promise((resolve,reject)=>{
    state.worker.onmessage=e=>{
      if(e.data.type==='ready'){state.worker.onmessage=onWorker;resolve();}
      else if(e.data.type==='error')reject(Error(e.data.message));
    };
    state.worker.onerror=e=>reject(Error(e.message||'Browser worker failed. Try the Python launcher.'));
    state.worker.postMessage({type:'init',model:state.model});
  });
}
function onWorker(e){
  const m=e.data;if(m.id&&m.id!==state.runId)return;
  if(m.type==='progress')setStatus(`Running local neural inference · ${Math.round(m.progress*100)}%`,m.progress);
  if(m.type==='error'){error(m.message);return;}
  if(m.type==='result'){
    state.result=m;$('run').disabled=false;$('chart-empty').hidden=true;
    ['export-report','export-csv','play','timeline'].forEach(id=>$(id).disabled=false);
    const start=state.options.scenario==='clean'?state.profile.rows.length*.45:state.options.start/state.profile.dt-30;
    state.index=clamp(Math.round(start),0,state.profile.rows.length-1);
    $('timeline').max=state.profile.rows.length-1;$('timeline').value=state.index;
    const kind=state.options.scenario==='clean'?'healthy signals':state.options.scenario==='bias'?'silent drift':state.options.scenario==='stuck'?'silent stuck reading':'injected dropout';
    setStatus(`Profile ${state.profile.id} · ${state.profile.rows.length.toLocaleString()} measured samples · ${kind} · inference complete`);
    updateUI();
  }
}
async function runExperiment(){
  const requestId=++state.runId;
  try{
    state.playing=false;$('play').textContent='▶';$('error').hidden=true;$('run').disabled=true;
    state.result=null;$('chart-empty').hidden=false;$('chart-empty').textContent='Running the trained neural models…';
    ['export-report','export-csv','play','timeline'].forEach(id=>$(id).disabled=true);
    setStatus('Loading held-out measured profile…',0);
    const id=Number($('profile').value),profile=await getJSON(`assets/profiles/${id}.json`);
    if(requestId!==state.runId)return;
    state.profile=profile;state.options=options();state.focus=state.options.scenario!=='clean';
    $('profile-info').textContent=`${number(profile.rows.length*profile.dt/60,1)} min · ${profile.rows.length.toLocaleString()} samples · test holdout`;
    state.worker.postMessage({type:'run',id:state.runId,profile,options:state.options});
  }catch(e){error(e.message+' Open the standalone HTML or start server.py if this browser blocks local files.');}
}
function color(temp){
  const colors=[[39,143,153],[158,194,167],[225,172,107],[209,100,79]],t=clamp((temp-20)/120,0,1)*3,i=Math.min(2,Math.floor(t)),u=t-i;
  return`rgb(${colors[i].map((c,j)=>Math.round(c+(colors[i+1][j]-c)*u)).join(',')})`;
}
function eventActive(i=state.index){const o=state.options,t=i*state.profile.dt;return o&&o.scenario!=='clean'&&t>=o.start&&t<o.start+o.duration;}
function torqueAt(i){return Math.min(...state.stop.map((s,k)=>clamp((s-state.result.upper[i*4+k])/(s-state.warn[k]),0,1)));}
function updateUI(){
  if(!state.result)return;
  $('play').setAttribute('aria-label',state.playing?'Pause measured replay':'Play measured replay');
  const i=state.index,k=state.component,r=state.result,row=state.profile.rows[i];
  $('kpi-temp').innerHTML=`${number(r.pred[i*4+k])}<small> °C</small>`;
  $('kpi-measured').innerHTML=`${number(row[7+k])}<small> °C</small>`;
  $('kpi-upper').innerHTML=`${number(r.upper[i*4+k])}<small> °C</small>`;
  $('kpi-torque').innerHTML=`${number(torqueAt(i)*100,0)}<small> %</small>`;
  $('kpi-component').textContent=names[k];
  $('component-list').innerHTML=names.map((n,j)=>`<div class="component-row"><span class="component-label"><i class="color-dot" style="background:${color(r.pred[i*4+j])}"></i>${n}</span><strong>${number(r.pred[i*4+j])} °C</strong></div>`).join('');
  ['heat-pm','heat-winding','heat-tooth','heat-yoke'].forEach((id,j)=>$(id).setAttribute('fill',color(r.pred[i*4+j])));
  const derated=torqueAt(i)<.995;$('motor-status').textContent=derated?'ADVISORY LIMIT':'ESTIMATED';$('motor-status').classList.toggle('warning',derated);
  const active=eventActive(),o=state.options,reported=active&&['dropout','combined'].includes(o.scenario);
  $('fault-badge').textContent=active?(reported?'REPORTED DROPOUT':'INJECTED SILENT ERROR'):'HEALTHY';
  $('fault-badge').classList.toggle('warning',active);
  const chips=[['i_d',0],['i_q',1],['u_d',2],['u_q',3],['speed',4],['coolant',5],['ambient',6]];
  $('sensor-list').innerHTML=chips.map(([label,j])=>`<span class="sensor-pill ${reported&&(o.scenario==='combined'?[3,5].includes(j):j===o.channel)?'missing':''}">${label}</span>`).join('');
  $('fault-note').textContent=active&&!reported?'A silent error is injected here. No event flag or onset is supplied to the neural estimator.':o.scenario==='combined'?'The combined event removes coolant temperature and q-axis voltage. Both receive missing-data flags.':'Known dropouts receive a missing-data flag. Silent drift and stuck readings do not.';
  const stat=r.stats.robust[k];$('score-mae').textContent=number(stat.mae,2)+' °C';$('score-baseline').textContent=number(r.stats.baseline[k].mae,2)+' °C';
  $('score-under').textContent=number(stat.p95_under,2)+' °C';$('score-coverage').textContent=number(stat.coverage*100,1)+'%';
  $('timeline').value=i;$('clock').textContent=`${clock(i*state.profile.dt)} / ${clock((state.profile.rows.length-1)*state.profile.dt)}`;
  $('focus').classList.toggle('active',state.focus);$('focus').textContent=state.focus?'Show full profile':'Focus event';
  $('chart-subtitle').textContent=names[k]+' · '+(state.focus?'event detail':'entire recorded profile');
  document.querySelectorAll('.component-chip').forEach((b,j)=>b.classList.toggle('active',j===k));
  drawChart();drawSparkline();
}
function range(){
  const n=state.profile.rows.length,o=state.options,dt=state.profile.dt;
  if(!state.focus||o.scenario==='clean')return[0,n-1];
  return[Math.max(0,Math.floor((o.start-180)/dt)),Math.min(n-1,Math.ceil((o.start+o.duration+300)/dt))];
}
function drawChart(){
  if(!state.result||$('view-replay').hidden)return;
  const canvas=$('chart'),rect=canvas.getBoundingClientRect(),ratio=Math.min(devicePixelRatio||1,2),w=rect.width,h=rect.height;
  if(!w)return;canvas.width=w*ratio;canvas.height=h*ratio;
  const ctx=canvas.getContext('2d');ctx.scale(ratio,ratio);
  const [a,b]=range(),k=state.component,r=state.result,rows=state.profile.rows,o=state.options;
  const pad={l:39,r:10,t:17,b:34},pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
  let low=Infinity,high=-Infinity;
  for(let i=a;i<=b;i++){for(const v of [rows[i][7+k],r.pred[i*4+k],r.baseline[i*4+k],r.upper[i*4+k]]){low=Math.min(low,v);high=Math.max(high,v);}}
  const extra=Math.max(3,(high-low)*.12);low=Math.floor((low-extra)/5)*5;high=Math.ceil((high+extra)/5)*5;
  const x=i=>pad.l+(i-a)/Math.max(1,b-a)*pw,y=v=>pad.t+(high-v)/(high-low)*ph;
  ctx.font='9px -apple-system,Segoe UI,sans-serif';ctx.fillStyle='#859aa5';ctx.fillText('°C',10,11);
  for(let j=0;j<=4;j++){
    const yy=pad.t+j*ph/4,val=high-j*(high-low)/4;
    ctx.strokeStyle='#eaf0f3';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(pad.l,yy);ctx.lineTo(w-pad.r,yy);ctx.stroke();
    ctx.fillStyle='#8ba0aa';ctx.textAlign='right';ctx.fillText(val.toFixed(0),pad.l-9,yy+3);
  }
  for(let j=0;j<=4;j++){
    const i=a+j*(b-a)/4;ctx.textAlign=j===4?'right':j===0?'left':'center';ctx.fillText((i*state.profile.dt/60).toFixed(1),x(i),h-17);
  }
  ctx.textAlign='right';ctx.fillStyle='#9badb6';ctx.fillText('time (min)',w-10,h-2);
  ctx.save();ctx.beginPath();ctx.rect(pad.l,pad.t,pw,ph);ctx.clip();
  if(o.scenario!=='clean'){
    const x1=x(o.start/state.profile.dt),x2=x((o.start+o.duration)/state.profile.dt);
    ctx.fillStyle='rgba(225,166,85,.13)';ctx.fillRect(x1,pad.t,x2-x1,ph);
    if(x1>=pad.l&&x1<w){ctx.setLineDash([3,4]);ctx.strokeStyle='#dbac71';ctx.beginPath();ctx.moveTo(x1,pad.t);ctx.lineTo(x1,h-pad.b);ctx.stroke();ctx.setLineDash([]);}
  }
  const step=Math.max(1,Math.floor((b-a)/700)),indices=[];for(let i=a;i<=b;i+=step)indices.push(i);if(indices.at(-1)!==b)indices.push(b);
  ctx.fillStyle='rgba(222,173,107,.1)';ctx.beginPath();indices.forEach((i,j)=>j?ctx.lineTo(x(i),y(r.upper[i*4+k])):ctx.moveTo(x(i),y(r.upper[i*4+k])));for(let j=indices.length-1;j>=0;j--){const i=indices[j];ctx.lineTo(x(i),y(r.pred[i*4+k]));}ctx.closePath();ctx.fill();
  function line(getter,stroke,width,dash=[]){ctx.strokeStyle=stroke;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.beginPath();indices.forEach((i,j)=>j?ctx.lineTo(x(i),y(getter(i))):ctx.moveTo(x(i),y(getter(i))));ctx.stroke();ctx.setLineDash([]);}
  line(i=>r.baseline[i*4+k],'#a7b5bf',1.4,[4,3]);line(i=>rows[i][7+k],'#24475c',1.8);line(i=>r.upper[i*4+k],'#cf9851',1.1,[4,4]);line(i=>r.pred[i*4+k],'#119c9a',2.2);
  if(state.index>=a&&state.index<=b){
    const xx=x(state.index),yy=y(r.pred[state.index*4+k]);ctx.strokeStyle='#9ab9c2';ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(xx,pad.t);ctx.lineTo(xx,h-pad.b);ctx.stroke();ctx.setLineDash([]);
    ctx.beginPath();ctx.arc(xx,yy,4,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.lineWidth=2;ctx.strokeStyle='#119c9a';ctx.stroke();
  }
  ctx.restore();
}
function drawSparkline(){
  const r=state.result,k=state.component,n=state.profile.rows.length,vals=Array.from({length:25},(_,j)=>r.pred[Math.floor(j*(n-1)/24)*4+k]),min=Math.min(...vals),max=Math.max(...vals);
  $('sparkline').innerHTML=`<svg viewBox="0 0 70 35"><polyline fill="none" stroke="#389e9e" stroke-width="1.4" points="${vals.map((v,j)=>`${j*70/24},${31-(v-min)/Math.max(1,max-min)*27}`).join(' ')}"/></svg>`;
}
function renderBenchmarks(){
  const q=state.model.evaluation_summary[$('benchmark-scenario').value];
  $('benchmark-body').innerHTML=names.map((n,k)=>`<tr><td>${n}</td><td>${number(q.baseline.mae[k],2)} °C</td><td>${number(q.robust.mae[k],2)} °C</td><td>${number(q.robust.rmse[k],2)} °C</td><td>${number(q.robust.p95_under[k],2)} °C</td><td>${number(q.robust.upper_coverage[k]*100,1)}%</td></tr>`).join('');
  $('split-info').innerHTML=Object.entries(state.model.split).map(([name,ids])=>`<div class="split-row"><span>${name[0].toUpperCase()+name.slice(1)}<br><small>IDs: ${ids.join(', ')}</small></span><strong>${ids.length} profiles</strong></div>`).join('');
}
function download(name,text,type){
  const a=document.createElement('a'),url=URL.createObjectURL(new Blob([text],{type}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);
}
function exportReport(){
  if(!state.result)return;
  const report={project:'ThermoGuard Motor',exported_at:new Date().toISOString(),profile_id:state.profile.id,held_out_test:true,
    sample_period_s:state.profile.dt,scenario:state.options,metrics:state.result.stats,inputs:state.model.inputs,targets:state.model.targets,
    model_architecture:state.model.architecture,calibration:state.model.calibration_description,
    dataset:state.model.audit,thresholds_illustrative:{warning_c:state.warn,stop_c:state.stop},limitations:state.model.limitations};
  download(`thermoguard-profile-${state.profile.id}-experiment.json`,JSON.stringify(report,null,2),'application/json');
}
function exportCSV(){
  if(!state.result)return;
  const cols=['time_s',...state.model.inputs.map(s=>'original_'+s),...names.flatMap((_,k)=>[`${state.model.targets[k]}_measured_c`,`${state.model.targets[k]}_neural_c`,`${state.model.targets[k]}_baseline_c`,`${state.model.targets[k]}_upper_c`]),'advisory_multiplier','injected_event','reported_coolant','reported_u_q','reported_u_d','missing_flag_coolant','missing_flag_u_q','missing_flag_u_d'];
  const lines=[cols.join(',')];
  for(let i=0;i<state.profile.rows.length;i++){
    const row=state.profile.rows[i],v=[i*state.profile.dt,...row.slice(0,7)];
    for(let k=0;k<4;k++)v.push(row[7+k],state.result.pred[i*4+k],state.result.baseline[i*4+k],state.result.upper[i*4+k]);
    v.push(torqueAt(i),eventActive(i)?1:0);
    const reported=[],flags=[];
    for(const ch of [5,3,2]){
      let value=row[ch],missing=0;const o=state.options;
      if(eventActive(i)){
        if((o.scenario==='dropout'&&ch===o.channel)||(o.scenario==='combined'&&[5,3].includes(ch))){value=null;missing=1;}
        else if(ch===o.channel&&o.scenario==='bias'){
          const a=Math.floor(o.start/state.profile.dt),b=Math.ceil((o.start+o.duration)/state.profile.dt);
          value+=o.bias*(i-a)/Math.max(1,b-a-1);
        }else if(ch===o.channel&&o.scenario==='stuck')value=state.profile.rows[Math.max(0,Math.floor(o.start/state.profile.dt)-1)][ch];
      }
      reported.push(value);flags.push(missing);
    }
    v.push(...reported,...flags);lines.push(v.map(n=>n===null?'':Number(n).toFixed(5)).join(','));
  }
  download(`thermoguard-profile-${state.profile.id}-predictions.csv`,lines.join('\n'),'text/csv');
}
function tick(time){
  if(state.playing&&state.result){
    const delta=state.lastTick?time-state.lastTick:0;
    state.fraction=(state.fraction||0)+delta/1000*Number($('speed').value)/state.profile.dt;
    const advance=Math.floor(state.fraction);
    if(advance){state.fraction-=advance;const [a,b]=range();if(state.index<a||state.index>b)state.index=a;state.index+=advance;
      if(state.index>b){state.index=b;state.playing=false;$('play').textContent='▶';}updateUI();}
  }
  state.lastTick=time;requestAnimationFrame(tick);
}
async function main(){
  try{
    [state.model,state.profiles]=await Promise.all([getJSON('assets/model.json'),getJSON('assets/profiles.json')]);
    $('profile').innerHTML=state.profiles.map(p=>`<option value="${p.id}">Profile ${p.id} · ${number(p.duration_s/60,0)} min</option>`).join('');
    $('component-tabs').innerHTML=shortNames.map((n,k)=>`<button class="component-chip ${k===0?'active':''}" data-k="${k}">${n}</button>`).join('');
    $('component-tabs').addEventListener('click',e=>{const b=e.target.closest('[data-k]');if(b){state.component=Number(b.dataset.k);updateUI();}});
    $('thresholds').innerHTML=names.map((n,k)=>`<label>${n}<br>Warn <input type="number" min="20" max="200" value="${state.warn[k]}" data-kind="warn" data-k="${k}" aria-label="${n} warning threshold"> °C<br>Stop <input type="number" min="21" max="220" value="${state.stop[k]}" data-kind="stop" data-k="${k}" aria-label="${n} stop threshold"> °C</label>`).join('');
    $('thresholds').addEventListener('change',e=>{
      if(!e.target.dataset.kind)return;const k=Number(e.target.dataset.k),kind=e.target.dataset.kind,val=Number(e.target.value),old=state[kind][k];state[kind][k]=val;
      if(!Number.isFinite(val)||state.stop[k]<=state.warn[k]){state[kind][k]=old;e.target.value=old;setStatus('Stop threshold must exceed warning threshold.');}updateUI();
    });
    $('model-info').textContent=`3 × ${state.model.members[0].parameter_count.toLocaleString()} learned parameters`;
    await initWorker();renderBenchmarks();updateControls();
    $('run').onclick=runExperiment;$('profile').onchange=runExperiment;
    ['scenario','channel','start','duration','bias'].forEach(id=>$(id).addEventListener('input',setDirty));
    $('benchmark-scenario').onchange=renderBenchmarks;
    $('focus').onclick=()=>{state.focus=!state.focus;updateUI();};
    $('timeline').oninput=e=>{state.index=Number(e.target.value);state.playing=false;$('play').textContent='▶';updateUI();};
    $('play').onclick=()=>{if(!state.result)return;const[a,b]=range();if(state.index>=b||state.index<a)state.index=a;state.playing=!state.playing;$('play').textContent=state.playing?'Ⅱ':'▶';updateUI();};
    $('chart').addEventListener('pointerdown',e=>{if(!state.result)return;const r=$('chart').getBoundingClientRect(),[a,b]=range();state.index=clamp(Math.round(a+(e.clientX-r.left-39)/(r.width-49)*(b-a)),a,b);updateUI();});
    $('export-csv').onclick=exportCSV;$('export-report').onclick=exportReport;
    document.querySelectorAll('.tab').forEach(btn=>btn.onclick=()=>{document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b===btn));document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==`view-${btn.dataset.tab}`);drawChart();});
    new ResizeObserver(()=>drawChart()).observe($('chart'));
    await runExperiment();requestAnimationFrame(tick);
  }catch(e){error(e.message+' If using a file URL, open ThermoGuard_Standalone.html or run python3 server.py.');}
}
main();
