// admin/src/routes/AnalyticsPage.tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useDashboardStats } from '@/hooks/useAdminDashboard';
import { format } from 'date-fns';

export function AnalyticsPage() {
  const { data: stats, isLoading, error } = useDashboardStats();

  if (isLoading) return <AnalyticsSkeleton />;
  if (error) return <div className="text-destructive">Failed to load analytics data.</div>;
  if (!stats) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="mt-1 text-muted-foreground">Platform-wide growth and engagement metrics.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Signups</CardTitle>
            <CardDescription>New user registrations over the past 7 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">{stats.recent_signups}</div>
            <p className="mt-2 text-sm text-muted-foreground">
              {stats.recent_signups > 0
                ? `${stats.recent_signups} new user${stats.recent_signups !== 1 ? 's' : ''} this week`
                : 'No new signups this week'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active Tenants</CardTitle>
            <CardDescription>Tenants with activity in the last 30 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">{stats.active_tenants_30d}</div>
            <p className="mt-2 text-sm text-muted-foreground">
              Out of {stats.total_tenants} total tenants
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Total Audit Events</CardTitle>
            <CardDescription>Cross-tenant action trail</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">{stats.total_audit_events}</div>
            <p className="mt-2 text-sm text-muted-foreground">
              All CREATE, UPDATE, DELETE, LOGIN events across all tenants
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>User-to-Tenant Ratio</CardTitle>
            <CardDescription>Average users per tenant</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">
              {stats.total_tenants > 0
                ? (stats.total_users / stats.total_tenants).toFixed(1)
                : '0.0'}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {stats.total_users} users across {stats.total_tenants} tenants
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-40 animate-pulse rounded bg-muted" />
      <div className="h-4 w-72 animate-pulse rounded bg-muted" />
      <div className="grid gap-4 md:grid-cols-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-40 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    </div>
  );
}
