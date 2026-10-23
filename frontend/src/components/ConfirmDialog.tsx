import { useEffect, useRef, type ReactNode } from "react";
import "./ConfirmDialog.css";

export function ConfirmDialog({
  open, title, children, confirmLabel, danger = false, onConfirm, onCancel,
}: {
  open: boolean; title: string; children: ReactNode; confirmLabel: string; danger?: boolean;
  onConfirm: () => void; onCancel: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} className="dialog" onCancel={(e) => { e.preventDefault(); onCancel(); }}>
      <h2>{title}</h2>
      <div className="dialog-body">{children}</div>
      <div className="dialog-actions">
        <button className="btn" onClick={onCancel}>Cancel</button>
        <button className={`btn ${danger ? "btn-danger-solid" : "btn-primary"}`} onClick={onConfirm}>{confirmLabel}</button>
      </div>
    </dialog>
  );
}
