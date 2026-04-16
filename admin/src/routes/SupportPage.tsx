// admin/src/routes/SupportPage.tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export function SupportPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Support</h1>
        <p className="mt-1 text-muted-foreground">Support tickets and user assistance.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Coming Soon</CardTitle>
          <CardDescription>
            The support ticket system is planned for a future release.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-4 py-12">
            <Badge variant="secondary" className="text-lg px-4 py-2">MVP Placeholder</Badge>
            <p className="text-center text-muted-foreground max-w-md">
              Support ticket functionality including user-submitted tickets,
              admin response workflow, and SLA tracking will be added in Phase 8.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
