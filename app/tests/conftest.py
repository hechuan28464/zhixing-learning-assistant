import pytest
@pytest.fixture(autouse=True)
def isolated_test_access(monkeypatch):
 # Existing business tests explicitly exercise their own model/execution fixtures.
 monkeypatch.setenv('STUDY_REQUIRE_LOGIN','0')
 monkeypatch.setenv('STUDY_AI_ENABLED','1')
