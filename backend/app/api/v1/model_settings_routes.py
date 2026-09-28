"""Server-authenticated personal model settings; never returns a credential."""
from dataclasses import asdict

from app.api.v1.deps import get_auth_context, get_container
from app.application.container import AppContainer
from app.core.errors import AppError, ErrorCode
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, SecretStr

router = APIRouter(prefix="/api/v1")


class ModelSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    base_url: str = Field(min_length=1,max_length=2048)
    model_id: str = Field(min_length=1,max_length=200)
    protocol: str = "openai"
    api_key: SecretStr = Field(default=SecretStr(""),repr=False)


class ModelSettingsClear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)


class ModelSettingsResponse(BaseModel):
    version: int
    base_url: str
    model_id: str
    protocol: str
    has_api_key: bool
    source: str
    encryption_available: bool
    allowed_hosts: list[str]
    supported_protocols: list[str]


def _service(container):
    if container.model_settings_service is None:
        raise AppError(ErrorCode.DEPENDENCY_UNAVAILABLE,"Model settings storage is unavailable")
    return container.model_settings_service


def _response(view, container):
    settings = container.settings
    default = bool(settings.llm_api_key and settings.llm_model_id and settings.llm_base_url and not settings.use_fake_llm)
    source = "personal" if view.has_api_key else "deployment" if default else "unconfigured"
    data = asdict(view)
    if source == "deployment":
        data.update(base_url=settings.llm_base_url,model_id=settings.llm_model_id,protocol="openai")
    return ModelSettingsResponse(**data,source=source,encryption_available=bool(settings.model_settings_encryption_key),
                                 allowed_hosts=list(settings.llm_allowed_hosts),supported_protocols=list(_service(container).protocols))


@router.get("/model-settings",response_model=ModelSettingsResponse,operation_id="get_model_settings")
def get_model_settings(scope: AuthContext = Depends(get_auth_context),container: AppContainer = Depends(get_container)):
    return _response(_service(container).get(scope),container)


@router.put("/model-settings",response_model=ModelSettingsResponse,operation_id="save_model_settings")
def save_model_settings(payload: ModelSettingsRequest,scope: AuthContext = Depends(get_auth_context),container: AppContainer = Depends(get_container)):
    data = payload.model_dump(exclude={"api_key"})
    view = _service(container).save(scope,**data,api_key=payload.api_key.get_secret_value())
    return _response(view,container)


@router.delete("/model-settings",response_model=ModelSettingsResponse,operation_id="clear_model_settings")
def clear_model_settings(payload: ModelSettingsClear,scope: AuthContext = Depends(get_auth_context),container: AppContainer = Depends(get_container)):
    return _response(_service(container).clear(scope,expected_version=payload.expected_version),container)
