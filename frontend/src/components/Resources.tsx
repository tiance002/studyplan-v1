import type { DTO } from "../api/types";
export function Resources({
  items,
}: {
  items: DTO["StageResourceAssignmentView"][];
}) {
  if (!items.length) return <p className="empty">该阶段暂未分配学习资源。</p>;
  return (
    <div>
      {items.map((item) => (
        <div className="resource-group" key={item.assignment_id}>
          {(item.ordered_sections ?? []).map((section) => (
            <a
              className="resource-row"
              key={section.section_id}
              href={section.url}
              target="_blank"
              rel="noreferrer"
            >
              <span className="resource-icon">↗</span>
              <span>
                <strong>{section.title}</strong>
                <small>{item.creator || "公共资源"} · 目录核验通过</small>
              </span>
              <span className="pill">主线</span>
            </a>
          ))}
          {!(item.ordered_sections ?? []).length && (
            <div className="resource-row">
              <span className="resource-icon">⌕</span>
              <span>
                <strong>待查找学习资料</strong>
                <small>
                  {(item.fallback_search_terms ?? []).join("；") ||
                    "暂无可靠来源"}
                </small>
              </span>
              <span className="pill warm">未核验</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
