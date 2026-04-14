type StatCardProps = {
  label: string;
  value: string;
  tone?: 'sky' | 'mint' | 'amber' | 'rose';
};

export function StatCard({ label, value, tone = 'sky' }: StatCardProps) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <p className="stat-label">{label}</p>
      <strong className="stat-value">{value}</strong>
    </article>
  );
}
