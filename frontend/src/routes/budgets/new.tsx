// frontend/src/routes/budgets/new.tsx
import { useNavigate } from 'react-router-dom';
import { BudgetForm } from '@/features/budgets/components/BudgetForm';

export function BudgetNew() {
  const navigate = useNavigate();
  return <BudgetForm onSuccess={() => navigate('/budgets')} onCancel={() => navigate('/budgets')} />;
}
