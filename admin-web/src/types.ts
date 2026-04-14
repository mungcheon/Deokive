export type AdminTab = 'dashboard' | 'users' | 'backups' | 'support' | 'catalog';

export type AdminSession = {
  accessToken: string;
  displayName: string;
  role: string;
};

export type AdminProfile = {
  admin_id: number;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
};

export type DashboardSummary = {
  total_users: number;
  local_users: number;
  google_users: number;
  premium_users: number;
  backup_snapshot_count: number;
  active_backup_users: number;
  pending_support_count: number;
  catalog_item_count: number;
};

export type UserListItem = {
  user_id: number;
  login_id: string;
  nickname: string;
  tag: string;
  provider: string;
  google_email?: string | null;
  is_premium: boolean;
  created_at: string;
};

export type BackupListItem = {
  user_id: number;
  login_id: string;
  nickname: string;
  source: string;
  payload_bytes: number;
  uploaded_at: string;
};

export type SupportTicketListItem = {
  ticket_id: string;
  title: string;
  status: string;
  created_at: string;
};

export type CatalogItemListItem = {
  item_id: string;
  name: string;
  status: string;
  updated_at: string;
};
