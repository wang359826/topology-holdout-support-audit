from pathlib import Path
import sys, unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from summarize_results import normalize_support_booleans
import numpy as np
import pandas as pd

class SummaryRegression(unittest.TestCase):
 def frame(self):
  return pd.DataFrame(dict(novelty_class=['C0','C3','C3'],
   metal_seen=[True,False,True],linker1_seen=[True,True,False],
   linker2_seen=[True,True,False],n_unseen_linkers=[0,0,2],
   pair_seen=[True,True,False],coarse_seen=[True,False,False]))
 def test_empty_csv_fold_and_c3_partition(self):
  valid=self.frame()
  empty=pd.DataFrame(columns=valid.columns)
  pooled=pd.concat([valid,empty],ignore_index=True)
  fixed=normalize_support_booleans(pooled)
  self.assertEqual(fixed.metal_seen.dtype,np.dtype('bool'))
  self.assertEqual(fixed.coarse_seen.eq(False).mean(),2/3)
  c3=fixed[fixed.novelty_class.eq('C3')]
  self.assertEqual(sum(len(c3[c3.metal_seen.eq(False).eq(m)&c3.n_unseen_linkers.eq(n)]) for m in [False,True] for n in [0,1,2]),2)
  self.assertEqual(len(c3[c3.metal_seen.eq(False)&c3.n_unseen_linkers.eq(0)]),1)
 def test_empty_fold_is_valid(self):
  z=normalize_support_booleans(pd.DataFrame(columns=self.frame().columns))
  self.assertTrue(z.empty)
  self.assertEqual(z.coarse_seen.dtype,np.dtype('bool'))
 def test_invalid_flag_is_rejected(self):
  frame=self.frame()
  frame['metal_seen']=frame.metal_seen.astype(object)
  frame.loc[0,'metal_seen']='missing'
  with self.assertRaises(ValueError):
   normalize_support_booleans(frame)

if __name__=='__main__':
 unittest.main()
