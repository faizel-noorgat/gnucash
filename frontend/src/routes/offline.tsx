import { WifiOff } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function OfflinePage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <WifiOff className="mx-auto h-12 w-12 text-muted-foreground" />
          <CardTitle className="mt-4">You're Offline</CardTitle>
        </CardHeader>
        <CardContent className="text-center text-muted-foreground">
          <p>Check your internet connection and try again.</p>
        </CardContent>
      </Card>
    </div>
  );
}
