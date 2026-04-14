import { DataTable } from '../components/DataTable';
import type { SupportTicketListItem } from '../types';

type SupportPageProps = {
  tickets: SupportTicketListItem[];
};

export function SupportPage({ tickets }: SupportPageProps) {
  return (
    <DataTable
      title="Support"
      description="This panel is wired to the future support queue API."
      rows={tickets}
      emptyMessage="Support ticket APIs are not implemented yet."
      columns={[
        { key: 'ticket_id', header: 'Ticket ID', render: (row) => row.ticket_id },
        { key: 'title', header: 'Title', render: (row) => row.title },
        { key: 'status', header: 'Status', render: (row) => row.status },
        { key: 'created_at', header: 'Created', render: (row) => row.created_at },
      ]}
    />
  );
}
