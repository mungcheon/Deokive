import type { PropsWithChildren } from 'react';

import type { AdminProfile, AdminTab } from '../types';

const tabs: Array<{ key: AdminTab; label: string }> = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'users', label: 'Users' },
  { key: 'backups', label: 'Backups' },
  { key: 'support', label: 'Support' },
  { key: 'catalog', label: 'Catalog' },
];

type ShellProps = PropsWithChildren<{
  activeTab: AdminTab;
  profile: AdminProfile;
  onSelectTab: (tab: AdminTab) => void;
  onSignOut: () => void;
}>;

export function Shell({
  activeTab,
  profile,
  onSelectTab,
  onSignOut,
  children,
}: ShellProps) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">DK</span>
          <div>
            <p className="eyebrow">Deokive</p>
            <h1>Admin Console</h1>
          </div>
        </div>

        <nav className="nav">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              className={tab.key === activeTab ? 'nav-button active' : 'nav-button'}
              onClick={() => onSelectTab(tab.key)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="admin-card">
            <p className="admin-name">{profile.display_name}</p>
            <p className="admin-meta">{profile.email}</p>
            <p className="admin-role">{profile.role}</p>
          </div>
          <button className="secondary-button" onClick={onSignOut} type="button">
            Sign out
          </button>
        </div>
      </aside>

      <main className="content">{children}</main>
    </div>
  );
}
