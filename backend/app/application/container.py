"""应用容器：API 层唯一可见的「已装配依赖」视图。

## 为什么要单独一层

依赖方向是 ``api -> application -> domain & ports <- infrastructure``。
API 层**不应**知道基础设施实现（PG 仓储、Provider 工厂）。它只需要一个
「已经装配好的服务集合」——本容器就是这个集合。

- **本模块**（application 层）：只声明容器的**形状**，字段类型全部是端口与
  应用服务，**不 import 任何基础设施**。
- **组合根**（``app.composition``）：负责把具体实现填进容器，是**唯一**
  允许 import infrastructure 来装配业务服务的地方。

这样 API 路由只依赖本模块，基础设施的具体类型不会渗进路由签名。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.application.model_settings import ModelSettingsService
from app.application.plan_service import PlanService
from app.core.config import Settings
from app.ports.browser_auth import BrowserAuthPort
from app.ports.sessions import SessionResolverPort
from app.ports.workspace import WorkspaceReaderPort

__all__ = ["AppContainer"]


@dataclass(frozen=True, slots=True)
class AppContainer:
    """已装配的依赖集合。

    ``plan_service`` 可以为 ``None``：开发骨架允许在没有 ``DATABASE_URL``
    时启动（此时业务端点返回 503，而不是让进程起不来）。
    """

    settings: Settings
    sessions: SessionResolverPort
    plan_service: PlanService | None = None
    model_settings_service: ModelSettingsService | None = None
    browser_auth: BrowserAuthPort | None = None
    workspace_reader: WorkspaceReaderPort | None = None
