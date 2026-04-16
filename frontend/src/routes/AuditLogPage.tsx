// frontend/src/routes/AuditLogPage.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { useAuditLog } from '@/hooks/use-audit';
import type { AuditAction } from '@/types/audit';

const actionColors: Record<AuditAction, 'default' | 'destructive' | 'secondary' | 'outline'> = {
  CREATE: 'default',
  UPDATE: 'secondary',
  DELETE: 'destructive',
  LOGIN: 'outline',
  LOGOUT: 'outline',
  EXPORT: 'secondary',
};

export function AuditLogPage() {
  const [action, setAction] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [userFilter, setUserFilter] = useState('');

  const { data, isLoading, error } = useAuditLog(
    action || dateFrom || dateTo || userFilter
      ? { action, date_from: dateFrom, date_to: dateTo, user: userFilter }
      : undefined,
  );

  const handleClearFilters = () => {
    setAction('');
    setDateFrom('');
    setDateTo('');
    setUserFilter('');
  };

  const hasFilters = action || dateFrom || dateTo || userFilter;

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-10 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load audit log.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Audit Log</h1>
        <Button variant="outline" asChild><Link to="/settings">Back to Settings</Link></Button>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">Filters</CardTitle></CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => { e.preventDefault(); }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            <div className="space-y-2">
              <Label htmlFor="filter-action">Action</Label>
              <Input
                id="filter-action"
                value={action}
                onChange={(e) => setAction(e.target.value)}
                placeholder="CREATE, UPDATE..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-date-from">Date from</Label>
              <Input
                id="filter-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-date-to">Date to</Label>
              <Input
                id="filter-date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-user">User</Label>
              <Input
                id="filter-user"
                value={userFilter}
                onChange={(e) => setUserFilter(e.target.value)}
                placeholder="user@example.com"
              />
            </div>
          </form>
          {hasFilters && (
            <div className="mt-4">
              <Button variant="ghost" size="sm" onClick={handleClearFilters}>Clear filters</Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} entries</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Object ID</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.results.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(log.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Badge variant={actionColors[log.action]}>{log.action}</Badge>
                  </TableCell>
                  <TableCell className="text-sm">{log.user_email ?? 'system'}</TableCell>
                  <TableCell className="text-sm font-mono">{log.model}</TableCell>
                  <TableCell className="text-sm font-mono text-muted-foreground">
                    {log.object_id.slice(0, 8)}...
                  </TableCell>
                </TableRow>
              ))}
              {data?.results.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                    No audit log entries found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
