"""A requested long probe must not be silently cut back to two minutes."""
import io,json
import pytest
from backend.agent import provider

@pytest.mark.parametrize('requested,expected',[(240,240),(40,40),(900,300)])
def test_model_request_forwards_explicit_long_timeout_with_upper_bound(monkeypatch,requested,expected):
    observed={}
    class Response(io.BytesIO):
        def __enter__(self):return self
        def __exit__(self,*args):self.close()
    class Opener:
        def open(self,request,timeout):
            observed['timeout']=timeout
            return Response(json.dumps({'choices':[{'message':{'content':'OK'}}]}).encode())
    monkeypatch.setattr(provider.urllib.request,'build_opener',lambda *a:Opener())
    result,_=provider.request({'LLM_API_KEY':'test-only','LLM_BASE_URL':'https://example.invalid/v1'},'/chat/completions',{},timeout=requested)
    assert observed['timeout']==expected
    assert result['choices'][0]['message']['content']=='OK'
