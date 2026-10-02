"""Read-only stage completion from a saved stage summary and accepted practices."""


def derive_stage_completion(*, summary_completed, required_task_ids, available_task_ids, accepted_task_ids):
    required = set(required_task_ids)
    completed = required & set(available_task_ids) & set(accepted_task_ids)
    return {"status": "completed" if summary_completed and completed == required else "incomplete",
            "summary_completed": summary_completed, "completed_practice_tasks": len(completed),
            "total_practice_tasks": len(required)}
