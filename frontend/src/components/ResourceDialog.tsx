import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';

export function ResourceDialog({ title, open, close, children }: {
  title: string;
  open: boolean;
  close: () => void;
  children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal();
    if (!open && dialog.current?.open) dialog.current.close();
  }, [open]);
  return (
    <dialog ref={dialog} className="resource-dialog" aria-labelledby={titleId}
      onCancel={event => { event.preventDefault(); close(); }}>
      <header className="resource-dialog-header">
        <h2 id={titleId}>{title}</h2>
        <button className="btn quiet" aria-label={`关闭${title}`} onClick={close}>关闭 ×</button>
      </header>
      <div className="resource-dialog-body">{children}</div>
    </dialog>
  );
}
