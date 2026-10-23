export function Placeholder({ title }: { title: string }) {
  return (
    <div className="page">
      <div className="page-head"><div><h1>{title}</h1></div></div>
      <div className="card empty"><p>This page is built in a later step.</p></div>
    </div>
  );
}
