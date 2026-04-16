// admin/src/routes/BillingPage.tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ExternalLink } from 'lucide-react';

export function BillingPage() {
  const stripeDashboardUrl = import.meta.env.VITE_STRIPE_DASHBOARD_URL ?? 'https://dashboard.stripe.com';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
        <p className="mt-1 text-muted-foreground">Stripe billing dashboard and subscription management.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Stripe Dashboard</CardTitle>
          <CardDescription>
            Access the Stripe dashboard for subscription management, invoices, and revenue analytics.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4 py-8">
          <p className="text-center text-muted-foreground">
            For full billing analytics, subscription details, and revenue reports,
            open the Stripe dashboard.
          </p>
          <Button asChild>
            <a href={stripeDashboardUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="mr-2 h-4 w-4" />
              Open Stripe Dashboard
            </a>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Subscription Plans</CardTitle>
          <CardDescription>Configured pricing tiers for tenant subscriptions.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <PlanCard name="Free" price="$0" features={['1 user', 'Basic accounts', 'Transaction entry']} />
            <PlanCard name="Pro" price="$15/mo" features={['Up to 5 users', 'Budgets & reports', 'Receipt scanning', 'Recurring transactions']} highlighted />
            <PlanCard name="Enterprise" price="$49/mo" features={['Unlimited users', 'Investment tracking', 'Import/export', 'Priority support', 'Custom integrations']} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PlanCard({ name, price, features, highlighted = false }: {
  name: string;
  price: string;
  features: string[];
  highlighted?: boolean;
}) {
  return (
    <Card className={highlighted ? 'border-primary shadow-md' : ''}>
      <CardHeader>
        <CardTitle className="text-lg">{name}</CardTitle>
        <CardDescription className="text-2xl font-bold">{price}</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {features.map((feature) => (
            <li key={feature} className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="text-primary">&#10003;</span>
              {feature}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
