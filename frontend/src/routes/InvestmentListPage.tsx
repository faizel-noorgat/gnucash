// frontend/src/routes/InvestmentListPage.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useInvestmentAccounts } from '@/hooks/use-investments';

export function InvestmentListPage() {
  const { data, isLoading, error } = useInvestmentAccounts();

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load investments.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Investments</h1>
        <Button asChild><Link to="/investments/new">New Investment</Link></Button>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} Investment Accounts</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Account</TableHead>
                <TableHead>Institution</TableHead>
                <TableHead>Account Number</TableHead>
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.results.map((inv) => (
                <TableRow key={inv.id}>
                  <TableCell className="font-medium">{inv.account_name}</TableCell>
                  <TableCell className="text-muted-foreground">{inv.institution || '—'}</TableCell>
                  <TableCell className="font-mono text-sm">{inv.account_number || '—'}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" asChild>
                      <Link to={`/investments/${inv.id}`}>View</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {data?.results.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                    No investment accounts. Create one to get started.
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
