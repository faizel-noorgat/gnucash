// frontend/src/components/reports/ReportDatePicker.tsx
import { format } from 'date-fns';
import { CalendarIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

interface ReportDatePickerProps {
  label: string;
  value: string;
  onChange: (date: string) => void;
}

export function ReportDatePicker({ label, value, onChange }: ReportDatePickerProps) {
  return (
    <div className="space-y-2">
      <span className="text-sm font-medium">{label}</span>
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="outline" className={cn('w-full justify-start text-left font-normal', !value && 'text-muted-foreground')}>
            <CalendarIcon className="mr-2 h-4 w-4" />
            {value ? format(new Date(value), 'PPP') : 'Pick a date'}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar mode="single" selected={value ? new Date(value) : undefined} onSelect={(d) => { if (d) onChange(format(d, 'yyyy-MM-dd')); }} initialFocus />
        </PopoverContent>
      </Popover>
    </div>
  );
}
