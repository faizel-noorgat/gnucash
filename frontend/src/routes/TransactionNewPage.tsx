import { useNavigate } from 'react-router-dom';
import { TransactionForm } from '@/features/transactions/components/transaction-form';

export function TransactionNewPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">New Transaction</h1>
      </div>
      <TransactionForm
        onSuccess={() => navigate('/transactions')}
        onCancel={() => navigate('/transactions')}
      />
    </div>
  );
}
