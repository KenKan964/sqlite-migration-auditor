from contextlib import closing
import copy,json,os,sqlite3,tempfile,unittest
from pathlib import Path
import sma
CASES=[
('normal','SELECT 1;',0,None),
('add_column','ALTER TABLE people ADD COLUMN note TEXT;',0,None),
('rename','ALTER TABLE people RENAME COLUMN name TO label;',0,None),
('references','UPDATE people SET amount=amount;',0,None),
('add_row',"INSERT INTO people VALUES('c','carol',2);",0,None),
('transform','UPDATE people SET amount=amount*2;',0,None),
('empty','SELECT 1;',0,None),
('unicode','SELECT 1;',0,None),
('delete_row',"DELETE FROM people WHERE id='日本';",1,'DATA_LOSS'),
('tamper',"UPDATE people SET amount=8 WHERE id='a';",1,'DATA_LOSS'),
('drop','DROP TABLE orders;',1,'UNAPPROVED_SCHEMA_CHANGE'),
('duplicate',"DROP INDEX people_id; INSERT INTO people VALUES('a','x',1); DROP TABLE orders;",1,'DATA_LOSS'),
('orphan',"UPDATE orders SET person='absent';",1,'FOREIGN_KEY_VIOLATION'),
('fk_delete',"DELETE FROM people WHERE id='a';",1,'FOREIGN_KEY_VIOLATION'),
('unapproved_column','ALTER TABLE people ADD COLUMN x;',1,'UNAPPROVED_SCHEMA_CHANGE'),
('syntax','UPDTE people;',1,'MIGRATION_FAILED'),
('partial',"DELETE FROM people WHERE id='日本'; BAD SQL;",1,'MIGRATION_FAILED'),
('wrong_schema','SELECT 1;',1,'UNAPPROVED_SCHEMA_CHANGE'),
('unapproved_add',"INSERT INTO people VALUES('z','z',1);",1,'UNAPPROVED_ROW_ADDITION'),
('null_key',"UPDATE people SET id=NULL WHERE id='日本';",1,'DATA_LOSS'),
('attach',"ATTACH 'outside.sqlite' AS other;",1,'MIGRATION_FAILED'),
('vacuum',"VACUUM INTO 'outside.sqlite';",1,'MIGRATION_FAILED'),
('extension',"SELECT load_extension('nonexistent');",1,'MIGRATION_FAILED'),
('pragma','PRAGMA writable_schema=ON;',1,'MIGRATION_FAILED'),
('transaction','BEGIN; UPDATE people SET amount=0;',2,'UNVERIFIABLE'),
('invalid_policy','SELECT 1;',2,'UNVERIFIABLE'),
('missing_column','ALTER TABLE people DROP COLUMN name;',1,'DATA_LOSS'),
('approved_drop','ALTER TABLE people DROP COLUMN name;',0,None),
('ascii_upper','UPDATE people SET name=upper(name);',0,None),
('existing','SELECT 1;',2,'UNVERIFIABLE'),
('symlink','SELECT 1;',2,'UNVERIFIABLE'),
('source_duplicate','SELECT 1;',2,'UNVERIFIABLE'),
]
class Acceptance(unittest.TestCase):pass

def case_test(name,sql,exit_code,code):
 def test(self):
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);db=base/'source.sqlite';sma.fixture(db)
   if name=='empty':
    with closing(sqlite3.connect(db)) as c, c:c.executescript('DELETE FROM orders; DELETE FROM people;')
   if name=='source_duplicate':
    with closing(sqlite3.connect(db)) as c, c:c.executescript("DROP TABLE orders; DROP INDEX people_id; INSERT INTO people VALUES('a','x',1); CREATE TABLE orders(id TEXT, person TEXT);")
   p=sma.default_policy(db)
   if name in ('add_column','rename','approved_drop'):
    expected={'add_column':'CREATE TABLE people(id TEXT, name TEXT, amount INTEGER, note TEXT)', 'rename':'CREATE TABLE people(id TEXT, label TEXT, amount INTEGER)', 'approved_drop':'CREATE TABLE people(id TEXT, amount INTEGER)'}
    p['expected_schema']['table:people']=expected[name]
   if name=='rename':p['tables']['people']['columns']['name']['to']='label'
   if name=='approved_drop':del p['tables']['people']['columns']['name'];p['tables']['people']['drop_columns']=['name']
   if name=='add_row':p['tables']['people']['allow_additions']=True
   if name=='transform':p['tables']['people']['columns']['amount']['transform']='double_integer'
   if name=='ascii_upper':p['tables']['people']['columns']['name']['transform']='upper_ascii'
   if name=='wrong_schema':p['expected_schema']={}
   if name=='invalid_policy':p['version']=99
   (base/'policy.json').write_text(json.dumps(p));(base/'migration.sql').write_text(sql)
   out=base/'trial'
   if name=='existing':out.mkdir();(out/'marker').write_bytes(b'keep')
   if name=='symlink':
    try:(base/'link').symlink_to(db)
    except OSError:self.skipTest('symlink creation unavailable')
    db=base/'link'
   before=sma.digest(db);r=sma.audit(db,base/'migration.sql',base/'policy.json',out,name)
   self.assertEqual(r['exit_code'],exit_code,r)
   if code:self.assertIn(code,[x['code'] for x in r['findings']],r)
   self.assertEqual(sma.digest(db),before)
   if name=='existing':self.assertEqual((out/'marker').read_bytes(),b'keep')
   self.assertFalse((base/'outside.sqlite').exists())
   self.assertFalse(Path('outside.sqlite').exists())
   if os.environ.get('SMA_EVIDENCE'):
    dest=Path(os.environ['SMA_EVIDENCE']);dest.mkdir(exist_ok=True,parents=True)
    (dest/(name+'.json')).write_text(json.dumps({'expected_exit':exit_code,'expected_code':code,'source_unchanged':sma.digest(db)==before,'report':r},indent=2,ensure_ascii=False))
 return test
for n,s,e,c in CASES:setattr(Acceptance,'test_'+n,case_test(n,s,e,c))
if __name__=='__main__':unittest.main()
