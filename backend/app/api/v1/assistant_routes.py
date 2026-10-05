from typing import Annotated
from fastapi import APIRouter, Depends, Query
from app.api.v1.deps import get_auth_context, get_container
from app.api.v1.routes import ProjectId
from app.api.v1.assistant_schemas import AssistantCreateRequest, AssistantMessageRequest, AssistantSaveRequest, AssistantCancelRequest, AssistantConversationView, AssistantHistoryView
from app.application.container import AppContainer
from app.application.assistant import AssistantService
from app.core.errors import DependencyUnavailableError
from app.domain.workspace.models import AuthContext

router=APIRouter(prefix='/api/v1/assistant/conversations')

def get_service(container: AppContainer=Depends(get_container)) -> AssistantService:
    if container.assistant_service is None: raise DependencyUnavailableError('学习助手尚未装配')
    return container.assistant_service

@router.get('',response_model=AssistantHistoryView,operation_id='list_assistant_conversations')
def history(cursor: Annotated[str | None,Query(max_length=1024)]=None,limit: Annotated[int,Query(ge=1,le=100)]=20,project_id: str=ProjectId,scope: AuthContext=Depends(get_auth_context),service: AssistantService=Depends(get_service)):
    return service.list(scope,project_id,cursor,limit)

@router.post('',response_model=AssistantConversationView,operation_id='create_assistant_conversation')
def create(body: AssistantCreateRequest,project_id: str=ProjectId,scope: AuthContext=Depends(get_auth_context),service: AssistantService=Depends(get_service)):
    return service.create(scope,project_id,body.model_dump())

@router.get('/{conversation_id}',response_model=AssistantConversationView,operation_id='get_assistant_conversation')
def get(conversation_id: str,before_sequence: Annotated[int | None,Query(ge=1)]=None,project_id: str=ProjectId,scope: AuthContext=Depends(get_auth_context),service: AssistantService=Depends(get_service)):
    return service.get(scope,project_id,conversation_id,before_sequence)

@router.post('/{conversation_id}/messages',response_model=AssistantConversationView,status_code=202,operation_id='send_assistant_message')
def send(conversation_id: str,body: AssistantMessageRequest,project_id: str=ProjectId,scope: AuthContext=Depends(get_auth_context),service: AssistantService=Depends(get_service)):
    return service.send(scope,project_id,conversation_id,body.model_dump())

@router.post('/{conversation_id}/save',response_model=AssistantConversationView,operation_id='save_assistant_formal_artifact')
def save(conversation_id: str,body: AssistantSaveRequest,project_id: str=ProjectId,scope: AuthContext=Depends(get_auth_context),service: AssistantService=Depends(get_service)):
    return service.save(scope,project_id,conversation_id,body.model_dump())

@router.post('/{conversation_id}/cancel',response_model=AssistantConversationView,operation_id='cancel_assistant_reply')
def cancel(conversation_id: str,body: AssistantCancelRequest,project_id: str=ProjectId,scope: AuthContext=Depends(get_auth_context),service: AssistantService=Depends(get_service)):
    return service.cancel(scope,project_id,conversation_id,body.model_dump())
