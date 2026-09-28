"""Authenticated personal metadata/save/clear; provider secrets stay server-only."""
from typing import Callable

from app.core.errors import ValidationAppError
from app.ports.model_settings import ModelSettingsRepository, ModelSettingsView


class ModelSettingsService:
    def __init__(self, repository: ModelSettingsRepository, endpoint_guard: Callable[[str],str], *, protocols=("openai",)):
        self.repository = repository
        self.endpoint_guard = endpoint_guard
        self.protocols = protocols

    def get(self, scope):
        return self.repository.get(scope.actor_id) or ModelSettingsView(0,"","","openai",False)

    def save(self, scope, *, expected_version, base_url, model_id, protocol, api_key):
        if protocol not in self.protocols:
            raise ValidationAppError("Unsupported model API protocol")
        model_id = model_id.strip()
        if not model_id or len(model_id)>200 or any(ord(c)<32 for c in model_id):
            raise ValidationAppError("Invalid model name")
        if api_key and (len(api_key)>4096 or api_key != api_key.strip() or any(ord(c)<33 for c in api_key)):
            raise ValidationAppError("Invalid API Key")
        base_url = self.endpoint_guard(base_url)
        return self.repository.save(scope.actor_id,expected_version=expected_version,base_url=base_url,
                                    model_id=model_id,protocol=protocol,api_key=api_key)

    def clear(self, scope, *, expected_version):
        return self.repository.clear(scope.actor_id,expected_version=expected_version)
