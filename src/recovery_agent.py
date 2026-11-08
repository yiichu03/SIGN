"""Optional four-arm decisions within the shared RecoveryHarness state machine."""
import hashlib
import json
from collections import deque
from pathlib import Path
import numpy as np
from src.recovery_memory import EpisodeMemory, forward_observation, physical_commands, rule_memory_keep


def select_agent(value, feedback=False):
    labels=('continue','return') if feedback else ('left','right','keep')
    safe='return' if feedback else 'keep'
    try:
        p=np.asarray(value['probabilities'],dtype=float)
        mass=float(value['candidate_mass'])
        if value.get('valid',True) is False or p.shape!=(len(labels),) or not np.isfinite(p).all() or (p<0).any() or not np.isclose(p.sum(),1,atol=1e-6):
            raise ValueError('invalid probabilities')
        if not np.isfinite(mass) or mass<.1:return safe,'insufficient_candidate_token_mass'
        rank=np.argsort(p)
        if p[rank[-1]]-p[rank[-2]]<=1e-6:return safe,'tied_choice'
        return labels[int(rank[-1])],'model_argmax'
    except (KeyError,TypeError,ValueError):return safe,'invalid_model_evidence'


def image_item(role,path):
    path=Path(path)
    return dict(role=role,image=str(path),image_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def save_rgb(role,image,path):
    from PIL import Image
    Image.fromarray(np.asarray(image,dtype=np.uint8)).save(path)
    return image_item(role,path)


class AgentSupport:
    def _agent_reset(self,state):
        if self.agent and self.cfg.max_interventions>0 and self.arm in ('C','D'):
            state.memory=EpisodeMemory(self.cfg,'outcome' if self.arm=='C' else 'visual',state.key,
                lambda row:self._append('memory.jsonl',dict(episode=list(state.key),**row)))

    def _agent_observe(self,state,frame):
        state.issued_kind='sign'
        if state.last_action is not None and state.images:
            if state.memory is not None:
                state.memory.observe(state.images[-1],state.last_action,frame,state.step,state.last_kind)
            probe=state.probe
            if probe is not None and probe['start']+self.cfg.turn_steps < state.step <= probe['start']+self.cfg.turn_steps+4:
                probe['commands'].append(state.last_action.tolist())
        probe=state.probe
        if probe is not None and state.step==probe['start']+self.cfg.turn_steps:
            probe['before']=np.asarray(frame,dtype=np.uint8).copy()
        if probe is not None and state.step==probe['start']+self.cfg.turn_steps+4:
            if len(probe['commands'])!=4 or 'before' not in probe:raise RuntimeError('Closed-loop command/image boundary mismatch')
            probe['after']=np.asarray(frame,dtype=np.uint8).copy();probe['ready']=True

    def _agent_requests(self,state,row):
        files=row['view_files']
        images=[image_item(role,files[name]['path']) for role,name in
            [('GOAL','goal'),('CURRENT','forward'),('LEFT','left'),('RIGHT','right')]]
        context=dict(candidate_angles_command_deg={'LEFT':90,'RIGHT':-90},current_step=state.step)
        base=dict(id=row['id'],task='arbitration',images=images,context=json.dumps(context))
        retrieved=[]
        if state.memory is not None:
            from PIL import Image
            candidates={side:np.asarray(Image.open(files[side.lower()]['path']).convert('RGB')) for side in ('LEFT','RIGHT')}
            retrieved=state.memory.retrieve(candidates,row['step'],getattr(self.cfg,'memory_retrieval','verified'))
        row['memory_retrieval']=[dict(entry_id=x['entry']['id'],matched_candidate=x['matched_candidate'],match=x['match']) for x in retrieved]
        state.memory_hits+=sum(x['match']['valid'] for x in retrieved)
        request=dict(base,images=list(images))
        memory_context=[]
        if getattr(self.cfg,'memory_decision','vlm')=='vlm':
            for j,item in enumerate(retrieved):
                e=item['entry'];stem=self.output/'inputs'/(row['id']+'.memory'+str(j))
                request['images'].append(save_rgb('MEMORY_'+str(j)+'_BEFORE',e['before']['image'],str(stem)+'.before.png'))
                meta=dict(entry_id=e['id'],observed_steps=[e['start_step'],e['end_step']],
                    matched_candidate=item['matched_candidate'],appearance_match=item['match'],observations=e['observations'])
                if 'after' in e:
                    request['images'].append(save_rgb('MEMORY_'+str(j)+'_AFTER',e['after']['image'],str(stem)+'.after.png'))
                    meta.update(actual_normalized_commands=e['commands'],command_units_m_deg=physical_commands(e['commands']).tolist(),
                        visual_observation=e['observation'])
                memory_context.append(meta)
        if memory_context:
            context['memories']=memory_context;request['context']=json.dumps(context)
            state.memory_prompt_entries+=len(memory_context)
        row['_retrieved']=retrieved
        row['memory_prompt_count']=len(memory_context)
        row['request']=request
        if memory_context:
            row['shadow_request']=dict(base,id=base['id']+':without_memory')
        return request

    def _agent_score(self,requests):
        if not requests:return []
        try:
            if self.client is None:
                if self.client_factory is None:
                    from src.qwen_client import QwenClient
                    self.client_factory=QwenClient
                self.client=self.client_factory(self.cfg,self.output/'worker')
            request=self.request;self.request+=1
            response=self.client.score(request,requests)
        except (RuntimeError,OSError) as exc:
            # An ID/SHA mismatch is an integrity failure, never a valid fallback.
            if any(word in str(exc).lower() for word in ('mismatch','duplicate')):raise
            self.technical_errors+=1
            self._append('technical_errors.jsonl',dict(request_id=self.request,ids=[r['id'] for r in requests],error=str(exc)))
            return [dict(id=r['id'],valid=False,error=str(exc)) for r in requests]
        if [r['id'] for r in response['results']] != [r['id'] for r in requests]:raise RuntimeError('Recovery worker image ID/order mismatch')
        self.worker_seconds+=response['seconds']
        return response['results']

    def _agent_pending(self,pending,result):
        arbitration=[(i,r) for i,r in pending if r.get('task')!='feedback']
        requests=[]
        for i,row in arbitration:
            request=self._agent_requests(self.states[i],row)
            from PIL import Image
            # A uniform/blank camera provides no directional evidence. Do not force a choice.
            valid=all(float(np.asarray(Image.open(x['image'])).std())>=1. for x in request['images'][:4])
            row['visual_input_valid']=valid
            if valid:
                requests.append(request)
                if 'shadow_request' in row:requests.append(row['shadow_request'])
        feedback=[]
        for i,row in pending:
            if row.get('task')!='feedback':continue
            state=self.states[i];probe=state.probe
            obs=forward_observation(probe['before'],probe['after'],probe['commands'])
            if not obs['forward_only']:raise RuntimeError('Feedback includes turning rather than four aligned forward actions')
            row['observation']=obs;row['actual_commands']=probe['commands']
            row['request']=dict(id=row['id'],task='feedback',images=[
                save_rgb('BEFORE_FORWARD',probe['before'],self.output/'inputs'/(row['id']+'.before.png')),
                save_rgb('AFTER_FORWARD',probe['after'],self.output/'inputs'/(row['id']+'.after.png'))],
                context=json.dumps(dict(actual_commands=probe['commands'],physical_commands=physical_commands(probe['commands']).tolist(),observation=obs)))
            feedback.append((i,row))
            if getattr(self.cfg,'feedback_source','vlm')=='vlm':requests.append(row['request'])
        values={r['id']:r for r in self._agent_score(requests)}
        choices=[]
        for i,row in arbitration:
            state=self.states[i];value=values.get(row['id'],dict(valid=False))
            word,reason=select_agent(value)
            label={'left':'A','right':'B','keep':'C'}[word]
            shadow=values.get(row['id']+':without_memory')
            shadow_word=select_agent(shadow)[0] if shadow is not None else None
            memory_changed=bool(shadow is not None and reason=='model_argmax' and select_agent(shadow)[1]=='model_argmax' and shadow_word!=word)
            state.memory_changed+=memory_changed
            retrieved=row.pop('_retrieved',[])
            rule_memory=None
            if getattr(self.cfg,'memory_decision','vlm')=='rule':label,rule_memory=rule_memory_keep(label,retrieved)
            default='A' if row['attempt']%2 else 'B'
            source='rule_memory' if rule_memory and rule_memory['changed'] else 'vlm' if reason=='model_argmax' else 'safe_keep'
            detail=dict(source=source,reason=reason,raw=value,
                semantic_choice=word,default_rule=default,differs_from_rule=label!=default,
                shadow_without_memory=shadow,shadow_choice=shadow_word,memory_changed_decision=memory_changed,rule_memory=rule_memory)
            choices.append((label,detail))
        for i,row in feedback:
            state=self.states[i]
            if getattr(self.cfg,'feedback_source','vlm')=='visual':
                word='continue' if row['observation']['visual_mae']>=.01 else 'return';reason='fixed_visual_threshold';value=None
            else:value=values[row['id']];word,reason=select_agent(value,True)
            state.feedback_calls+=value is not None
            state.feedback_returns+=word=='return'
            if word=='continue':
                state.actions=deque([np.array([.6,0.],np.float32) for _ in range(4)])
                result[i]=state.actions.popleft();state.overrides+=1;state.recovery_overrides+=1;state.issued_kind='tail'
                if state.active_event is not None:state.active_event['end_step']=state.step+4
                state.cooldown_until=state.step+4+self.cfg.cooldown
            else:
                if state.active_event is not None:
                    self._append('outcomes.jsonl',dict(id=state.active_event['id'],episode=list(state.key),step=state.step,
                        phase='closed_loop_return',after_rgb_sha256=hashlib.sha256(np.ascontiguousarray(state.probe['after']).tobytes()).hexdigest(),
                        note='Handed back after four aligned forward commands, no task outcome label.'))
                    state.active_event=None
                state.cooldown_until=state.step+self.cfg.cooldown
            self._append('feedback.jsonl',dict(**row,choice=word,reason=reason,model=value,episode=list(state.key),step=state.step))
            state.probe=None
        return arbitration,choices
