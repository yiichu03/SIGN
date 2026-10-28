from pathlib import Path
import json,math,sys
HERE=Path(__file__).resolve().parent;folder=Path(sys.argv[1]);run=json.loads((folder/'run.json').read_text());v=json.loads((folder/'verification.json').read_text())
assert run['status']=='complete' and run['total']==run['valid']==16 and v['passed']
scored=json.loads((folder/'scores.json').read_text());rows=scored['results'];assert len(rows)==16
assert len({(r['group_id'],r['id']) for r in rows})==16
for row in rows:
 assert row['valid'] and all(math.isfinite(row[k]) for k in ['p_low','p_medium','p_high','q'])
 assert abs(sum(row[k] for k in ['p_low','p_medium','p_high'])-1)<1e-12
 assert abs(row['q']-.5*row['p_medium']-row['p_high'])<1e-12
 assert abs(row['new_area_m2']/row['action_count']-row['new_area_m2_per_action'])<1e-12
 assert row['prompt_version']==run['prompt_version']
lines=['| 图片 | 动作数 | 新增m² | m²/动作 | P(LOW) | P(MEDIUM) | P(HIGH) | q |','|---|---:|---:|---:|---:|---:|---:|---:|']
for r in rows:lines.append('| %s/%s | %d | %.4f | %.4f | %.4f | %.4f | %.4f | %.4f |'%(r['group_id'],r['id'],r['action_count'],r['new_area_m2'],r['new_area_m2_per_action'],r['p_low'],r['p_medium'],r['p_high'],r['q']))
(folder/'results_table.md').write_text('\n'.join(lines)+'\n')
summary={'result_folder':str(folder),'valid_images':16,'prompt_version':run['prompt_version'],'dtype':run['dtype'],'verification':v,'candidate_mass_range':[min(r['candidate_mass'] for r in rows),max(r['candidate_mass'] for r in rows)]}
(folder/'checked_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('\n'.join(lines));print('VERIFICATION',json.dumps(v));print('MASS',summary['candidate_mass_range'])
