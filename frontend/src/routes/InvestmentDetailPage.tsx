// frontend/src/routes/InvestmentDetailPage.tsx
import { useParams, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useInvestmentAccount, useInvestmentLots } from '@/hooks/use-investments';

function formatDecimal(value: string, digits = 2): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return num.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function InvestmentDetailPage() {
  const { id } = useParams<{ id: string }>() as { id: string };
  const { data: account, isLoading: accountLoading } = useInvestmentAccount(id);
  const { data: lots, isLoading: lotsLoading } = useInvestmentLots(id);

  if (accountLoading || lotsLoading) {
    return <div className="space-y-4">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (!account) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Investment account not found.</p></div>;
  }

  const totalQuantity = lots?.results.reduce((sum, lot) => {
    if (lot.is_closed) return sum;
    return sum + parseFloat(lot.quantity);
  }, 0) ?? 0;

  const totalCostBasis = lots?.results.reduce((sum, lot) => {
    return sum + parseFloat(lot.cost_basis);
  }, 0) ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{account.account_name}</h1>
          {account.institution && <p className="text-sm text-muted-foreground">{account.institution}</p>}
        </div>
        <Button variant="outline" asChild><Link to="/investments">Back</Link></Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle className="text-sm font-medium text-muted-foreground">Holdings</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{formatDecimal(totalQuantity.toString(), 4)}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm font-medium text-muted-foreground">Total Cost Basis</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">${formatDecimal(totalCostBasis.toString())}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm font-medium text-muted-foreground">Lots</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{lots?.count ?? 0}</p></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Lots</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Security</TableHead>
                <TableHead className="text-right">Quantity</TableHead>
                <TableHead className="text-right">Purchase Price</TableHead>
                <TableHead className="text-right">Cost Basis</TableHead>
                <TableHead>Purchase Date</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {lots?.results.map((lot) => (
                <TableRow key={lot.id}>
                  <TableCell className="font-mono font-medium">{lot.security_id}</TableCell>
                  <TableCell className="text-right">{formatDecimal(lot.quantity, 4)}</TableCell>
                  <TableCell className="text-right">${formatDecimal(lot.purchase_price)}</TableCell>
                  <TableCell className="text-right font-medium">${formatDecimal(lot.cost_basis)}</TableCell>
                  <TableCell className="text-muted-foreground">{new Date(lot.purchase_date).toLocaleDateString()}</TableCell>
                  <TableCell>
                    {lot.is_closed ? (
                      <Badge variant="outline">Closed</Badge>
                    ) : (
                      <Badge variant="default">Open</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {lots?.results.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No lots recorded for this account.
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
