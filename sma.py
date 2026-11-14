from contextlib import closing
"""SQLite Migration Auditor: trusted local SQL, isolated Backup API copies."""
import argparse, hashlib, json, os, re, sqlite3, sys, time, uuid
from pathlib import Path
VERSION='0.1.0'
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def q(s): return '"'+s.replace('"','""')+'"'
def safe_path(p):
 p=Path(os.path.abspath(p))
 if any(x.is_symlink() for x in [p,*p.parents]): raise ValueError('symlink path rejected')
 return p

def schema(c):
 return {r[0]+':'+r[1]:r[2] for r in c.execute("SELECT type,name,sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")}
def pack(v):
 if isinstance(v,bytes):return {'blob_hex':v.hex()}
 return {'type':type(v).__name__,'value':v}
def rows(c,table,key):
 data={};cur=c.execute('SELECT * FROM '+q(table));names=[d[0] for d in cur.description]
 if key not in names:raise ValueError('missing business key '+key)
 for row in cur:
  d=dict(zip(names,row));k=d[key]
  if k is None or not isinstance(k,(str,int)):raise ValueError('business key must be non-null text/integer')
  token=json.dumps(pack(k),sort_keys=True)
  if token in data:raise ValueError('duplicate business ID '+token)
  data[token]=d
 return data,names

def policy_check(p):
 if not isinstance(p,dict) or set(p)!={'version','tables','expected_schema'} or p['version']!=1:raise ValueError('policy fields/version')
 if not isinstance(p['expected_schema'],dict) or not all(isinstance(k,str) and (isinstance(v,str) or v is None) for k,v in p['expected_schema'].items()):raise ValueError('expected_schema must be complete schema map')
 if not isinstance(p['tables'],dict) or not p['tables']:raise ValueError('tables required')
 for name,t in p['tables'].items():
  if not isinstance(name,str) or not isinstance(t,dict) or set(t)!={'key','columns','drop_columns','allow_additions'}:raise ValueError('table policy fields')
  if not isinstance(t['key'],str) or not isinstance(t['columns'],dict) or type(t['allow_additions']) is not bool or not isinstance(t['drop_columns'],list):raise ValueError('table policy types')
  if not all(isinstance(x,str) for x in t['drop_columns']) or len(set(t['drop_columns']))!=len(t['drop_columns']):raise ValueError('drop_columns')
  targets=[]
  for col,r in t['columns'].items():
   if not isinstance(col,str) or not isinstance(r,dict) or set(r)!={'to','transform'} or not isinstance(r['to'],str) or r['transform'] not in ('identity','upper_ascii','double_integer'):raise ValueError('column mapping/transform')
   targets.append(r['to'])
  if len(targets)!=len(set(targets)) or set(t['columns'])&set(t['drop_columns']):raise ValueError('ambiguous column mapping')
  if t['key'] not in t['columns'] or t['columns'][t['key']]!={'to':t['key'],'transform':'identity'}:raise ValueError('business key must be preserved unchanged')
 return p

def guard(c,denied):
 c.enable_load_extension(False)
 forbidden={sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH,sqlite3.SQLITE_CREATE_VTABLE,sqlite3.SQLITE_DROP_VTABLE,sqlite3.SQLITE_PRAGMA}
 def auth(action,a,b,db,trigger):
  if action==sqlite3.SQLITE_ALTER_TABLE: db=a
  bad=action in forbidden or (db not in (None,'main') and not (db=='temp' and action in (sqlite3.SQLITE_READ,sqlite3.SQLITE_UPDATE) and a=='sqlite_temp_master')) or (action==sqlite3.SQLITE_FUNCTION and (b or '').lower() in ('load_extension','writefile','readfile'))
  if bad:denied.append({'action':action,'arg1':a,'arg2':b,'database':db});return sqlite3.SQLITE_DENY
  return sqlite3.SQLITE_OK
 c.set_authorizer(auth)

def transform(v,kind):
 if kind=='identity':return v
 if kind=='double_integer' and type(v) is int:return 2*v
 if kind=='upper_ascii' and isinstance(v,str) and v.isascii():return v.upper()
 raise ValueError('transform not defined for source value')

def audit(db,sql,policy,out,operation_id='migration-001'):
 report={'schema_version':'sma-report-v1','tool_version':VERSION,'operation_id':operation_id,'copy_id':str(uuid.uuid4()),'status':'UNVERIFIABLE','exit_code':2,'findings':[]}
 c=None;created=False
 def finding(code,**kw):report['findings'].append({'code':code,**kw})
 try:
  db=safe_path(db);sql=safe_path(sql);policy=safe_path(policy);out=safe_path(out)
  if not all(p.is_file() for p in (db,sql,policy)):raise ValueError('regular input files required')
  p=policy_check(json.loads(policy.read_text(encoding='utf-8'),object_pairs_hook=unique_object))
  script=sql.read_text(encoding='utf-8')
  if len(script)>1_000_000:raise ValueError('SQL exceeds 1MB limit')
  out.mkdir(mode=0o700);created=True
  report['inputs']={'db_sha256_before':digest(db),'sql_sha256':digest(sql),'policy_sha256':digest(policy)}
  c=sqlite3.connect(out/'trial.sqlite');c.execute('PRAGMA trusted_schema=OFF')
  start=time.monotonic()
  with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,timeout=2)) as source, source:
   def progress(*args):
    if time.monotonic()-start>10:raise TimeoutError('backup deadline')
   source.backup(c,pages=128,progress=progress,sleep=.01)
  report['snapshot_schema']=schema(c);report['sqlite_version']=sqlite3.sqlite_version
  report['source_user_version']=c.execute('PRAGMA user_version').fetchone()[0]
  before={}
  for table,t in p['tables'].items():
   before[table],columns=rows(c,table,t['key'])
   if set(columns)!=set(t['columns'])|set(t['drop_columns']):raise ValueError('every source column must be preserved or explicitly dropped: '+table)
  report['before_counts']={k:len(v) for k,v in before.items()}
  denied=[];guard(c,denied);deadline=time.monotonic()+5
  c.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
  try:c.executescript(script)
  except sqlite3.Error as e:finding('MIGRATION_FAILED',error=str(e),denied=denied)
  finally:c.set_authorizer(None);c.set_progress_handler(None,0)
  if c.in_transaction:
   c.rollback();finding('UNVERIFIABLE',reason='migration left an open transaction; rolled back pending work')
  report['after_schema']=schema(c)
  report['integrity_check']=[r[0] for r in c.execute('PRAGMA integrity_check')]
  report['foreign_key_check']=[list(r) for r in c.execute('PRAGMA foreign_key_check')]
  if report['integrity_check']!=['ok']:finding('INTEGRITY_VIOLATION',rows=report['integrity_check'])
  if report['foreign_key_check']:finding('FOREIGN_KEY_VIOLATION',rows=report['foreign_key_check'])
  if report['after_schema']!=p['expected_schema']:finding('UNAPPROVED_SCHEMA_CHANGE',expected=p['expected_schema'],observed=report['after_schema'])
  for table,t in p['tables'].items():
   try:after,cols=rows(c,table,t['key'])
   except (ValueError,sqlite3.Error) as e:finding('DATA_LOSS',table=table,reason=str(e));continue
   for key,old in before[table].items():
    if key not in after:finding('DATA_LOSS',table=table,key=key,reason='missing row');continue
    for col,r in t['columns'].items():
     expected=transform(old[col],r['transform']);actual=after[key].get(r['to'])
     if r['to'] not in cols or pack(expected)!=pack(actual):finding('DATA_LOSS',table=table,key=key,column=r['to'],expected=pack(expected),observed=pack(actual))
   added=sorted(set(after)-set(before[table]))
   if added and not t['allow_additions']:finding('UNAPPROVED_ROW_ADDITION',table=table,keys=added)
   for col in t['drop_columns']:
    if col in cols:finding('UNAPPROVED_SCHEMA_CHANGE',table=table,column=col,reason='declared deletion not performed')
  report['inputs']['db_sha256_after']=digest(db)
  report['inputs']['main_file_unchanged']=report['inputs']['db_sha256_before']==report['inputs']['db_sha256_after']
  if not report['inputs']['main_file_unchanged']:finding('UNVERIFIABLE',reason='source changed during inspection; external writer or unsafe environment')
  report['exit_code']=2 if any(x['code']=='UNVERIFIABLE' for x in report['findings']) else int(bool(report['findings']))
  report['status']=['PASS','FAIL','UNVERIFIABLE'][report['exit_code']]
 except (ValueError,OSError,sqlite3.Error,TimeoutError,TypeError) as e:
  finding('UNVERIFIABLE',reason=str(e));report['exit_code']=2;report['status']='UNVERIFIABLE'
 finally:
  if c is not None:c.close()
 if created:
  try:(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  except OSError as e:report['status']='UNVERIFIABLE';report['exit_code']=2;finding('UNVERIFIABLE',reason='report write failed: '+str(e))
 return report

def unique_object(items):
 d={}
 for k,v in items:
  if k in d:raise ValueError('duplicate JSON key '+k)
  d[k]=v
 return d

def fixture(path):
 with closing(sqlite3.connect(path)) as c, c:
  c.executescript("CREATE TABLE people(id TEXT, name TEXT, amount INTEGER); CREATE TABLE orders(id TEXT, person TEXT REFERENCES people(id)); CREATE UNIQUE INDEX people_id ON people(id); INSERT INTO people VALUES('a','alice',7),('日本','bob',9); INSERT INTO orders VALUES('o1','a');")

def default_policy(db):
 with closing(sqlite3.connect(db)) as c, c:
  return {'version':1,'expected_schema':schema(c),'tables':{t:{'key':'id','columns':{r[1]:{'to':r[1],'transform':'identity'} for r in c.execute('PRAGMA table_info('+q(t)+')')},'drop_columns':[],'allow_additions':False} for t in ('people','orders')}}

def main(argv=None):
 try:
  a=argparse.ArgumentParser();sub=a.add_subparsers(dest='command',required=True)
  d=sub.add_parser('demo');d.add_argument('--out',required=True)
  r=sub.add_parser('run')
  for flag in ('db','sql','policy','out'):r.add_argument('--'+flag,required=True)
  r.add_argument('--operation-id',default='migration-001');args=a.parse_args(argv)
  if args.command=='demo':
   base=safe_path(args.out);base.mkdir(mode=0o700);fixture(base/'source.sqlite');p=default_policy(base/'source.sqlite');(base/'policy.json').write_text(json.dumps(p,indent=2));(base/'migration.sql').write_text("UPDATE people SET name=name;\n");result=audit(base/'source.sqlite',base/'migration.sql',base/'policy.json',base/'trial')
  else:result=audit(args.db,args.sql,args.policy,args.out,args.operation_id)
 except (OSError,ValueError) as e:result={'schema_version':'sma-report-v1','status':'UNVERIFIABLE','exit_code':2,'findings':[{'code':'UNVERIFIABLE','reason':str(e)}]}
 print(json.dumps(result,ensure_ascii=False));return result['exit_code']
if __name__=='__main__':sys.exit(main())
