from backend.video import html5,media

def test_course_adapter_uses_matching_official_links_and_cdn(monkeypatch):
    page=b'<h1>CS50 Python</h1><h1>Functions</h1><a href="https://cdn.cs50.net/python/2023/x/shorts/functions/functions-360p.mp4">360p</a><a href="https://cdn.cs50.net/python/2023/x/shorts/functions/lang/en/functions.srt">Subtitles</a><a href="https://evil.example/fake.srt">fake</a>'
    monkeypatch.setattr(media,'fetch_bytes',lambda *a,**k:page)
    info,meta=html5.probe(html5.COURSE_PREFIX+'functions/')
    assert info['title']=='CS50 Python · Functions'
    assert info['subtitles']['en'][0]['url'].endswith('/functions/lang/en/functions.srt')
    assert info['html5_media_url'].startswith(html5.COURSE_CDN)
