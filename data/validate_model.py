"""Validate logical model artifacts, not a running database."""
from pathlib import Path
import json,xml.etree.ElementTree as E
R=Path(__file__).resolve().parent
model=json.loads((R/'model.json').read_text());data=json.loads((R/'fixtures.json').read_text())
assert set(data)==set(model)
checked=0;foreign=0
for table,rows in data.items():
 fields=model[table]['fields'];names={f['name'] for f in fields}
 for row in rows:
  assert set(row)==names,(table,'field mismatch')
  for f in fields:
   value=row[f['name']]
   if f['required']=='Так':assert value is not None,(table,f['name'])
   if value is not None and 'FK → ' in f['rule']:
    target,key=f['rule'].split('FK → ')[1].split(';')[0].split('.')
    assert any(parent[key]==value for parent in data[target]),(table,f['name'])
    foreign+=1
  checked+=1
seen=set();pages=[]
tree=E.parse(R/'erd.drawio')
master=E.parse(R.parent/'docs/models/coursework-diagrams.drawio')
for d in tree.findall('diagram'):
 cells=d.findall('.//mxCell');ids={c.get('id') for c in cells}
 assert len(ids)==len(cells)
 for c in cells:
  if c.get('id') in model:seen.add(c.get('id'))
  if c.get('edge')=='1':assert c.get('source') in ids and c.get('target') in ids
  if c.get('edge')=='1' or c.get('vertex')=='1':
   assert 'fontFamily=Times New Roman;' in c.get('style') and 'fontSize=14;' in c.get('style')
 # Compare XML structurally, ignoring whitespace inserted by indentation.
 md=master.find("./diagram[@id='"+d.get('id')+"']")
 assert md is not None
 def canonical(el):return (el.tag,tuple(sorted(el.attrib.items())),tuple(canonical(c) for c in el))
 assert canonical(d)==canonical(md)
 pages.append(d.get('id'))
assert seen==set(model)
result={'status':'passed','date':'2026-10-25','entities':len(model),'fixture_rows':checked,'non_null_fixture_foreign_keys':foreign,'erd_pages':pages,'all_entities_drawn':True,'master_synchronized':True,'font':'Times New Roman 14','limits':'Static XML/model/fixture checks only; no DBMS, SQL, API server or TEST-ID executed.'}
(R/'validation-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
