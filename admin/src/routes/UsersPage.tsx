// admin/src/routes/UsersPage.tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { useAdminUsers, useToggleUserActive, useSetUserStaff } from '@/hooks/useAdminUsers';
import { format } from 'date-fns';
import { Search, UserCheck, UserX } from 'lucide-react';

export function UsersPage() {
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);

  const { data, isLoading } = useAdminUsers({ search: search || undefined, is_active: activeFilter });
  const toggleActive = useToggleUserActive();
  const setStaff = useSetUserStaff();

  const users = data?.results ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Users</h1>
        <p className="mt-1 text-muted-foreground">Cross-tenant user directory.</p>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={activeFilter === undefined ? '' : activeFilter ? 'active' : 'inactive'}
          onChange={(e) => {
            const v = e.target.value;
            setActiveFilter(v === '' ? undefined : v === 'active');
          }}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">All Users</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{data?.count ?? 0} Users</CardTitle>
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
                  <TableHead>Email</TableHead>
                  <TableHead>Staff</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Tenants</TableHead>
                  <TableHead>Last Login</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.email}</TableCell>
                    <TableCell>
                      {user.is_staff ? (
                        <Badge variant="default">Staff</Badge>
                      ) : (
                        <Badge variant="secondary">User</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {user.is_active ? (
                        <Badge variant="success">Active</Badge>
                      ) : (
                        <Badge variant="destructive">Inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {user.tenant_count} tenant{user.tenant_count !== 1 ? 's' : ''}
                      </span>
                    </TableCell>
                    <TableCell>
                      {user.last_login_at
                        ? format(new Date(user.last_login_at), 'yyyy-MM-dd HH:mm')
                        : 'Never'}
                    </TableCell>
                    <TableCell>
                      {format(new Date(user.created_at), 'yyyy-MM-dd')}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleActive.mutate(user.id)}
                          disabled={toggleActive.isPending}
                        >
                          {user.is_active ? (
                            <><UserX className="mr-1 h-3 w-3" /> Deactivate</>
                          ) : (
                            <><UserCheck className="mr-1 h-3 w-3" /> Activate</>
                          )}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {users.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No users found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
