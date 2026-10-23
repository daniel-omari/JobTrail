import { useRef, useState, type ReactNode } from "react";
import "./Tooltip.css";

/** Shows `text` after hovering (or focusing) for about a second. */
export function Tooltip({ text, children, delay = 900 }: { text: string; children: ReactNode; delay?: number }) {
  const [open, setOpen] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const show = () => { timer.current = window.setTimeout(() => setOpen(true), delay); };
  const hide = () => { window.clearTimeout(timer.current); setOpen(false); };
  return (
    <span className="tip-wrap" onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}>
      {children}
      {open && <span role="tooltip" className="tip">{text}</span>}
    </span>
  );
}
