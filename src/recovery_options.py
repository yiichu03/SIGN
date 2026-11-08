"""Pure, shared answer-option mapping; never touches policy random streams."""
import hashlib
import itertools
import math
ACTIONS=('LEFT','RIGHT','KEEP')
PERMUTATIONS=tuple(itertools.permutations(ACTIONS))


def balanced_option_map(index,seed=100):
    if type(index) is not int or index<0:raise ValueError('Invalid option mapping index')
    block,offset=divmod(index,6)
    order=sorted(range(6),key=lambda n:hashlib.sha256(('%s:%d:%d'%(seed,block,n)).encode()).digest())
    return dict(zip('ABC',PERMUTATIONS[order[offset]]))


def action_probabilities(probabilities,option_map):
    if set(option_map)!=set('ABC') or set(option_map.values())!=set(ACTIONS):raise ValueError('Invalid option/action bijection')
    p=list(probabilities)
    if len(p)!=3 or any(not math.isfinite(float(x)) or float(x)<0 for x in p) or abs(sum(p)-1)>1e-6:
        raise ValueError('Invalid option probabilities')
    inverse={v:k for k,v in option_map.items()}
    return [float(p['ABC'.index(inverse[action])]) for action in ACTIONS]
