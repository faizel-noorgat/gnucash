import { render, screen } from '@testing-library/react';
import type { RegisterEntry } from '@/types/register';
import { RegisterEntryRow } from '../components/RegisterEntryRow';

function makeEntry(overrides: Partial<RegisterEntry> = {}): RegisterEntry {
  return {
    id: 'test-id',
    post_date: '2025-03-15',
    description: 'Grocery Store',
    num: '1001',
    split_value: '-42.50',
    split_memo: 'Weekly shopping',
    other_accounts: ['Expenses:Groceries'],
    reconcile_state: 'n',
    created_at: '2025-03-15T10:00:00Z',
    ...overrides,
  };
}

test('renders date, description, and amount', () => {
  render(<RegisterEntryRow entry={makeEntry()} runningBalance="100.00" />);
  expect(screen.getByText('Mar 15, 2025')).toBeTruthy();
  expect(screen.getByText('Grocery Store')).toBeTruthy();
  expect(screen.getByText('$42.50')).toBeTruthy();
});

test('shows memo text when present', () => {
  render(<RegisterEntryRow entry={makeEntry()} runningBalance="0" />);
  expect(screen.getByText('Weekly shopping')).toBeTruthy();
});

test('shows other account names', () => {
  render(<RegisterEntryRow entry={makeEntry()} runningBalance="0" />);
  expect(screen.getByText('Expenses:Groceries')).toBeTruthy();
});

test('renders running balance', () => {
  render(<RegisterEntryRow entry={makeEntry()} runningBalance="1250.75" />);
  expect(screen.getByText('$1,250.75')).toBeTruthy();
});

test('renders ReconcileBadge with correct state', () => {
  render(<RegisterEntryRow entry={makeEntry({ reconcile_state: 'y' })} runningBalance="0" />);
  expect(screen.getByText('Reconciled')).toBeTruthy();
});

test('shows dash for empty num field', () => {
  render(<RegisterEntryRow entry={makeEntry({ num: '' })} runningBalance="0" />);
  expect(screen.getByText('\u2014')).toBeTruthy();
});
