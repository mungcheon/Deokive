import { DataTable } from '../components/DataTable';
import type { UserListItem } from '../types';

type UsersPageProps = {
  users: UserListItem[];
};

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export function UsersPage({ users }: UsersPageProps) {
  return (
    <DataTable
      title="Users"
      description="Inspect provider mix, premium status, and profile identities."
      rows={users}
      emptyMessage="No users were returned by the admin API."
      columns={[
        { key: 'login_id', header: 'Login ID', render: (row) => row.login_id },
        {
          key: 'profile',
          header: 'Profile',
          render: (row) => (
            <div>
              <strong>{row.nickname}</strong>
              <div className="cell-subtle">{row.tag}</div>
            </div>
          ),
        },
        { key: 'provider', header: 'Provider', render: (row) => row.provider },
        {
          key: 'google_email',
          header: 'Google Email',
          render: (row) => row.google_email || '-',
        },
        {
          key: 'premium',
          header: 'Premium',
          render: (row) => (row.is_premium ? 'Yes' : 'No'),
        },
        {
          key: 'created_at',
          header: 'Created',
          render: (row) => formatDate(row.created_at),
        },
      ]}
    />
  );
}
