export type Panels = {
  nav: boolean;
  plan: boolean;
  assistant: boolean;
  assistantWidth: number;
  restore?: { nav: boolean; plan: boolean };
};
export const initialPanels: Panels = {
  nav: true,
  plan: true,
  assistant: false,
  assistantWidth: 430,
};
export function panelWidths(width: number) {
  return {nav: Math.max(150, Math.min(190, width * .12)), plan: Math.max(250, Math.min(300, width * .22))};
}
export function togglePanel(
  state: Panels,
  panel: "nav" | "plan" | "assistant",
  width?: number,
): Panels {
  const s = { ...(width ? fitPanels(state, width) : state) };
  if (panel === "assistant") {
    if (s.assistant)
      return { ...s, assistant: false, ...s.restore, restore: undefined };
    s.restore = { nav: s.nav, plan: s.plan };
    s.assistant = true;
    if (s.nav && s.plan) s.nav = false;
  } else {
    s[panel] = !s[panel];
    if (s[panel] && s.nav && s.plan && s.assistant) {
      if (panel === "nav") s.plan = false;
      else s.assistant = false;
    }
    if (s.assistant) s.restore = { nav: s.nav, plan: s.plan };
    // Explicitly reopening a left panel takes priority over the previously
    // widened assistant. Shrink A to preserve the readable canvas.
    if (width && s[panel] && s.assistant) {
      s.assistantWidth = Math.max(
        280,
        Math.min(
          s.assistantWidth,
          width -
            (s.nav ? panelWidths(width).nav : 62) -
            (s.plan ? panelWidths(width).plan : 0) -
            600,
        ),
      );
    }
  }
  return s;
}
export function fitPanels(state: Panels, width: number): Panels {
  const s = { ...state };
  const remaining = () =>
    width -
    (s.nav ? panelWidths(width).nav : 62) -
    (s.plan ? panelWidths(width).plan : 0) -
    (s.assistant ? s.assistantWidth : 0);
  if (remaining() < 600) s.nav = false;
  if (remaining() < 600) s.plan = false;
  if (s.assistant)
    s.assistantWidth = Math.max(280, Math.min(s.assistantWidth, width - 662));
  if (width < 960) s.assistant = false;
  if (width < 760) s.plan = false;
  return s;
}
