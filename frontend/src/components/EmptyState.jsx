export default function EmptyState({ title, hint, action }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      {hint && <p>{hint}</p>}
      {action}
    </div>
  );
}
