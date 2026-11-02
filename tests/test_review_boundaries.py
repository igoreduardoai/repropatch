import pytest
from repropatch.cases import check_agent_path
from repropatch.security import BoundaryError
from repropatch.verify import redact

def test_absolute_paths_are_rejected_before_normalization():
    with pytest.raises(BoundaryError):check_agent_path(None,'/src/file.js')

def test_meta_token_shape_is_redacted():
    token='LLM_'+'1234567890_'+'x'*24
    assert token not in redact('sample '+token)
