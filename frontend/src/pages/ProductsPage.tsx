import { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import api from '@/lib/api';
import type { Product } from '@/types';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { EmptyState } from '@/components/ui/EmptyState';

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [manufacturer, setManufacturer] = useState('');

  const load = async () => {
    try {
      const res = await api.get<Product[]>('/api/products/');
      setProducts(res.data);
    } catch { setError('Failed to load products.'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    if (!code.trim() || !name.trim()) { setFormError('Code and name are required.'); return; }
    setSubmitting(true);
    try {
      await api.post('/api/products/', {
        product_code: code.trim(), product_name: name.trim(),
        category: category.trim() || null, manufacturer: manufacturer.trim() || null,
      });
      setCode(''); setName(''); setCategory(''); setManufacturer('');
      setShowForm(false);
      load();
    } catch (err: any) {
      setFormError(err?.response?.data?.detail || 'Failed to create product.');
    } finally { setSubmitting(false); }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Products</h1>
          <p className="text-sm text-slate-500 mt-0.5">Registered packaged commodity products</p>
        </div>
        <button
          id="btn-add-product"
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Product
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl border border-slate-200 p-4 mb-4 space-y-3">
          <h2 className="text-sm font-semibold text-slate-800">Register New Product</h2>
          {formError && <ErrorAlert message={formError} />}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Product Code *</label>
              <input id="inp-code" type="text" value={code} onChange={(e) => setCode(e.target.value)} placeholder="PROD-001"
                className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Product Name *</label>
              <input id="inp-pname" type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Product name"
                className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Category</label>
              <input id="inp-cat" type="text" value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. Food & Beverages"
                className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Manufacturer</label>
              <input id="inp-mfr" type="text" value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} placeholder="Company name"
                className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="px-3 py-2 text-sm text-slate-500 hover:text-slate-700">Cancel</button>
            <button id="btn-submit-product" type="submit" disabled={submitting}
              className="rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60 transition-colors">
              {submitting ? 'Creating…' : 'Create Product'}
            </button>
          </div>
        </form>
      )}

      {loading && <LoadingSpinner className="py-20" label="Loading products…" />}
      {error && <ErrorAlert message={error} />}

      {!loading && !error && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          {products.length === 0 ? (
            <EmptyState title="No products yet" description="Add your first product to start inspecting." />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Manufacturer</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">{p.product_code}</td>
                    <td className="px-4 py-3 text-slate-700">{p.product_name}</td>
                    <td className="px-4 py-3 text-slate-500">{p.category ?? '—'}</td>
                    <td className="px-4 py-3 text-slate-500">{p.manufacturer ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
