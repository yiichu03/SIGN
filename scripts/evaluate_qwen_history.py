#!/usr/bin/env python3
"""One resident Qwen2B; reuse the existing independent FP32 ABC logit reader."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from qwen_single_image import SingleImageJudge, probabilities_from_logits, validate_metadata
from prepare_qwen_history import dump, sha


def check_result(result):
    if not result['valid']:
        raise ValueError('Invalid probability: ' + str(result.get('error')))
    expected = probabilities_from_logits(result['logits'])
    for key in ['p_low', 'p_medium', 'p_high', 'q']:
        if abs(result[key]-expected[key]) > 1e-12:
            raise ValueError('Probability/logit formula mismatch')


def score(data, model):
    assert model.name == 'Qwen3.5-2B', 'This experiment is 2B only'
    spec = json.loads((data/'windows.json').read_text())
    inputs = spec['inputs']
    out = data/'scores'
    out.mkdir(exist_ok=False)
    run = dict(status='loading', model=str(model), model_config_sha256=sha(model/'config.json'),
               dtype='float32', batch_size=8, temperature=1, model_loads=0,
               method='independent single-image A/B/C logits; q=.5*p_medium+p_high',
               input_manifest_sha256=sha(data/'windows.json'),
               code_sha256={str(p.name):sha(p) for p in
                   [Path(__file__), Path(__file__).resolve().parents[1]/'src/qwen_single_image.py']})
    dump(out/'run.json', run)
    results = []
    started = time.perf_counter()
    try:
        judge = SingleImageJudge(model, (data/'prompts/history.txt').read_text(), dtype='float32')
        run.update(judge.environment)
        run['model_loads'] = 1
        for prompt_name in ['prompts/legacy.txt', 'prompts/history.txt']:
            selected = [r for r in inputs if r['prompt'] == prompt_name]
            judge.prompt = (data/prompt_name).read_text()
            fresh = []
            for row in selected:
                assert sha(data/row['image']) == row['image_sha256']
                assert sha(data/prompt_name) == row['prompt_version']
                validate_metadata(row['metadata'])
                if row['reused_score']:
                    old = json.loads((data/row['reused_score']).read_text())
                    assert old['image_sha256'] == row['image_sha256']
                    assert old['prompt_version'] == row['prompt_version']
                    assert all(old[k] == v for k,v in row['metadata'].items())
                    check_result(old)
                    # The original run used the identical 2B FP32 model/config.
                    original_run = data/'sources'/f"{row['cohort']}_2b_run.json"
                    old_run = json.loads(original_run.read_text())
                    assert old_run['model_config_sha256'] == run['model_config_sha256']
                    assert old_run['dtype'] == 'torch.float32'
                    assert Path(old_run['model_dir']).name == model.name
                    for key in ['torch', 'transformers']:
                        assert old_run[key] == judge.environment[key]
                    assert old_run['max_image_pixels'] == judge.max_pixels
                    assert old_run['enable_thinking'] is False
                    results.append(dict(**row, result={k:old[k] for k in
                        ['p_low','p_medium','p_high','q','logits','candidate_mass','valid','error']},
                        inference='reused_exact_published_input', seconds=None, timing_scope='not rerun'))
                else:
                    fresh.append(row)
            # Includes different text lengths and exact independent rows.
            probe = fresh[:1] + fresh[len(fresh)//2:len(fresh)//2+1] + fresh[-1:]
            images = [str(data/r['image']) for r in probe]
            metadata = [dict(r['metadata'], image=path) for r,path in zip(probe,images)]
            verified = judge.verify_readout(images, metadata)
            dump(out/('verify_'+Path(prompt_name).stem+'.json'), verified)
            if not verified['passed']:
                raise RuntimeError('Single/batch/answer-boundary verification failed')
            for index in range(0, len(fresh), 8):
                batch = fresh[index:index+8]
                images = [str(data/r['image']) for r in batch]
                metadata = [dict(r['metadata'], image=path) for r,path in zip(batch,images)]
                values, audit = judge.class_probabilities(images, metadata)
                # Audit actual serialized text: totals must really reach the model.
                for r, chat in zip(batch, audit['rendered_chats']):
                    stats = r['metadata']
                    if 'total_covered_area_m2' in stats:
                        assert '"total_covered_area_m2": '+str(stats['total_covered_area_m2']) in chat
                    assert '"action_count": '+str(stats['action_count']) in chat
                batch_name = 'batch_'+Path(prompt_name).stem+f'_{index//8:02d}.json'
                dump(out/batch_name, dict(items=batch, results=values, audit=audit))
                for row, value in zip(batch,values):
                    check_result(value)
                    results.append(dict(**row, result=value, inference='fresh_fp32_forward',
                        seconds=audit['seconds'], timing_scope='shared independent batch, not per-image latency',
                        batch_audit='scores/'+batch_name))
        assert len(results) == len(inputs) == len({r['id'] for r in results})
        dump(out/'results.json', results)
        run.update(status='complete', total=len(results), valid=sum(r['result']['valid'] for r in results),
                   reused=sum(r['inference']=='reused_exact_published_input' for r in results),
                   wall_seconds=time.perf_counter()-started)
    except Exception as exc:
        run.update(status='failed', error=repr(exc), completed_rows=len(results))
        dump(out/'partial_results.json', results)
        raise
    finally:
        dump(out/'run.json', run)
    print(json.dumps(run, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--model-dir', type=Path, required=True)
    a = p.parse_args()
    score(a.data.resolve(), a.model_dir.resolve())
