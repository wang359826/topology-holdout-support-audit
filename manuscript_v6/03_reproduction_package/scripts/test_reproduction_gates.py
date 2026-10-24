from pathlib import Path
import sys,json,importlib.util,unittest
from unittest.mock import patch
import pandas as pd
P=Path(__file__).resolve().parents[1]
def load_module(name,rel):
 spec=importlib.util.spec_from_file_location(name,P/rel)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
l2=load_module('reproduction_level2','level2_predictions/verify_predictions.py')
l3=load_module('reproduction_level3','level3_rerun/run_subset.py')
class GateRegression(unittest.TestCase):
 def test_missing_prediction_seed_is_failure(self):
  original=Path.is_file
  with patch.object(Path,'is_file',lambda path:False if path.name=='predictions_arms_seed244.csv' else original(path)):
   with self.assertRaisesRegex(ValueError,'missing prediction file'):l2.check_arms(P,1e-6)
 def test_deleted_prediction_group_is_failure(self):
  original=pd.read_csv
  def corrupt(path,*args,**kw):
   data=original(path,*args,**kw)
   if Path(path).name=='predictions_arms_seed42.csv':data=data[~((data.strategy=='nbo:e')&(data.fit_population=='cleaned'))]
   return data
  with patch.object(pd,'read_csv',corrupt):
   with self.assertRaisesRegex(ValueError,'group set differs'):l2.check_arms(P,1e-6)
 def test_duplicate_material_is_failure(self):
  original=pd.read_csv
  def corrupt(path,*args,**kw):
   data=original(path,*args,**kw)
   if Path(path).name=='predictions_screening_seed42.csv':data=pd.concat([data,data.iloc[:1]],ignore_index=True)
   return data
  with patch.object(pd,'read_csv',corrupt):
   with self.assertRaisesRegex(ValueError,'duplicate material'):l2.check_screening(P)
 def test_missing_archive_is_failure(self):
  with self.assertRaisesRegex(ValueError,'missing reference archive'):l3.validate_archive(P/'nonexistent_reference.csv')
 def test_empty_or_partial_reference_is_failure(self):
  path=P/'outputs/followup_20261023/experiment12/full/pooled_metrics.csv'
  data=pd.read_csv(path)
  for sample in (data.iloc[:0],data[data.representation!='I']):
   with self.subTest(rows=len(sample)),patch.object(pd,'read_csv',return_value=sample):
    with self.assertRaisesRegex(ValueError,'exactly one G, B and I'):l3.validate_archive(path)
 def test_wrong_raw_input_checksum_is_failure(self):
  with self.assertRaisesRegex(ValueError,'SHA256 or byte size'):l3.validate_input(P/'config/config.json',P/'config/config.json')
if __name__=='__main__':unittest.main(verbosity=2)
