"""Run the unchanged acceptance suite, force GC, display and gate ResourceWarning."""
import gc,json,platform,sys,unittest,warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
 with warnings.catch_warnings(record=True) as caught:
  warnings.simplefilter('always',ResourceWarning)
  suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
  result=unittest.TextTestRunner(verbosity=2,warnings='always').run(suite)
  del suite
  for _ in range(3):gc.collect()
 resource=[w for w in caught if issubclass(w.category,ResourceWarning)]
 for w in caught:sys.stderr.write(warnings.formatwarning(w.message,w.category,w.filename,w.lineno))
 summary={'python':platform.python_version(),'platform':platform.platform(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'resource_warning_count':len(resource),'gc_collections':3,'warning_filter':'always','passed':result.wasSuccessful() and not resource and not result.skipped}
 print(json.dumps(summary,indent=2));return 0 if summary['passed'] else 1
if __name__=='__main__':sys.exit(main())
