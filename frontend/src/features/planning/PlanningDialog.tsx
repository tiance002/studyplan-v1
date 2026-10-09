import { useEffect, useRef, type ReactNode } from 'react';
export function PlanningDialog({ title, children, onClose }: {
    title: string;
    children: ReactNode;
    onClose: () => void;
}) {
    const ref = useRef<HTMLDialogElement>(null);
    useEffect(() => { const previous = document.activeElement as HTMLElement | null; const dialog = ref.current!; dialog.showModal(); return () => { dialog.close(); previous?.focus(); }; }, []);
    return <dialog ref={ref} className="planning-dialog" aria-label={title} onCancel={e => { e.preventDefault(); onClose(); }}><header><h2>{title}</h2><button type="button" aria-label="关闭弹窗" onClick={onClose}>×</button></header>{children}</dialog>;
}
