import { render, screen } from '@testing-library/react';
import { ReconcileBadge } from '../components/ReconcileBadge';

test.each([
  ['n', 'Not Reconciled'],
  ['c', 'Cleared'],
  ['y', 'Reconciled'],
  ['f', 'Frozen'],
  ['v', 'Void'],
])('renders %s state as %s', (state, label) => {
  render(<ReconcileBadge state={state as 'n' | 'c' | 'y' | 'f' | 'v'} />);
  expect(screen.getByText(label)).toBeTruthy();
});
