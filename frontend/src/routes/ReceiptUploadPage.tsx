import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useCreateReceipt } from '@/hooks/use-receipts';

export function ReceiptUploadPage() {
  const navigate = useNavigate();
  const createReceipt = useCreateReceipt();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [vendor, setVendor] = useState('');
  const [receiptDate, setReceiptDate] = useState('');
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    setUploadError(null);
    if (selected && selected.type.startsWith('image/')) {
      const url = URL.createObjectURL(selected);
      setPreview(url);
    } else {
      setPreview(null);
    }
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadError(null);

    if (!file) {
      setUploadError('Please select a file to upload.');
      return;
    }

    // For now, file is uploaded client-side to a placeholder URL.
    // In production, replace with actual file upload to Cloudflare R2 via presigned URL.
    const fileUrl = `/uploads/${Date.now()}-${file.name}`;

    createReceipt.mutate(
      {
        file_url: fileUrl,
        vendor: vendor || undefined,
        receipt_date: receiptDate || undefined,
      },
      {
        onSuccess: (receipt) => navigate(`/receipts/${receipt.id}`),
        onError: () => setUploadError('Failed to upload receipt. Please try again.'),
      },
    );
  }, [file, vendor, receiptDate, createReceipt, navigate]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/receipts')}>Back</Button>
        <h1 className="text-2xl font-bold">Upload Receipt</h1>
      </div>
      <Card>
        <CardHeader><CardTitle>Receipt Details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="file">Receipt Image</Label>
              <Input
                id="file"
                type="file"
                accept="image/*"
                onChange={handleFileChange}
              />
              {preview && (
                <div className="mt-4 max-w-xs">
                  <img src={preview} alt="Receipt preview" className="rounded-md border" />
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="vendor">Vendor (optional)</Label>
                <Input
                  id="vendor"
                  type="text"
                  placeholder="e.g., Walmart"
                  value={vendor}
                  onChange={(e) => setVendor(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="receiptDate">Receipt Date (optional)</Label>
                <Input
                  id="receiptDate"
                  type="date"
                  value={receiptDate}
                  onChange={(e) => setReceiptDate(e.target.value)}
                />
              </div>
            </div>

            {uploadError && (
              <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3">
                <p className="text-sm text-destructive">{uploadError}</p>
              </div>
            )}

            <div className="flex gap-2">
              <Button type="submit" disabled={createReceipt.isPending || !file}>
                {createReceipt.isPending ? 'Uploading...' : 'Upload & Process'}
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate('/receipts')} disabled={createReceipt.isPending}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
