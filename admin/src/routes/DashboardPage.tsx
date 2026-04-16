// admin/src/routes/DashboardPage.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useDashboardStats } from '@/hooks/useAdminDashboard';
import { Building2, Users, FileText, TrendingUp } from 'lucide-react';

export function DashboardPage() {
  const { data: stats, isLoading, error } = useDashboardStats();

  if (isLoading) return <DashboardSkeleton />;
  if (error) return <div className="text-destructive">Failed to load dashboard stats.</div>;
  if (!stats) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Platform Dashboard</h1>
        <p className="mt-1 text-muted-foreground">Overview of your GnuCash Web platform.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Tenants"
          value={stats.total_tenants}
          icon={Building2}
          subtitle={`${stats.active_tenants_30d} active in last 30 days`}
        />
        <StatCard
          title="Total Users"
          value={stats.total_users}
          icon={Users}
          subtitle={`${stats.recent_signups} new this week`}
        />
        <StatCard
          title="Audit Events"
          value={stats.total_audit_events}
          icon={FileText}
          subtitle="Cross-tenant audit trail"
        />
        <StatCard
          title="Platform Health"
          value={<Badge variant="success">Operational</Badge>}
          icon={TrendingUp}
          subtitle="All systems normal"
        />
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  subtitle,
}: {
  title: string;
  value: number | React.ReactNode;
  icon: React.ComponentType<{ className?: string }>;
  subtitle: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
      </CardContent>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded bg-muted" />
      <div className="h-4 w-72 animate-pulse rounded bg-muted" />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    </div>
  );
}
