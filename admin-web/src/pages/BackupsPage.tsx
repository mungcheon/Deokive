import { DataTable } from '../components/DataTable';
import type { BackupListItem } from '../types';

type BackupsPageProps = {
  backups: BackupListItem[];
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function BackupsPage({ backups }: BackupsPageProps) {
  return (
    <DataTable
      title="Backups"
      description="Track migration-ready server snapshots for local-account users."
      rows={backups}
      emptyMessage="No server snapshots are available yet."
      columns={[
        { key: 'login_id', header: 'Login ID', render: (row) => row.login_id },
        { key: 'nickname', header: 'Nickname', render: (row) => row.nickname },
        { key: 'source', header: 'Source', render: (row) => row.source },
        {
          key: 'payload',
          header: 'Payload Size',
          render: (row) => formatBytes(row.payload_bytes),
        },
        {
          key: 'uploaded_at',
          header: 'Uploaded At',
          render: (row) => new Date(row.uploaded_at).toLocaleString(),
        },
      ]}
    />
  );
}
