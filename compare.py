from contextlib import closing
"""Practical shared-infrastructure baseline: SQL invariants + SQLite checks."""
import json,sqlite3,tempfile,time
from pathlib import Path
import sma

def baseline(db,sql):
 with closing(sqlite3.connect(':memory:')) as c, c:
  with closing(sqlite3.connect(Path(db).as_uri()+'?mode=ro',uri=True)) as src, src:src.backup(c)
  before=list(c.execute('SELECT id,name,amount FROM people ORDER BY id'))
  denied=[];sma.guard(c,denied)
  try:c.executescript(sql)
  except sqlite3.Error as e:return {'passed':False,'error':str(e)}
  c.set_authorizer(None)
  checks={'integrity':list(c.execute('PRAGMA integrity_check'))==[('ok',)],'foreign_keys':not list(c.execute('PRAGMA foreign_key_check')),'business_values':list(c.execute('SELECT id,name,amount FROM people ORDER BY id'))==before}
  return {'passed':all(checks.values()),'checks':checks}

def main():
 records=[]
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);db=root/'source.sqlite';sma.fixture(db);p=sma.default_policy(db);(root/'policy.json').write_text(json.dumps(p))
  for i in range(10):
   for name,sql,expected in [('normal','UPDATE people SET name=name;',True),('loss',"DELETE FROM people WHERE id='日本';",False),('value','UPDATE people SET amount=0;',False),('foreign',"UPDATE orders SET person='missing';",False)]:
    (root/'migration.sql').write_text(sql)
    for mode in ('baseline','sma'):
     start=time.perf_counter()
     r=baseline(db,sql) if mode=='baseline' else sma.audit(db,root/'migration.sql',root/'policy.json',root/(name+str(i)))
     passed=r['passed'] if mode=='baseline' else r['exit_code']==0
     records.append({'iteration':i,'case':name,'mode':mode,'expected_pass':expected,'observed_pass':passed,'matched':passed==expected,'seconds':time.perf_counter()-start,'evidence':r})
  # Both practical baselines already detect value loss: no superiority claim.
 return {'records':records,'all_matched':all(r['matched'] for r in records),'executions':len(records),'human_work_seconds':None,'source_lines':{n:len(Path(n).read_text().splitlines()) for n in ('sma.py','compare.py')},'reproduction_commands':1,'limits':'Shared guard/fixture allowed; in-memory baseline versus disk/evidence SMA; timings not directly comparable. No measured scenario-addition effort.'}
if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
