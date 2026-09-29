import type { PointerEvent } from "react";
export function ResizableDivider({
  width,
  onResize,
}: {
  width: number;
  onResize: (width: number) => void;
}) {
  function start(e: PointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return;
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    e.currentTarget.dataset.start = String(e.clientX);
    e.currentTarget.dataset.width = String(width);
  }
  return (
    <div
      className="resize-divider"
      role="separator"
      aria-label="调整学习助手宽度"
      aria-orientation="vertical"
      aria-valuenow={Math.round(width)}
      aria-valuemin={280}
      aria-valuemax={800}
      tabIndex={0}
      onPointerDown={start}
      onPointerMove={(e) => {
        if (e.currentTarget.hasPointerCapture(e.pointerId) && e.buttons === 1)
          onResize(
            Number(e.currentTarget.dataset.width) +
              Number(e.currentTarget.dataset.start) -
              e.clientX,
          );
      }}
      onPointerUp={(e) => {
        if (e.currentTarget.hasPointerCapture(e.pointerId))
          e.currentTarget.releasePointerCapture(e.pointerId);
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          onResize(width + 20);
        }
        if (e.key === "ArrowRight") {
          e.preventDefault();
          onResize(width - 20);
        }
      }}
    />
  );
}
