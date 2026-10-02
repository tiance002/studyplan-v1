import type { Page } from "../api/types";
const links: { page: Page; label: string; icon: string }[] = [
  { page: "dashboard", label: "学习工作台", icon: "⌂" },
  { page: "planning", label: "学习计划", icon: "⊞" },
  { page: "path", label: "学习路径", icon: "↝" },
  { page: "workspace", label: "阶段学习", icon: "▤" },
  { page: "conversations", label: "我的会话", icon: "☷" },
  { page: "summary", label: "阶段总结", icon: "▧" },
  { page: "practice", label: "项目实践", icon: "⌘" },
];
export function GlobalNavigation({
  expanded,
  page,
  navigate,
  toggle,
  username,
  logout,
}: {
  expanded: boolean;
  page: Page;
  navigate: (p: Page) => void;
  toggle: () => void;
  username: string;
  logout: () => void;
}) {
  return (
    <nav
      className={`global-nav ${expanded ? "" : "mini"}`}
      aria-label="全局导航"
    >
      <div className="brand">
        <span className="brand-square">
          S<span>·</span>
        </span>
        {expanded && (
          <div>
            <strong>Study Plan</strong>
            <small>学习工作室</small>
          </div>
        )}
      </div>
      <div className="nav-heading">学习空间</div>
      {links.map((l) => (
        <button
          title={l.label}
          aria-label={l.label}
          aria-current={page === l.page ? "page" : undefined}
          className={`nav-link ${page === l.page ? "active" : ""}`}
          key={l.page}
          onClick={() => navigate(l.page)}
        >
          <span className="nav-icon">{l.icon}</span>
          {expanded && <span>{l.label}</span>}
        </button>
      ))}
      <div className="nav-spacer" />
      <button
        className="nav-link"
        title="模型设置"
        onClick={() => navigate("settings")}
      >
        <span className="nav-icon">⚙</span>
        {expanded && "模型设置"}
      </button>
      <div className="profile">
        <span className="avatar">{username[0]}</span>
        {expanded && <strong title={username}>{username}</strong>}
      </div>
      <button className="nav-link" title="退出登录" aria-label="退出登录" onClick={logout}>
        <span className="nav-icon">↪</span>
        {expanded && "退出登录"}
      </button>
      <button
        className="nav-link"
        title={expanded ? "折叠全局导航" : "展开全局导航"}
        aria-label={expanded ? "折叠全局导航" : "展开全局导航"}
        onClick={toggle}
      >
        <span className="nav-icon">{expanded ? "«" : "»"}</span>
        {expanded && "折叠导航"}
      </button>
    </nav>
  );
}
