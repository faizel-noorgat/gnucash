// frontend/src/routes/SettingsPage.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';

interface TenantSummary {
  id: string;
  name: string;
  slug: string;
  trial_ends_at: string | null;
}

function useCurrentTenant(): TenantSummary | null {
  const tenantId = typeof window !== 'undefined' ? localStorage.getItem('gnucash_tenant_id') : null;
  if (!tenantId) return null;
  const raw = typeof window !== 'undefined' ? localStorage.getItem(`gnucash_tenant_${tenantId}`) : null;
  if (!raw) return null;
  try {
    return JSON.parse(raw) as TenantSummary;
  } catch {
    return null;
  }
}

export function SettingsPage() {
  const tenant = useCurrentTenant();
  const [name, setName] = useState(tenant?.name ?? '');

  const trialBadge = tenant?.trial_ends_at ? (
    new Date(tenant.trial_ends_at) > new Date() ? (
      <Badge variant="default">Trial active — ends {new Date(tenant.trial_ends_at).toLocaleDateString()}</Badge>
    ) : (
      <Badge variant="destructive">Trial expired</Badge>
    )
  ) : (
    <Badge variant="outline">No trial info</Badge>
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Tenant Information</CardTitle>
          <CardDescription>View and manage your workspace settings.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="tenant-name">Workspace name</Label>
            <Input
              id="tenant-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Workspace"
            />
          </div>
          <div className="space-y-2">
            <Label>Slug</Label>
            <p className="text-sm text-muted-foreground">{tenant?.slug ?? '—'}</p>
          </div>
          <div className="space-y-2">
            <Label>Trial status</Label>
            <div>{trialBadge}</div>
          </div>
          <Button type="button" disabled={name === tenant?.name}>Save</Button>
        </CardContent>
      </Card>

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Quick Links</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link to="/settings/users">Manage Users</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/settings/audit-log">Audit Log</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
