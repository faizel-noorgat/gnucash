// frontend/src/routes/RegisterPage.tsx
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, Link } from 'react-router-dom';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(12, 'Password must be at least 12 characters')
    .regex(/[A-Z]/, 'Must contain an uppercase letter')
    .regex(/[a-z]/, 'Must contain a lowercase letter')
    .regex(/[0-9]/, 'Must contain a digit'),
  tenant_name: z.string().min(1, 'Household name is required'),
  tenant_slug: z.string().min(1, 'URL slug is required').regex(/^[a-z0-9-]+$/, 'Lowercase letters, numbers, and hyphens only'),
});
type RegisterForm = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    setError(null);
    try {
      await api.post('/auth/register/', data);
      navigate('/login');
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.response?.data;
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
  };

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Create Account</CardTitle>
        <CardDescription>Set up your GnuCash Web household workspace.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="you@example.com" {...register('email')} />
            {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" {...register('password')} />
            {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="tenant_name">Household Name</Label>
            <Input id="tenant_name" placeholder="My Household" {...register('tenant_name')} />
            {errors.tenant_name && <p className="text-sm text-destructive">{errors.tenant_name.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="tenant_slug">URL Slug</Label>
            <Input id="tenant_slug" placeholder="my-household" {...register('tenant_slug')} />
            {errors.tenant_slug && <p className="text-sm text-destructive">{errors.tenant_slug.message}</p>}
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Creating account...' : 'Create Account'}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Already have an account? <Link to="/login" className="text-primary underline-offset-4 hover:underline">Sign in</Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
