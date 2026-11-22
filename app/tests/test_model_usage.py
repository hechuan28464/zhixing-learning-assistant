from backend.agent import usage_summary

def test_usage_totals_come_from_reported_calls():
    value=usage_summary([{'usage':{'total_tokens':15,'prompt_tokens':10,'completion_tokens':5}},
                         {'usage':{'total_tokens':9,'prompt_tokens':7,'completion_tokens':2}}])
    assert value=={'requests':2,'reported_requests':2,'total_tokens':24,'prompt_tokens':17,'completion_tokens':7}

def test_missing_provider_usage_is_unknown_instead_of_false_zero():
    value=usage_summary([{'usage':None},{'usage':{'total_tokens':15,'prompt_tokens':10,'completion_tokens':5}}])
    assert value['requests']==2 and value['reported_requests']==1 and value['total_tokens'] is None
