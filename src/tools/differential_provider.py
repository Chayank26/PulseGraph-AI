"""Local Ollama adapter. No external endpoint or implicit credential use."""
import json
import time
from urllib.parse import urlsplit
import requests
from src.core.differential import SYSTEM_PROMPT


class OllamaProvider:
    def __init__(self, endpoint, model, timeout=30):
        url = urlsplit(endpoint)
        if (url.scheme != 'http' or url.hostname not in ('127.0.0.1', '::1') or
            url.username or url.password or url.query or url.fragment or url.path not in ('', '/')):
            raise ValueError('Use an explicit loopback HTTP endpoint without credentials or paths')
        if not model or model.endswith('-cloud') or ':cloud' in model:
            raise ValueError('An explicitly configured local model is required')
        self.endpoint, self.model, self.timeout = endpoint.rstrip('/'), model, timeout

    def generate(self, payload, schema):
        started = time.monotonic()
        with requests.Session() as session:
            session.trust_env = False
            response = session.post(self.endpoint + '/api/chat', json={
                'model': self.model, 'stream': False, 'format': schema,
                'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                             {'role': 'user', 'content': json.dumps(payload)}],
                'options': {'temperature': 0, 'num_predict': 2048}},
                timeout=(3, self.timeout), allow_redirects=False, stream=True)
            with response:
                if response.status_code != 200:
                    raise ValueError('Model service did not return success')
                body = bytearray()
                for chunk in response.iter_content(4096):
                    if time.monotonic() - started > self.timeout:
                        raise TimeoutError('Model response exceeded elapsed-time budget')
                    body.extend(chunk)
                    if len(body) > 131072:
                        raise ValueError('Provider response too large')
                result = json.loads(body)
                if result.get('done') is not True:
                    raise ValueError('Model response incomplete')
                return result['message']['content']


def configured_provider():
    from config.settings import settings
    if settings.diagnostic_backend == 'disabled':
        return None
    return OllamaProvider(settings.diagnostic_endpoint, settings.diagnostic_model, settings.diagnostic_timeout_seconds)
