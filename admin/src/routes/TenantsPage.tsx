// admin/src/routes/TenantsPage.tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { useAdminTenants, useCreateTenant, useExtendTrial } from '@/hooks/useAdminTenants';
import type { AdminTenantCreate } from '@/types/admin';
import { format } from 'date-fns';
import { Plus, Search, Clock } from 'lucide-react';

export function TenantsPage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useAdminTenants({ search: search || undefined, status });
  const createTenant = useCreateTenant();
  const extendTrial = useExtendTrial();

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const formData = new FormData(form);
    const data: AdminTenantCreate = {
      name: formData.get('name') as string,
      slug: formData.get('slug') as string,
    };
    const trialEnds = formData.get('trial_ends_at') as string;
    if (trialEnds) data.trial_ends_at = trialEnds;
    createTenant.mutate(data, { onSuccess: () => setShowCreate(false) });
  };

  const tenants = data?.results ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tenants</h1>
          <p className="mt-1 text-muted-foreground">Manage all platform tenants.</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Tenant
        </Button>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search tenants..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={status ?? ''}
          onChange={(e) => setStatus(e.target.value || undefined)}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="trial">Trial</option>
          <option value="active">Active</option>
          <option value="expired">Expired</option>
        </select>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{data?.count ?? 0} Tenants</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Slug</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Members</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants.map((tenant) => (
                  <TableRow key={tenant.id}>
                    <TableCell className="font-medium">{tenant.name}</TableCell>
                    <TableCell>
                      <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{tenant.slug}</code>
                    </TableCell>
                    <TableCell>{tenant.owner_email ?? '—'}</TableCell>
                    <TableCell>{tenant.member_count}</TableCell>
                    <TableCell>
                      <TenantStatusBadge tenant={tenant} />
                    </TableCell>
                    <TableCell>
                      {format(new Date(tenant.created_at), 'yyyy-MM-dd')}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => extendTrial.mutate({ id: tenant.id, days: 14 })}
                        disabled={extendTrial.isPending}
                      >
                        <Clock className="mr-1 h-3 w-3" />
                        Extend Trial
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {tenants.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No tenants found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Tenant</DialogTitle>
            <DialogDescription>
              Create a new tenant workspace for an organization.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="tenant-name">Name</Label>
              <Input id="tenant-name" name="name" placeholder="Acme Corp" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tenant-slug">Slug</Label>
              <Input id="tenant-slug" name="slug" placeholder="acme-corp" required pattern="[a-z0-9-]+" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="trial-ends">Trial Ends At (optional)</Label>
              <Input id="trial-ends" name="trial_ends_at" type="datetime-local" />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createTenant.isPending}>
                {createTenant.isPending ? 'Creating...' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function TenantStatusBadge({ tenant }: { tenant: { trial_ends_at: string | null; stripe_customer_id: string } }) {
  if (tenant.stripe_customer_id) {
    return <Badge variant="success">Active</Badge>;
  }
  if (tenant.trial_ends_at && new Date(tenant.trial_ends_at) > new Date()) {
    return <Badge variant="warning">Trial</Badge>;
  }
  return <Badge variant="destructive">Expired</Badge>;
}

function TableSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="h-10 animate-pulse rounded bg-muted" />
      ))}
    </div>
  );
}
