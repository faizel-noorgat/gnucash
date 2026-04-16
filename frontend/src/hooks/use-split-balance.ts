// frontend/src/hooks/use-split-balance.ts
import { useMemo } from 'react';

export function useSplitBalance(values: (string | undefined)[]) {
  return useMemo(() => {
    const nums = values.filter((v): v is string => v !== undefined && v !== '').map(Number).filter((n) => !isNaN(n));
    const total = nums.reduce((s, v) => s + v, 0);
    return {
      total,
      isBalanced: Math.abs(total) < 0.005,
      isEmpty: nums.length === 0,
      difference: total.toFixed(2),
    };
  }, [values]);
}
