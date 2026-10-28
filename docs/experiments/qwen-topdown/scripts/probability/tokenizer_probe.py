import sys,json
from pathlib import Path
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;TREE=ROOT/'SIGN-qwen-topdown-judge'
sys.path.insert(0,str(TREE/'src'))
from qwen_single_image import load_manifest,conversations,response_positions
from transformers import AutoProcessor
_,rows=load_manifest(HERE/'manifest.json');processor=AutoProcessor.from_pretrained(ROOT/'models/Qwen3.5-9B',local_files_only=True)
processor.tokenizer.padding_side='left';prompt=(TREE/'scripts/prompts/qwen_single_coverage_abc.txt').read_text();chosen=[rows[0],rows[10],rows[-1]]
messages=conversations([r['image'] for r in chosen],prompt,chosen)
inputs=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,return_dict=True,return_tensors='pt',processor_kwargs={'text_kwargs':{'padding':True},'images_kwargs':{'size':{'shortest_edge':65536,'longest_edge':262144}}})
ids={c:processor.tokenizer.encode(c,add_special_tokens=False) for c in 'ABC'}
for m in messages:
 text=processor.apply_chat_template(m,tokenize=False,add_generation_prompt=True,enable_thinking=False)
 for c,token in ids.items():assert len(token)==1 and processor.tokenizer.encode(text+c,add_special_tokens=False)==processor.tokenizer.encode(text,add_special_tokens=False)+token
masks=inputs['attention_mask'].tolist();record={'token_ids':ids,'padding_counts':[len(m)-sum(m) for m in masks],'response_positions':response_positions(masks),'image_grid_thw':inputs['image_grid_thw'].tolist(),'passed':True}
assert any(record['padding_counts'])
(HERE/'tokenizer_probe.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
