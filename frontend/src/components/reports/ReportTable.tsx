// frontend/src/components/reports/ReportTable.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

interface Row { label: string; value: string; bold?: boolean }

export function ReportTable({ title, rows }: { title: string; rows: Row[] }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent>
        {rows.map((row, i) => (
          <div key={i}>
            {i > 0 && <Separator className="my-2" />}
            <div className="flex justify-between py-2">
              <span className={row.bold ? 'font-semibold' : ''}>{row.label}</span>
              <span className={row.bold ? 'font-semibold' : 'text-muted-foreground'}>{row.value}</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
