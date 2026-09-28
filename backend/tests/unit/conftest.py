"""unit 层测试包标记。

共享夹具（路径引导、postgres/langgraph 跳过、角色清理）统一在
``backend/tests/conftest.py`` 中定义，对 unit / contract / integration
三层同时生效，避免多处重复注册导致行为分叉。
"""

from __future__ import annotations
