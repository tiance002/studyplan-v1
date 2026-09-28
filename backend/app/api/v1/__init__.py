"""``/api/v1`` 路由包（B2-V §六）。

对外导出 :data:`~app.api.v1.routes.router`：五条业务端点。
"""

from app.api.v1.routes import router

__all__ = ["router"]
