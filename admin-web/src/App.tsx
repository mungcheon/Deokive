import { useEffect, useState } from 'react';

import {
  fetchAdminProfile,
  fetchBackups,
  fetchCatalogItems,
  fetchDashboardSummary,
  fetchSupportTickets,
  fetchUsers,
  loginAdmin,
} from './api';
import { Shell } from './components/Shell';
import { BackupsPage } from './pages/BackupsPage';
import { CatalogPage } from './pages/CatalogPage';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { SupportPage } from './pages/SupportPage';
import { UsersPage } from './pages/UsersPage';
import type {
  AdminProfile,
  AdminSession,
  AdminTab,
  BackupListItem,
  CatalogItemListItem,
  DashboardSummary,
  SupportTicketListItem,
  UserListItem,
} from './types';

const SESSION_KEY = 'deokive_admin_session';

function readStoredSession(): AdminSession | null {
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as AdminSession;
  } catch {
    return null;
  }
}

export function App() {
  const [session, setSession] = useState<AdminSession | null>(() => readStoredSession());
  const [profile, setProfile] = useState<AdminProfile | null>(null);
  const [activeTab, setActiveTab] = useState<AdminTab>('dashboard');
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [backups, setBackups] = useState<BackupListItem[]>([]);
  const [tickets, setTickets] = useState<SupportTicketListItem[]>([]);
  const [catalogItems, setCatalogItems] = useState<CatalogItemListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [bootLoading, setBootLoading] = useState(Boolean(session));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setProfile(null);
      setBootLoading(false);
      return;
    }

    const accessToken = session.accessToken;
    let cancelled = false;

    async function bootstrap() {
      setBootLoading(true);
      try {
        const [adminProfile, summary, userRows, backupRows, supportRows, catalogRows] =
          await Promise.all([
            fetchAdminProfile(accessToken),
            fetchDashboardSummary(accessToken),
            fetchUsers(accessToken),
            fetchBackups(accessToken),
            fetchSupportTickets(accessToken),
            fetchCatalogItems(accessToken),
          ]);

        if (cancelled) return;

        setProfile(adminProfile);
        setDashboard(summary);
        setUsers(userRows);
        setBackups(backupRows);
        setTickets(supportRows);
        setCatalogItems(catalogRows);
        setError(null);
      } catch (caught) {
        if (cancelled) return;
        const message =
          caught instanceof Error ? caught.message : 'Failed to initialize admin app.';
        setError(message);
        setSession(null);
        window.localStorage.removeItem(SESSION_KEY);
      } finally {
        if (!cancelled) {
          setBootLoading(false);
        }
      }
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [session]);

  async function handleLogin(loginId: string, password: string) {
    setLoading(true);
    setError(null);
    try {
      const nextSession = await loginAdmin(loginId, password);
      setSession(nextSession);
      window.localStorage.setItem(SESSION_KEY, JSON.stringify(nextSession));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Failed to sign in.');
    } finally {
      setLoading(false);
    }
  }

  function handleSignOut() {
    setSession(null);
    setProfile(null);
    setDashboard(null);
    setUsers([]);
    setBackups([]);
    setTickets([]);
    setCatalogItems([]);
    setActiveTab('dashboard');
    setError(null);
    window.localStorage.removeItem(SESSION_KEY);
  }

  if (!session) {
    return <LoginPage onSubmit={handleLogin} loading={loading} error={error} />;
  }

  if (bootLoading || !profile) {
    return (
      <div className="loading-screen">
        <div className="loading-card">
          <div className="spinner" />
          <p>Loading admin console...</p>
        </div>
      </div>
    );
  }

  let page;
  switch (activeTab) {
    case 'dashboard':
      page = <DashboardPage summary={dashboard} />;
      break;
    case 'users':
      page = <UsersPage users={users} />;
      break;
    case 'backups':
      page = <BackupsPage backups={backups} />;
      break;
    case 'support':
      page = <SupportPage tickets={tickets} />;
      break;
    case 'catalog':
      page = <CatalogPage items={catalogItems} />;
      break;
  }

  return (
    <Shell
      activeTab={activeTab}
      profile={profile}
      onSelectTab={setActiveTab}
      onSignOut={handleSignOut}
    >
      <header className="content-header">
        <div>
          <p className="eyebrow">Separated Admin Product</p>
          <h2>{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}</h2>
        </div>
        <div className="status-pill">
          <span>Role</span>
          <strong>{profile.role}</strong>
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}
      {page}
    </Shell>
  );
}
