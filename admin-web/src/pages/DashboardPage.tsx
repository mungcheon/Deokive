import { StatCard } from '../components/StatCard';
import type { DashboardSummary } from '../types';

type DashboardPageProps = {
  summary: DashboardSummary | null;
};

export function DashboardPage({ summary }: DashboardPageProps) {
  if (!summary) {
    return (
      <section className="panel">
        <h2>Dashboard</h2>
        <p>Loading summary data...</p>
      </section>
    );
  }

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <p className="eyebrow">Operations Overview</p>
        <h2>Core health metrics for the current admin surface</h2>
        <p>
          This is the first pass of the separated admin console. Add audit logs, support
          throughput, and catalog moderation in the next phase.
        </p>
      </section>

      <section className="stats-grid">
        <StatCard label="Total users" value={String(summary.total_users)} tone="sky" />
        <StatCard label="Local users" value={String(summary.local_users)} tone="mint" />
        <StatCard label="Google users" value={String(summary.google_users)} tone="amber" />
        <StatCard label="Premium users" value={String(summary.premium_users)} tone="rose" />
        <StatCard
          label="Backup snapshots"
          value={String(summary.backup_snapshot_count)}
          tone="sky"
        />
        <StatCard
          label="Backup-ready users"
          value={String(summary.active_backup_users)}
          tone="mint"
        />
        <StatCard
          label="Pending support"
          value={String(summary.pending_support_count)}
          tone="amber"
        />
        <StatCard
          label="Catalog items"
          value={String(summary.catalog_item_count)}
          tone="rose"
        />
      </section>
    </div>
  );
}
