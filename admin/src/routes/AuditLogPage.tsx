// admin/src/routes/AuditLogPage.tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import { useAdminAuditLog } from '@/hooks/useAdminAuditLog';
import type { AuditLogFilters } from '@/hooks/useAdminAuditLog';
import { format } from 'date-fns';
import { Search, Eye } from 'lucide-react';

export function AuditLogPage() {
  const [filters, setFilters] = useState<AuditLogFilters>({});
  const [selectedEntry, setSelectedEntry] = useState<import('@/types/admin').AdminAuditLog | null>(null);

  const { data, isLoading } = useAdminAuditLog(filters);

  const logs = data?.results ?? [];

  const handleSearch = (field: keyof AuditLogFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [field]: value || undefined }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Audit Log</h1>
        <p className="mt-1 text-muted-foreground">Cross-tenant audit event viewer. All entries are immutable.</p>
      </div>

      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Filter by model..."
            value={filters.model ?? ''}
            onChange={(e) => handleSearch('model', e.target.value)}
            className="pl-9"
          />
        </div>
        <Input
          placeholder="Filter by user email..."
          value={filters.user_email ?? ''}
          onChange={(e) => handleSearch('user_email', e.target.value)}
          className="min-w-[200px]"
        />
        <Input
          placeholder="Filter by action (CREATE, UPDATE...)"
          value={filters.action ?? ''}
          onChange={(e) => handleSearch('action', e.target.value)}
          className="min-w-[200px]"
        />
        <Input
          placeholder="Date from (YYYY-MM-DD)"
          value={filters.date_from ?? ''}
          onChange={(e) => handleSearch('date_from', e.target.value)}
          className="min-w-[180px]"
        />
        <Input
          placeholder="Date to (YYYY-MM-DD)"
          value={filters.date_to ?? ''}
          onChange={(e) => handleSearch('date_to', e.target.value)}
          className="min-w-[180px]"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{data?.count ?? 0} Audit Events</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-10 animate-pulse rounded bg-muted" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Tenant</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Object ID</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="text-sm">
                      {format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm')}
                    </TableCell>
                    <TableCell className="font-medium">{log.tenant_name}</TableCell>
                    <TableCell>{log.user_email ?? 'system'}</TableCell>
                    <TableCell><ActionBadge action={log.action} /></TableCell>
                    <TableCell>
                      <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{log.model}</code>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {log.object_id.slice(0, 8)}...
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedEntry(log)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {logs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No audit events found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!selectedEntry} onOpenChange={() => setSelectedEntry(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Audit Event Details</DialogTitle>
            <DialogDescription>
              {selectedEntry && (
                <>
                  {selectedEntry.action} on {selectedEntry.model}#{selectedEntry.object_id.slice(0, 8)}
                  {' '}by {selectedEntry.user_email ?? 'system'} at{' '}
                  {selectedEntry && format(new Date(selectedEntry.timestamp), 'yyyy-MM-dd HH:mm:ss')}
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          {selectedEntry && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Tenant:</span> {selectedEntry.tenant_name}
                </div>
                <div>
                  <span className="font-medium">IP Address:</span> {selectedEntry.ip_address ?? '—'}
                </div>
                <div>
                  <span className="font-medium">User Agent:</span>{' '}
                  <span className="text-muted-foreground">{selectedEntry.user_agent}</span>
                </div>
                <div>
                  <span className="font-medium">Timestamp:</span>{' '}
                  {format(new Date(selectedEntry.timestamp), 'yyyy-MM-dd HH:mm:ss')}
                </div>
              </div>
              {selectedEntry.old_values && (
                <div>
                  <span className="font-medium">Old Values:</span>
                  <pre className="mt-1 rounded bg-muted p-3 text-xs overflow-auto">
                    {JSON.stringify(selectedEntry.old_values, null, 2)}
                  </pre>
                </div>
              )}
              {selectedEntry.new_values && (
                <div>
                  <span className="font-medium">New Values:</span>
                  <pre className="mt-1 rounded bg-muted p-3 text-xs overflow-auto">
                    {JSON.stringify(selectedEntry.new_values, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ActionBadge({ action }: { action: string }) {
  const variantMap: Record<string, 'default' | 'destructive' | 'secondary' | 'warning'> = {
    CREATE: 'default',
    UPDATE: 'warning',
    DELETE: 'destructive',
    LOGIN: 'secondary',
    LOGOUT: 'secondary',
    EXPORT: 'secondary',
  };
  return <Badge variant={variantMap[action] ?? 'secondary'}>{action}</Badge>;
}
