import argparse,hashlib,io,json,sys,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'companion'))
import utr_baselines as ub
import verify
parser = argparse.ArgumentParser(description="Read-only checks of archived predictions against pinned source labels")
parser.add_argument("--inputs", type=Path, required=True)
parser.add_argument("--records", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
source = args.inputs / 'mrl-sample-designed.parquet'
assert hashlib.sha256(source.read_bytes()).hexdigest()==ub.PINS[source.name]['sha256']
src=pd.read_parquet(source)
geo_source = args.inputs / 'GSM3130443_designed_library.csv.gz'
assert hashlib.sha256(geo_source.read_bytes()).hexdigest() == ub.PINS[geo_source.name]['sha256']
geo = pd.read_csv(geo_source, usecols=['utr', 'mother'])
rebuilt = verify.rebuild_components(src.sequence.str[25:75], dict(zip(geo.utr.str[:50], geo.mother.str[:50])))

records=pd.read_parquet(args.records)
assert np.array_equal(rebuilt, records.component)
assert np.array_equal(verify.grouped_allocation(rebuilt), records.split_grouped)
with zipfile.ZipFile(ROOT / 'downloads/utr-baselines-results.zip') as z:
 prefix='utr-baselines-results/run/'
 prep=json.loads(z.read(prefix+'prepare.json'))
 verify.validate_population(records,src.sequence.to_list(),src.target_mrl_designed.to_numpy(),prep)
 metrics=json.loads(z.read(prefix+'metrics.json'))
 diffs=[]; checked=[]
 for split in ub.SPLITS:
  test=records[records['split_'+split]=='test']
  for method in ub.ALL_METHODS:
   pred=pd.read_parquet(io.BytesIO(z.read(prefix+f'runs/{split}/{method}/predictions.parquet')))
   ub.validate_predictions(records,pred,split)
   p=pred.set_index('source_index').loc[test.source_index,'prediction'].to_numpy()
   y=src.target_mrl_designed.to_numpy()[test.source_index]
   expected=metrics['splits'][split]['methods'][method]
   for key,value in ub.regression_metrics(y,p).items():
    if isinstance(value,(int,float)) and key in expected:diffs.append(abs(value-expected[key]))
   for key in ('mse_ci95','precision_at_k_ci95'):
    assert np.isfinite(expected[key]).all()
   checked.append({'split':split,'method':method,'validation_test_predictions':len(pred),'test_predictions':len(test)})
 assert max(diffs)<1e-9
 report={'scope':'Read-only archived prediction population, finite-value and source-label metric checks; no fitting or bootstrap rerun',
 'archive_sha256':hashlib.sha256((ROOT / 'downloads/utr-baselines-results.zip').read_bytes()).hexdigest(),
 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'records_sha256':hashlib.sha256((args.records).read_bytes()).hexdigest(),
 'independent_bfs_components_and_grouped_allocation_match':True,
 'checks':checked,'max_abs_metric_difference':max(diffs),'all_passed':True}
 args.output.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'method_split_pairs':len(checked),'max_abs_metric_difference':max(diffs)}))
