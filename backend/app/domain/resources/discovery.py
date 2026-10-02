"""Private chapter mapping rules; evidence schemas are validated at boundaries."""
from typing import Protocol, Sequence

from app.core.errors import ValidationAppError


class PrivateSelectionMapping(Protocol):
    @property
    def module_keys(self) -> Sequence[str]: ...

    @property
    def chapter_paths(self) -> Sequence[str]: ...


class IndexedChapter(Protocol):
    @property
    def path(self) -> str: ...

    @property
    def order(self) -> int: ...

    @property
    def status(self) -> str: ...


class ReadFile(Protocol):
    @property
    def path(self) -> str: ...


class PrivateMappingEvidence(Protocol):
    @property
    def selection_mapping(self) -> PrivateSelectionMapping | None: ...

    @property
    def chapters(self) -> Sequence[IndexedChapter]: ...

    @property
    def files(self) -> Sequence[ReadFile]: ...


def validate_private_mapping(evidence: PrivateMappingEvidence, allowed_module_keys: Sequence[str]):
    mapping = evidence.selection_mapping
    if mapping is None:
        return
    if (not mapping.module_keys or len(set(mapping.module_keys)) != len(mapping.module_keys)
            or any(key not in allowed_module_keys for key in mapping.module_keys)):
        raise ValidationAppError("模块键必须属于指定当前学习单元")
    chapters = sorted(evidence.chapters, key=lambda c: c.order)
    file_paths = {file.path for file in evidence.files}
    indexes = {c.path: index for index, c in enumerate(chapters) if c.status == "read" and c.path in file_paths}
    paths = mapping.chapter_paths
    if not paths or len(set(paths)) != len(paths) or any(path not in indexes for path in paths):
        raise ValidationAppError("只能映射已实际读取的章节")
    positions = [indexes[path] for path in paths]
    if positions != list(range(positions[0], positions[0] + len(positions))):
        raise ValidationAppError("映射章节必须是按作者顺序排列的连续区间")
