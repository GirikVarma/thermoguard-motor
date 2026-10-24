import json
import sys
import unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from thermoguard.core import features,fault_inputs,INPUTS,TARGETS,make_parity_fixture

class ProtocolTests(unittest.TestCase):
    def test_no_profile_leakage(self):
        split=json.loads((ROOT/'data/manifests/split.json').read_text())
        groups=[set(v) for v in split.values()]
        for i,g in enumerate(groups):
            for h in groups[i+1:]:self.assertFalse(g&h)
        self.assertEqual(len(set.union(*groups)),69)
    def test_no_target_input(self):
        self.assertFalse(set(INPUTS)&set(TARGETS))
        self.assertNotIn('torque',INPUTS)
    def test_features_are_causal(self):
        rng=np.random.default_rng(1);x=rng.normal(size=(150,7)).astype('float32');fallback=np.zeros(7)
        a=features(x,np.ones_like(x),fallback)
        changed=x.copy();changed[100:]+=100
        b=features(changed,np.ones_like(x),fallback)
        np.testing.assert_array_equal(a[:100],b[:100])
    def test_faults_do_not_mutate_source(self):
        x=np.ones((100,7),dtype='float32');old=x.copy()
        bad,mask=fault_inputs(x,'dropout',5,20,30)
        np.testing.assert_array_equal(x,old)
        self.assertEqual(int((mask[:,5]==0).sum()),15)
        self.assertTrue(np.isnan(bad[10:25,5]).all())
    def test_silent_errors_expose_no_mask(self):
        x=np.ones((100,7),dtype='float32')
        for case in ['bias','stuck']:
            _,mask=fault_inputs(x,case,5,20,30,10)
            self.assertTrue((mask==1).all())
    def test_model_export(self):
        m=json.loads((ROOT/'web/assets/model.json').read_text())
        self.assertEqual(len(m['members']),3)
        for model in m['members']+[m['baseline']]:
            self.assertEqual(len(model['mean']),49)
            self.assertEqual(len(model['layers']),3)
        self.assertEqual(len(m['upper_q']),4)

    def test_training_export_preserves_all_parity_scenarios(self):
        old=json.loads((ROOT/'tests/parity_fixture.json').read_text())
        m=json.loads((ROOT/'web/assets/model.json').read_text())
        fixture=make_parity_fixture(old['x'],m['members'][0],m['fallback'])
        self.assertEqual(len(fixture['cases']),7)
        self.assertEqual({c['options']['scenario'] for c in fixture['cases']},
                         {'clean','dropout','combined','bias','stuck'})
        for case in fixture['cases']:
            self.assertEqual(len(case['prediction']),len(fixture['indices']))
            self.assertTrue(np.isfinite(case['prediction']).all())

if __name__=='__main__':unittest.main()
