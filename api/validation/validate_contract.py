"""Run from project root with openapi-spec-validator==0.7.2 installed."""
from pathlib import Path
import copy, json, platform, hashlib, importlib.metadata as md
import yaml
from openapi_spec_validator import validate
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'api/openapi.yaml';s=yaml.safe_load(p.read_text())
validate(s)
def expand(x):
 if isinstance(x,dict):
  if '$ref' in x:
   assert x['$ref'].startswith('#/components/schemas/')
   return expand(s['components']['schemas'][x['$ref'].split('/')[-1]])
  return {k:expand(v) for k,v in x.items()}
 if isinstance(x,list):return [expand(v) for v in x]
 return x
def validator(name):return Draft202012Validator(expand(s['components']['schemas'][name]),format_checker=FormatChecker())
checks=[]
for record in json.loads((ROOT/'api/examples/manifest.json').read_text()):
 example=json.loads((ROOT/'api/examples'/record['file']).read_text())
 validator(record['schema']).validate(example)
 checks.append(record['file'])
valid=json.loads((ROOT/'api/examples/create-request.json').read_text())
negative=[]
for title,mod in [('foreign-owner',{'requesterId':'00000000-0000-4000-8000-000000000002'}),('server-state',{'state':'closed'}),('oversize-title',{'title':'а'*151}),('empty-title',{'title':''}),('invalid-category-format',{'categoryId':'not-a-uuid'})]:
 example=valid|mod
 assert list(validator('CreateTicketRequest').iter_errors(example)),title
 negative.append(title)
for name,example,title in [('StateRequest',{'expectedVersion':1,'toState':'cancelled'},'undefined-state'),('AssignmentRequest',{'expectedVersion':0,'assigneeId':valid['categoryId']},'invalid-version'),('User',{'id':valid['categoryId'],'login':'demo','displayName':'demo','active':True,'roles':['requester'],'version':1,'credential_hash':'secret'},'secret-in-output')]:
 assert list(validator(name).iter_errors(example)),title
 negative.append(title)
ids=[op['operationId'] for item in s['paths'].values() for method,op in item.items() if method in ['get','post','put','delete','patch']]
assert len(ids)==len(set(ids))
assert set(x for item in s['paths'].values() for op in item.values() for x in op.get('x-requirements',[]))=={f'US-{i:02d}' for i in range(1,11)}
# Arithmetic example from BR-07; not a server test.
assert ((50+40+30)*60*1000)==7200000
assert not (7200000>7200000)
result={'status':'passed','date':'2026-10-25','python':platform.python_version(),'tools':{k:md.version(k) for k in ['openapi-spec-validator','openapi-schema-validator','jsonschema','PyYAML']},'specification':'OpenAPI 3.1.1','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'operations':len(ids),'positive_examples':len(checks),'negative_schema_cases':len(negative),'positive_files':checks,'negative_cases':negative,'arithmetic_example':'120 minutes; equality not breached','limits':'Static contract and example validation only. TEST-01–TEST-39 not executed. No server, database transaction, access-control or load tests.'}
(ROOT/'api/validation/result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
