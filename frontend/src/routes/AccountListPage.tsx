// frontend/src/routes/AccountListPage.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAccounts } from '@/hooks/use-accounts';

export function AccountListPage() {
  const { data, isLoading, error } = useAccounts();

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load accounts.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Accounts</h1>
        <Button asChild><Link to="/accounts/new">New Account</Link></Button>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} Accounts</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full">
            <thead><tr className="border-b"><th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Name</th><th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Type</th><th className="w-24" /></tr></thead>
            <tbody>
              {data?.results.map((account) => (
                <tr key={account.id} className="border-b last:border-0">
                  <td className="px-4 py-3 text-sm font-medium">{account.full_name}</td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{account.account_type}</td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="sm" asChild><Link to={`/accounts/${account.id}`}>View</Link></Button>
                  </td>
                </tr>
              ))}
              {data?.results.length === 0 && (
                <tr><td colSpan={3} className="px-4 py-8 text-center text-sm text-muted-foreground">No accounts yet.</td></tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
