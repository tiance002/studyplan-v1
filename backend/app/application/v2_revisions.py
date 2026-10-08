"""Thin application entry for bounded local changes and Item1–7 replanning."""
from app.domain.planning.revisions import classify_change
from app.ports.v2_revisions import V2RevisionsPort


class V2RevisionService:
    def __init__(self, repository: V2RevisionsPort):
        self._repository = repository

    @staticmethod
    def classify_change(*, change_text):
        return classify_change(change_text=change_text)

    def context(self, **kwargs):
        return self._repository.context(**kwargs)

    def preview_local(self, **kwargs):
        return self._repository.preview_local(**kwargs)

    def get_preview(self, **kwargs):
        return self._repository.get_preview(**kwargs)

    def confirm(self, **kwargs):
        return self._repository.confirm(**kwargs)

    def cancel(self, **kwargs):
        return self._repository.cancel(**kwargs)

    def submit_semantic(self, **kwargs):
        return self._repository.submit_semantic(**kwargs)
