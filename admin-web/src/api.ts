import type {
  AdminProfile,
  AdminSession,
  BackupListItem,
  CatalogItemListItem,
  DashboardSummary,
  SupportTicketListItem,
  UserListItem,
} from './types';

type LoginResponse = {
  access_token: string;
  token_type: string;
  role: string;
  display_name: string;
};

const envBaseUrl = (import.meta.env.VITE_DEOKIVE_ADMIN_API_BASE_URL as string | undefined)?.trim();

const API_BASE_URL =
  envBaseUrl && envBaseUrl.length > 0
    ? envBaseUrl.replace(/\/$/, '')
    : 'http://127.0.0.1:8000';

type RequestOptions = {
  method?: 'GET' | 'POST';
  token?: string;
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (!response.ok) {
    let detail = `Request failed with ${response.status}`;
    try {
      const json = (await response.json()) as { detail?: string | Array<{ msg?: string }> };
      if (typeof json.detail === 'string' && json.detail) {
        detail = json.detail;
      } else if (Array.isArray(json.detail) && json.detail.length > 0) {
        detail = json.detail
          .map((item) => item.msg || JSON.stringify(item))
          .join(', ');
      }
    } catch {
      // Ignore malformed JSON responses.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function loginAdmin(loginId: string, password: string): Promise<AdminSession> {
  return request<LoginResponse>('/admin-api/v1/auth/login', {
    method: 'POST',
    body: { login_id: loginId, password },
  }).then((response) => ({
    accessToken: response.access_token,
    displayName: response.display_name,
    role: response.role,
  }));
}

export function fetchAdminProfile(token: string): Promise<AdminProfile> {
  return request<AdminProfile>('/admin-api/v1/auth/me', { token });
}

export function fetchDashboardSummary(token: string): Promise<DashboardSummary> {
  return request<DashboardSummary>('/admin-api/v1/dashboard/summary', { token });
}

export function fetchUsers(token: string): Promise<UserListItem[]> {
  return request<UserListItem[]>('/admin-api/v1/users', { token });
}

export function fetchBackups(token: string): Promise<BackupListItem[]> {
  return request<BackupListItem[]>('/admin-api/v1/backups', { token });
}

export function fetchSupportTickets(token: string): Promise<SupportTicketListItem[]> {
  return request<SupportTicketListItem[]>('/admin-api/v1/support/tickets', { token });
}

export function fetchCatalogItems(token: string): Promise<CatalogItemListItem[]> {
  return request<CatalogItemListItem[]>('/admin-api/v1/catalog/items', { token });
}
