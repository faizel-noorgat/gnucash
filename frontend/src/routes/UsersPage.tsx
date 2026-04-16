// frontend/src/routes/UsersPage.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  useTenantMemberhips,
  useCreateMembership,
  useUpdateMembership,
  useDeleteMembership,
} from '@/hooks/use-users';
import type { MembershipRole } from '@/types/tenant';

const roleVariant: Record<MembershipRole, 'default' | 'secondary' | 'outline'> = {
  OWNER: 'default',
  ADMIN: 'secondary',
  MEMBER: 'outline',
};

export function UsersPage() {
  const { data, isLoading, error } = useTenantMemberhips();
  const createMutation = useCreateMembership();
  const updateMutation = useUpdateMembership();
  const deleteMutation = useDeleteMembership();

  const [email, setEmail] = useState('');
  const [role, setRole] = useState<MembershipRole>('MEMBER');

  const handleAddMember = () => {
    if (!email.trim()) return;
    createMutation.mutate({ user_email: email.trim(), role });
    setEmail('');
    setRole('MEMBER');
  };

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load members.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Team Members</h1>
          <p className="text-sm text-muted-foreground">Manage who has access to this workspace.</p>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">Add Member</CardTitle></CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => { e.preventDefault(); handleAddMember(); }}
            className="flex gap-3 items-end"
          >
            <div className="flex-1 space-y-2">
              <Label htmlFor="member-email">Email</Label>
              <Input
                id="member-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@example.com"
                disabled={createMutation.isPending}
              />
            </div>
            <div className="w-40 space-y-2">
              <Label htmlFor="member-role">Role</Label>
              <Select value={role} onValueChange={(v: MembershipRole) => setRole(v)} disabled={createMutation.isPending}>
                <SelectTrigger id="member-role"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="OWNER">Owner</SelectItem>
                  <SelectItem value="ADMIN">Admin</SelectItem>
                  <SelectItem value="MEMBER">Member</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" disabled={createMutation.isPending || !email.trim()}>
              {createMutation.isPending ? 'Adding...' : 'Add'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} Members</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead className="w-48">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.results.map((m) => (
                <TableRow key={m.id}>
                  <TableCell className="font-medium">{m.user_email}</TableCell>
                  <TableCell>
                    <Select
                      value={m.role}
                      onValueChange={(v: MembershipRole) => updateMutation.mutate({ id: m.id, role: v })}
                      disabled={m.role === 'OWNER'}
                    >
                      <SelectTrigger className="w-32">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="OWNER">Owner</SelectItem>
                        <SelectItem value="ADMIN">Admin</SelectItem>
                        <SelectItem value="MEMBER">Member</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(m.joined_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {m.role !== 'OWNER' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => deleteMutation.mutate(m.id)}
                        disabled={deleteMutation.isPending}
                      >
                        Remove
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {data?.results.length === 0 && (
                <TableRow><TableCell colSpan={4} className="text-center py-8 text-muted-foreground">No members found.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Button variant="outline" asChild>
        <Link to="/settings">Back to Settings</Link>
      </Button>
    </div>
  );
}
