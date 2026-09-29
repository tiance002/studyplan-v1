import { useEffect, useState } from "react";
import type { ReactNode, CSSProperties } from "react";
import type { DTO, Page } from "../api/types";
import { GlobalNavigation } from "./GlobalNavigation";
import { LearningPlanSidebar } from "./LearningPlanSidebar";
import { LearningAssistantPanel } from "./LearningAssistantPanel";
import { ResizableDivider } from "./ResizableDivider";
import { fitPanels, initialPanels, togglePanel } from "./panels";
import type { Panels } from "./panels";
const titles: Record<Page, string> = {
  dashboard: "学习工作台",
  planning: "学习计划",
  path: "学习路径",
  workspace: "阶段学习工作区",
  summary: "知识总结",
  practice: "项目实践",
  conversations: "我的会话",
  settings: "模型设置",
};
export function AppShell({
  page,
  navigate,
  session,
  workspace,
  stageId,
  nodeId,
  selectStage,
  selectNode,
  logout,
  children,
}: {
  page: Page;
  navigate: (p: Page) => void;
  session: DTO["SessionView"];
  workspace: DTO["LearningWorkspaceView"] | null;
  stageId: string;
  nodeId: string;
  selectStage: (id: string) => void;
  selectNode: (id: string) => void;
  logout: () => void;
  children: ReactNode;
}) {
  const [panels, setPanels] = useState<Panels>(() => {
    try {
      return {
        ...initialPanels,
        ...JSON.parse(localStorage.getItem("studyplan-panels") || "{}"),
      };
    } catch {
      return initialPanels;
    }
  });
  const [width, setWidth] = useState(window.innerWidth);
  useEffect(() => {
    const resize = () => setWidth(window.innerWidth);
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);
  useEffect(
    () => localStorage.setItem("studyplan-panels", JSON.stringify(panels)),
    [panels],
  );
  const visible = fitPanels(panels, width),
    toggle = (panel: "nav" | "plan" | "assistant") =>
      setPanels((s) => togglePanel(s, panel, width));
  const stage = workspace?.stages.find((s) => s.stage.stage_id === stageId);
  const node = stage?.nodes.find((n) => n.node_id === nodeId) || stage?.nodes[0];
  const currentGoal = node?.objectives?.join("；") || stage?.stage.objective || workspace?.plan.goal_snapshot || "";
  return (
    <div
      className="app-shell"
      style={
        {
          "--nav-width": visible.nav ? "11vw" : "62px",
          "--plan-width": visible.plan ? "17vw" : "0px",
          "--assistant-width": visible.assistant
            ? `${visible.assistantWidth}px`
            : "0px",
        } as CSSProperties
      }
    >
      <GlobalNavigation
        expanded={visible.nav}
        page={page}
        navigate={navigate}
        toggle={() => toggle("nav")}
        username={session.username || "学习者"}
        logout={logout}
      />
      {visible.plan && (
        <LearningPlanSidebar
          workspace={workspace}
          stageId={stageId}
          nodeId={nodeId}
          selectStage={selectStage}
          selectNode={selectNode}
          navigate={navigate}
        />
      )}
      <div className="main-workspace">
        <header className="topbar">
          <span className="breadcrumbs">
            学习空间 <span>/</span> {titles[page]}
          </span>
          <div className="toolbar">
            <button className="btn quiet" onClick={() => toggle("plan")}>
              {visible.plan ? "收起计划" : "展开计划"}
            </button>
            <button
              className="btn quiet"
              onClick={() =>
                setPanels((s) => ({
                  ...s,
                  nav: false,
                  plan: false,
                  assistant: false,
                }))
              }
            >
              专注阅读
            </button>
            <button className="btn" onClick={() => toggle("assistant")}>
              ✧ {visible.assistant ? "收起助手" : "学习助手"}
            </button>
          </div>
        </header>
        {page === "workspace" && workspace && (
          <div className="learning-pin">
            <span className="pill">当前目标</span>
            <span title={currentGoal}>
              {currentGoal}
            </span>
          </div>
        )}
        <main className="main-scroll" id="main-content">
          {children}
        </main>
      </div>
      {visible.assistant && (
        <>
          <ResizableDivider
            width={visible.assistantWidth}
            onResize={(w) =>
              setPanels((s) =>
                fitPanels(
                  { ...s, assistantWidth: Math.max(280, Math.min(800, w)) },
                  width,
                ),
              )
            }
          />
          <LearningAssistantPanel
            close={() => toggle("assistant")}
            stageTitle={stage?.stage.title || ""}
          />
        </>
      )}
    </div>
  );
}
