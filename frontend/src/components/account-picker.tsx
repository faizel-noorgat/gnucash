// frontend/src/components/account-picker.tsx
import * as React from 'react';
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useAccounts } from '@/hooks/use-accounts';

export interface AccountPickerProps {
  value?: string | null;
  onValueChange: (accountId: string) => void;
  placeholder?: string;
  disabled?: boolean;
  'aria-label'?: string;
  id?: string;
}

function getIndentLevel(fullName: string): number {
  return fullName.split(':').length - 1;
}

export function AccountPicker({ value, onValueChange, placeholder = 'Select account...', disabled, 'aria-label': ariaLabel, id }: AccountPickerProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const { data, isLoading } = useAccounts(search ? { search } : undefined);
  const accounts = data?.results ?? [];
  const selected = accounts.find((a) => a.id === value) ?? null;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" aria-expanded={open} aria-label={ariaLabel} id={id} disabled={disabled} className="w-full justify-between">
          {selected ? <span className="truncate">{selected.full_name}</span> : <span className="text-muted-foreground">{placeholder}</span>}
          {isLoading ? <Loader2 className="ml-2 h-4 w-4 animate-spin" /> : <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Search accounts..." onValueChange={setSearch} />
          <CommandList>
            {!isLoading && accounts.length === 0 && <CommandEmpty>No accounts found.</CommandEmpty>}
            <CommandGroup>
              {accounts.map((account) => {
                const indent = getIndentLevel(account.full_name);
                return (
                  <CommandItem key={account.id} value={account.full_name} onSelect={() => { onValueChange(account.id); setOpen(false); }}>
                    <Check className={cn('mr-2 h-4 w-4 shrink-0', value === account.id ? 'opacity-100' : 'opacity-0')} />
                    <span className="truncate" style={{ paddingLeft: `${indent * 16}px` }}>{account.full_name}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{account.account_type}</span>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
