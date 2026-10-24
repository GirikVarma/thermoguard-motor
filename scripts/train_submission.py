"""Train the submission models on measured data; export a dependency-free web demo.

Run from the project root: .venv/bin/python scripts/train_submission.py
The download is handled separately; this script never silently synthesizes data.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from thermoguard.core import INPUTS,TARGETS,TARGET_NAMES,DT,TAUS,HISTORY,features,fault_inputs,numpy_predict,metrics,make_parity_fixture

torch.set_num_threads(2)


def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,allow_nan=False,separators=(',',':')))


def subset_idx(n,limit=1200):
    return np.linspace(0,n-1,min(n,limit)).astype(int)


def collect(profiles,ids,fallback,augmented):
    xs=[]; ys=[]
    rng=np.random.default_rng(54)
    for pid in ids:
        x,y=profiles[pid]
        variants=[('clean',5,600.,120.,0.)]
        if augmented:
            length=len(x)*DT
            for scenario,channel in [('dropout',5),('combined',3)]:
                duration=min(float(rng.choice([120,300,600])),length*.35)
                start=float(rng.uniform(.15,.65)*max(1,length-duration))
                variants.append((scenario,channel,start,duration,0.))
        for case,ch,start,duration,bias in variants:
            fx,mask=fault_inputs(x,case,ch,start,duration,bias)
            ff=features(fx,mask,fallback)
            ix=subset_idx(len(ff))
            xs.append(ff[ix]);ys.append((y[ix]-x[ix,6,None])/50.)
    return np.concatenate(xs),np.concatenate(ys)


def train_one(x,y,vx,vy,seed,name,epochs=65):
    torch.manual_seed(seed)
    rng=np.random.default_rng(seed)
    mean=x.mean(0); scale=x.std(0); constant=scale<1e-5;scale[constant]=1.
    a=torch.from_numpy(((x-mean)/scale).astype('float32'))
    b=torch.from_numpy(y.astype('float32'))
    va=torch.from_numpy(((vx-mean)/scale).astype('float32'))
    vb=torch.from_numpy(vy.astype('float32'))
    net=nn.Sequential(nn.Linear(x.shape[1],96),nn.ReLU(),nn.Linear(96,64),nn.ReLU(),nn.Linear(64,4))
    with torch.no_grad(): net[0].weight[:,constant]=0.
    opt=torch.optim.AdamW(net.parameters(),lr=.0015,weight_decay=.0001)
    best=float('inf');best_state=None; stale=0;history=[]
    t0=time.perf_counter()
    for epoch in range(epochs):
        net.train(); total=0.
        order=rng.permutation(len(a))
        for start in range(0,len(a),1024):
            ix=order[start:start+1024]
            pred=net(a[ix]);err=pred-b[ix]
            loss=(err**2).mean()
            opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(net.parameters(),5.);opt.step()
            total+=loss.item()*len(ix)
        net.eval()
        with torch.no_grad(): score=(net(va)-vb).abs().mean().item()*50.
        history.append({'epoch':epoch+1,'train_mse_scaled':total/len(a),'val_mae_c':score})
        if score<best-.003:
            best=score;best_state={k:v.detach().clone() for k,v in net.state_dict().items()};stale=0
        else: stale+=1
        if epoch%10==0 or stale>=10: print(f'{name}: epoch {epoch+1}, validation MAE {score:.3f} C, best {best:.3f}',flush=True)
        if stale>=10: break
    net.load_state_dict(best_state)
    layers=[]
    for i in [0,2,4]:
        layers.append({'weight':net[i].weight.detach().numpy().round(8).tolist(),
                       'bias':net[i].bias.detach().numpy().round(8).tolist(),
                       'activation':'relu' if i<4 else 'linear'})
    model={'name':name,'seed':seed,'mean':mean.tolist(),'scale':scale.tolist(),'layers':layers,
           'validation_mae_c':best,'epochs':len(history),'history':history,
           'parameter_count':sum(p.numel() for p in net.parameters()),'training_seconds':time.perf_counter()-t0}
    print(f'{name} complete: {best:.3f} C in {model["training_seconds"]:.1f}s',flush=True)
    return model


def ensemble(models,ff,ambient):
    ps=np.stack([numpy_predict(m,ff,ambient) for m in models])
    return ps.mean(0),np.maximum(ps.std(0),2.)


def main():
    t0=time.perf_counter()
    path=ROOT/'data/raw/measures_v2.csv'
    if not path.exists(): raise SystemExit('Measured dataset missing. Follow README data acquisition steps.')
    d=pd.read_csv(path,dtype='float32')
    assert not d.isna().any().any(),'Audit unexpected missing data before training.'
    ids=sorted(d.profile_id.astype(int).unique().tolist())
    order=np.random.default_rng(42).permutation(ids).tolist()
    nt=int(len(ids)*.5);nv=max(1,round(len(ids)*.1));nc=int(len(ids)*.2)
    split={'train':order[:nt],'validation':order[nt:nt+nv],
           'calibration':order[nt+nv:nt+nv+nc],'test':order[nt+nv+nc:]}
    assert len(set(sum(split.values(),[])))==len(ids)
    profiles={int(pid):(g[INPUTS].to_numpy(),g[TARGETS].to_numpy()) for pid,g in d.groupby('profile_id',sort=False)}
    # Downsample 0.5-second recordings to a 2-second thermal replay.
    profiles={pid:(x[::4].copy(),y[::4].copy()) for pid,(x,y) in profiles.items()}
    fallback=np.median(np.concatenate([profiles[p][0] for p in split['train']]),axis=0)
    audit={'rows_native':len(d),'profiles':len(ids),'native_sample_period_s':.5,'replay_sample_period_s':DT,
           'missing_values':int(d.isna().sum().sum()),'csv_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
           'input_columns':INPUTS,'target_columns':TARGETS,'excluded_from_model':['torque','profile_id']+TARGETS,
           'license':'CC BY-SA 4.0','dataset_api_version':3,'downloaded_on':'2026-10-25',
           'source':'https://www.kaggle.com/datasets/wkirgsn/electric-motor-temperature',
           'profile_lengths_native':{str(int(p)):int(n) for p,n in d.groupby('profile_id').size().items()}}
    dump(ROOT/'data/manifests/audit.json',audit);dump(ROOT/'data/manifests/split.json',split)
    del d
    print('Profile split:',split,flush=True)
    cx,cy=collect(profiles,split['train'],fallback,False)
    vx,vy=collect(profiles,split['validation'],fallback,True)
    baseline=train_one(cx,cy,vx,vy,7,'Clean-trained baseline')
    rx,ry=collect(profiles,split['train'],fallback,True)
    robust=[train_one(rx,ry,vx,vy,seed,f'Fault-trained member {i+1}') for i,seed in enumerate([11,23,37])]
    scores=[]
    for pid in split['calibration']:
        x,y=profiles[pid]
        for case,ch in [('clean',5),('dropout',5),('dropout',3),('combined',5)]:
            fx,mask=fault_inputs(x,case,ch,len(x)*DT*.45,120.)
            pred,std=ensemble(robust,features(fx,mask,fallback),x[:,6])
            ix=subset_idx(len(x),400)
            scores.append((y[ix]-pred[ix])/std[ix])
    q=np.maximum(np.quantile(np.concatenate(scores),.9,axis=0),0.)
    print('Empirical 90% upper multipliers:',q,flush=True)
    eval_rows=[]
    for pid in split['test']:
        x,y=profiles[pid]
        for case,ch in [('clean',5),('dropout',5),('dropout',3),('combined',5),('bias',5),('stuck',5)]:
            fx,mask=fault_inputs(x,case,ch,len(x)*DT*.45,120.,10.)
            ff=features(fx,mask,fallback)
            pred,std=ensemble(robust,ff,x[:,6]);base=numpy_predict(baseline,ff,x[:,6])
            upper=pred+q*std
            eval_rows.append({'profile':pid,'scenario':case,'channel':INPUTS[ch],
                              'robust':metrics(y,pred,upper),'baseline':metrics(y,base)})
    summary={}
    for case in ['clean','dropout','combined','bias','stuck']:
        rows=[r for r in eval_rows if r['scenario']==case]
        summary[case]={}
        for method in ['baseline','robust']:
            summary[case][method]={key:np.mean([r[method][key] for r in rows],axis=0).tolist()
                                   for key in rows[0][method]}
    evaluation={'summary':summary,'per_profile':eval_rows,'split':split,
                'protocol':'Whole-profile holdout. Macro averages. 120 s fault at 45% of profile. Unreported errors get no mask.',
                'calibration':'Empirical, profile-balanced 90th percentile of standardized positive residuals on separate calibration profiles. Not a profile-level coverage guarantee.',
                'hardware':platform.platform(),'torch_version':torch.__version__,'training_total_seconds':time.perf_counter()-t0}
    dump(ROOT/'results/evaluation.json',evaluation)
    export={'format_version':1,'inputs':INPUTS,'targets':TARGETS,'target_names':TARGET_NAMES,
            'dt':DT,'taus':TAUS,'history_indices':HISTORY,'fallback':fallback.tolist(),
            'baseline':baseline,'members':robust,'upper_q':q.tolist(),'scale_floor_c':2.,
            'calibration_description':evaluation['calibration'],'audit':audit,'split':split,
            'evaluation_summary':summary,'architecture':'49 inputs / Dense(96) / ReLU / Dense(64) / ReLU / Dense(4). First-order causal history filters.',
            'limitations':['Single measured motor platform.','Data faults are injected, not physical motor failures.',
                           'Upper bounds are empirical and can miss under distribution shift.',
                           'Torque advice does not change recorded temperatures.']}
    dump(ROOT/'web/assets/model.json',export)
    info=[]
    for pid in split['test']:
        x,y=profiles[pid]
        rows=np.concatenate([x,y],axis=1).round(4).tolist()
        dump(ROOT/f'web/assets/profiles/{pid}.json',{'id':pid,'dt':DT,'rows':rows})
        info.append({'id':pid,'samples':len(x),'duration_s':len(x)*DT,
                     'max_temperatures':y.max(0).round(2).tolist()})
    dump(ROOT/'web/assets/profiles.json',info)
    # Independent test fixture for JS/Python inference and fault-feature parity.
    pid=split['test'][0];x,y=profiles[pid]
    small=x[:400]
    fixture=make_parity_fixture(small,robust[0],fallback)
    dump(ROOT/'tests/parity_fixture.json',fixture)
    print('Complete. Clean robust MAE per component:',summary['clean']['robust']['mae'],flush=True)


if __name__=='__main__':main()
