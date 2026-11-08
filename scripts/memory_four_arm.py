"""Frozen experiment switches: one controller, no duplicated arm implementations."""
ARMS={
    'off':('off',{}),
    'rule':('rule',{'agent_variant':'legacy'}),
    'A':('qwen',{'agent_variant':'A'}),
    'B':('qwen',{'agent_variant':'B'}),
    'C':('qwen',{'agent_variant':'C'}),
    'D':('qwen',{'agent_variant':'D'}),
    'B_visual':('qwen',{'agent_variant':'B','feedback_source':'visual'}),
    'C_rule':('qwen',{'agent_variant':'C','memory_decision':'rule'}),
    'D_recent':('qwen',{'agent_variant':'D','memory_retrieval':'recent'}),
    'D_random':('qwen',{'agent_variant':'D','memory_retrieval':'random'}),
    'disabled':('disabled',{'agent_variant':'D'}),
}


def arm_options(arm):
    mode,settings=ARMS[arm]
    result=[]
    for key,value in settings.items():result+=['inference_recovery.'+key,str(value)]
    return mode,result
