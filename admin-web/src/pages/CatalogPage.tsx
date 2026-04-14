import { DataTable } from '../components/DataTable';
import type { CatalogItemListItem } from '../types';

type CatalogPageProps = {
  items: CatalogItemListItem[];
};

export function CatalogPage({ items }: CatalogPageProps) {
  return (
    <DataTable
      title="Catalog"
      description="The future product catalog manager will land here."
      rows={items}
      emptyMessage="Catalog APIs are not implemented yet."
      columns={[
        { key: 'item_id', header: 'Item ID', render: (row) => row.item_id },
        { key: 'name', header: 'Name', render: (row) => row.name },
        { key: 'status', header: 'Status', render: (row) => row.status },
        { key: 'updated_at', header: 'Updated', render: (row) => row.updated_at },
      ]}
    />
  );
}
