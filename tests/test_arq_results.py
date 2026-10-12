import pickle

from app.services.arq_results import _format_error, safe_unpickle


class BrokenProviderError(Exception):
    def __init__(self, *args, response, body):
        super().__init__(*args)
        self.response = response
        self.body = body


def test_safe_unpickle_reads_provider_errors_that_stdlib_pickle_cannot():
    payload = {
        "s": False,
        "r": BrokenProviderError("OpenRouter 429", response=object(), body={"error": "rate limit"}),
        "f": "process_job",
    }
    raw = pickle.dumps(payload)

    try:
        pickle.loads(raw)
        stdlib_ok = True
    except TypeError:
        stdlib_ok = False

    restored = safe_unpickle(raw)
    assert restored["s"] is False
    assert restored["r"] is not None
    if not stdlib_ok:
        assert "429" in str(restored["r"])


def test_format_error_explains_openai_unpickle_failure():
    message = _format_error(
        TypeError(
            "APIStatusError.__init__() missing 2 required keyword-only arguments: 'response' and 'body'"
        )
    )
    assert "Restart the ARQ worker" in message
    assert "structured extraction" in message
