import type { DTO } from "../api/types";
const roleLabels: Record<string, string> = {
  primary: "主线", supplement: "补充", comparison: "可选对照",
  reference: "参考", case_study: "案例", practice: "实践",
};
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
          {!!item.warnings?.length && <p className="muted">{item.warnings.join("；")}</p>}
          {(item.verification_status === "unverified" ? [] : item.ordered_sections ?? []).map((section) => (
            <a
              className="resource-row"
              key={section.section_id}
              href={section.url}
              target="_blank"
              rel="noreferrer"
              title={`${item.title || section.title} · ${item.documentation_version || "旧版索引"} · ${item.language || ""}`}
            >
              <span className="resource-icon">↗</span>
              <span>
                <strong>{section.title}</strong>
                <small>{item.creator || "公共资源"} · {item.verification_status === "reviewed" ? "章节内容与索引已核对" : "旧版目录索引"}</small>
              </span>
              <span className="pill">{roleLabels[item.role] ?? "未知资料角色"}</span>
            </a>
          ))}
          {(!item.ordered_sections?.length || item.verification_status === "unverified") && (
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
