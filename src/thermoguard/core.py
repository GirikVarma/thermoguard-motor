"""Shared, causal feature and fault protocol used by training and export."""
from __future__ import annotations

import numpy as np
import pandas as pd

INPUTS = ['i_d', 'i_q', 'u_d', 'u_q', 'motor_speed', 'coolant', 'ambient']
TARGETS = ['pm', 'stator_winding', 'stator_tooth', 'stator_yoke']
TARGET_NAMES = ['Rotor magnet', 'Stator winding', 'Stator tooth', 'Stator yoke']
DT = 2.0
TAUS = [10.0, 60.0, 300.0, 900.0]
HISTORY = [0, 1, 4, 5, 7, 9]


def fault_inputs(x, scenario='clean', channel=5, start=600., duration=120., bias=10., dt=DT):
    """Return damaged measurements and availability. Never access target labels."""
    out = np.array(x, dtype=np.float32, copy=True)
    mask = np.ones_like(out)
    a = max(0, min(len(x), int(start / dt)))
    b = max(a, min(len(x), int(np.ceil((start + duration) / dt))))
    channels = [channel]
    if scenario == 'combined':
        channels = [5, 3]
    if scenario in ('dropout', 'combined'):
        out[a:b, channels] = np.nan
        mask[a:b, channels] = 0
    elif scenario == 'bias':
        out[a:b, channel] += np.linspace(0, bias, b-a, dtype=np.float32)
    elif scenario == 'stuck' and b > a:
        out[a:b, channel] = x[max(0, a-1), channel]
    elif scenario != 'clean':
        raise ValueError(f'Unknown scenario: {scenario}')
    return out, mask


def features(x, mask, fallback, dt=DT):
    """First-order thermal-history bank. Causal, no measured target feedback."""
    x = np.array(x, dtype=np.float32, copy=True)
    mask = np.array(mask, dtype=np.float32, copy=True)
    ages = np.zeros_like(x)
    # Known missing measurements: short hold, then training-input median.
    for j in range(7):
        last = float(fallback[j])
        age = 0.
        for i in range(len(x)):
            if mask[i,j] > .5 and np.isfinite(x[i,j]):
                last, age = float(x[i,j]), 0.
            else:
                mask[i,j] = 0.
                age += dt
                x[i,j] = last if age <= 20. else fallback[j]
            ages[i,j] = min(age, 900.) / 900.
    i2 = x[:,0]**2 + x[:,1]**2
    power = np.abs(x[:,0]*x[:,2] + x[:,1]*x[:,3])
    base = np.column_stack([x, i2, np.abs(x[:,4]), power])
    cols = [base]
    for tau in TAUS:
        hist = pd.DataFrame(base[:,HISTORY]).ewm(alpha=1-np.exp(-dt/tau), adjust=False).mean()
        cols.append(hist.to_numpy(dtype=np.float32))
    cols.extend([mask, ages, np.minimum(np.arange(len(x))*dt,3600.)[:,None]/3600.])
    return np.column_stack(cols).astype(np.float32)


def numpy_predict(model, f, ambient):
    h = (f - np.array(model['mean'],np.float32)) / np.array(model['scale'],np.float32)
    for layer in model['layers']:
        h = h @ np.array(layer['weight'],np.float32).T + np.array(layer['bias'],np.float32)
        if layer['activation'] == 'relu': h = np.maximum(h,0)
    return h*50. + ambient[:,None]


def metrics(y, pred, upper=None):
    err = y-pred
    out = {'mae':np.mean(np.abs(err),axis=0).tolist(),
           'rmse':np.sqrt(np.mean(err**2,axis=0)).tolist(),
           'p95_under':np.quantile(np.maximum(err,0),.95,axis=0).tolist(),
           'max_under':np.maximum(err,0).max(axis=0).tolist()}
    if upper is not None:
        out['upper_coverage'] = (y<=upper).mean(axis=0).tolist()
        out['upper_margin'] = np.mean(upper-pred,axis=0).tolist()
    return out


def make_parity_fixture(x, model, fallback):
    """Export all browser parity cases after every training run."""
    x = np.round(np.asarray(x, dtype=np.float32), 4)
    if not len(x):
        raise ValueError('A parity fixture needs at least one measured sample.')
    indices = sorted({min(i, len(x)-1) for i in [0,49,50,80,110,150,399]})
    cases = []
    for name, channel in [('clean',5),('dropout',5),('dropout',3),
                          ('dropout',2),('combined',2),('bias',5),('stuck',5)]:
        options = {'scenario':name,'channel':channel,'start':100,
                   'duration':120,'bias':-10}
        damaged, mask = fault_inputs(x,name,channel,100,120,-10)
        ff = features(damaged,mask,fallback)
        pred = numpy_predict(model,ff,x[:,6])
        cases.append({'options':options,'features':ff[indices].tolist(),
                      'prediction':pred[indices].tolist()})
    return {'x':x.tolist(),'indices':indices,'cases':cases}
