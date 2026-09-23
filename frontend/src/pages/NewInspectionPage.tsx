import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, X, ChevronRight, ChevronLeft, CheckCircle2 } from 'lucide-react';
import api from '@/lib/api';
import type { Product, InspectionDetail, ViewType } from '@/types';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

const VIEW_TYPES: ViewType[] = ['FRONT', 'BACK', 'LEFT', 'RIGHT', 'TOP', 'BOTTOM', 'OTHER'];

interface ImageUpload {
  file: File;
  preview: string;
  viewType: ViewType;
  id: string;
}

export default function NewInspectionPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Step 1 — Product
  const [products, setProducts] = useState<Product[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  // New product form
  const [createNew, setCreateNew] = useState(false);
  const [newProductCode, setNewProductCode] = useState('');
  const [newProductName, setNewProductName] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [newManufacturer, setNewManufacturer] = useState('');

  // Step 2 — Details
  const [notes, setNotes] = useState('');

  // Step 3 — Images
  const [images, setImages] = useState<ImageUpload[]>([]);

  // Created inspection (after step 2)
  const [createdInspection, setCreatedInspection] = useState<InspectionDetail | null>(null);

  useEffect(() => {
    api.get<Product[]>('/api/products/').then((r) => {
      setProducts(r.data);
      setLoadingProducts(false);
    }).catch(() => setLoadingProducts(false));
  }, []);

  // ── Step 1 submit ─────────────────────────────────────────
  const handleStep1 = async () => {
    setError('');
    let productId = selectedProductId;

    if (createNew) {
      if (!newProductCode.trim() || !newProductName.trim()) {
        setError('Product code and name are required.');
        return;
      }
      try {
        const res = await api.post<Product>('/api/products/', {
          product_code: newProductCode.trim(),
          product_name: newProductName.trim(),
          category: newCategory.trim() || null,
          manufacturer: newManufacturer.trim() || null,
        });
        productId = res.data.id;
        setProducts((p) => [...p, res.data]);
        setSelectedProductId(res.data.id);
        setCreateNew(false);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to create product.');
        return;
      }
    }

    if (!productId) {
      setError('Please select or create a product.');
      return;
    }
    setStep(2);
  };

  // ── Step 2 submit — creates the inspection ────────────────
  const handleStep2 = async () => {
    setError('');
    setSubmitting(true);
    try {
      const res = await api.post<InspectionDetail>('/api/inspections/', {
        product_id: selectedProductId,
        notes: notes.trim() || null,
      });
      setCreatedInspection(res.data);
      setStep(3);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create inspection.');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Image handling ────────────────────────────────────────
  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    const newImgs: ImageUpload[] = files.map((f) => ({
      file: f,
      preview: URL.createObjectURL(f),
      viewType: 'OTHER',
      id: Math.random().toString(36).slice(2),
    }));
    setImages((prev) => [...prev, ...newImgs]);
    e.target.value = '';
  };

  const removeImage = useCallback((id: string) => {
    setImages((prev) => {
      const img = prev.find((i) => i.id === id);
      if (img) URL.revokeObjectURL(img.preview);
      return prev.filter((i) => i.id !== id);
    });
  }, []);

  const updateViewType = (id: string, vt: ViewType) => {
    setImages((prev) => prev.map((i) => (i.id === id ? { ...i, viewType: vt } : i)));
  };

  // ── Step 3 submit — uploads images then triggers analysis ────────────
  const handleStep3 = async () => {
    setError('');
    if (!createdInspection) return;
    setSubmitting(true);
    try {
      for (const img of images) {
        const form = new FormData();
        form.append('file', img.file);
        form.append('view_type', img.viewType);
        await api.post(`/api/inspections/${createdInspection.id}/images`, form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }
      // Navigate to detail page; trigger analysis from there
      navigate(`/inspections/${createdInspection.id}?tab=analysis&autostart=1`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to upload images.');
    } finally {
      setSubmitting(false);
    }
  };

  const selectedProduct = products.find((p) => p.id === selectedProductId);

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold text-slate-900 mb-1">New Inspection</h1>
      <p className="text-sm text-slate-500 mb-6">Complete the steps below to begin a compliance inspection.</p>

      {/* Step indicator */}
      <div className="flex items-center gap-3 mb-8">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                step > s
                  ? 'bg-green-600 text-white'
                  : step === s
                  ? 'bg-blue-700 text-white'
                  : 'bg-slate-200 text-slate-500'
              }`}
            >
              {step > s ? <CheckCircle2 className="h-4 w-4" /> : s}
            </div>
            <span className={`text-xs font-medium ${step >= s ? 'text-slate-900' : 'text-slate-400'}`}>
              {s === 1 ? 'Select Product' : s === 2 ? 'Inspection Details' : 'Upload Images'}
            </span>
            {s < 3 && <ChevronRight className="h-4 w-4 text-slate-300" />}
          </div>
        ))}
      </div>

      {error && <ErrorAlert message={error} />}

      {/* ── STEP 1: Product ── */}
      {step === 1 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-800">Select Product</h2>

          {loadingProducts ? (
            <LoadingSpinner size="sm" label="Loading products…" />
          ) : (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Existing Product</label>
                <select
                  id="sel-product"
                  value={selectedProductId ?? ''}
                  onChange={(e) => {
                    setSelectedProductId(e.target.value ? Number(e.target.value) : null);
                    setCreateNew(false);
                  }}
                  disabled={createNew}
                  className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500 disabled:opacity-50"
                >
                  <option value="">— Select a product —</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.product_name} ({p.product_code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2 text-sm text-slate-500">
                <div className="flex-1 border-t border-slate-200" />
                <span>or</span>
                <div className="flex-1 border-t border-slate-200" />
              </div>

              <button
                type="button"
                id="btn-create-new-product"
                onClick={() => { setCreateNew(!createNew); setSelectedProductId(null); }}
                className="text-xs font-medium text-blue-600 hover:underline"
              >
                {createNew ? '← Back to existing products' : '+ Register a new product'}
              </button>

              {createNew && (
                <div className="space-y-3 mt-2">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">Product Code *</label>
                      <input id="inp-product-code" type="text" value={newProductCode} onChange={(e) => setNewProductCode(e.target.value)}
                        placeholder="e.g. PROD-001"
                        className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">Product Name *</label>
                      <input id="inp-product-name" type="text" value={newProductName} onChange={(e) => setNewProductName(e.target.value)}
                        placeholder="e.g. Tata Salt 1kg"
                        className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">Category</label>
                      <input id="inp-category" type="text" value={newCategory} onChange={(e) => setNewCategory(e.target.value)}
                        placeholder="e.g. Food & Beverages"
                        className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">Manufacturer</label>
                      <input id="inp-manufacturer" type="text" value={newManufacturer} onChange={(e) => setNewManufacturer(e.target.value)}
                        placeholder="e.g. Tata Consumer Products"
                        className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500" />
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          <div className="flex justify-end pt-2">
            <button
              id="btn-step1-next"
              onClick={handleStep1}
              className="flex items-center gap-2 rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
            >
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 2: Details ── */}
      {step === 2 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-800">Inspection Details</h2>

          {selectedProduct && (
            <div className="rounded-md bg-blue-50 border border-blue-100 px-3 py-2 text-sm">
              <span className="font-medium text-blue-800">{selectedProduct.product_name}</span>
              <span className="text-blue-600 ml-2 text-xs">({selectedProduct.product_code})</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Notes <span className="text-slate-400 font-normal">(optional)</span></label>
            <textarea
              id="inp-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Any relevant observations or context for this inspection…"
              className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500 resize-none"
            />
          </div>

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(1)} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
              <ChevronLeft className="h-4 w-4" /> Back
            </button>
            <button
              id="btn-step2-create"
              onClick={handleStep2}
              disabled={submitting}
              className="flex items-center gap-2 rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60 transition-colors"
            >
              {submitting ? 'Creating…' : <><span>Create Inspection</span> <ChevronRight className="h-4 w-4" /></>}
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 3: Images ── */}
      {step === 3 && createdInspection && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Upload Package Images</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Inspection <span className="font-mono font-medium">{createdInspection.inspection_number}</span> created.
              Upload all sides of the package.
            </p>
          </div>

          {/* Upload zone */}
          <label
            id="lbl-image-upload"
            htmlFor="inp-image-file"
            className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 p-8 cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
          >
            <Upload className="h-8 w-8 text-slate-400 mb-2" />
            <p className="text-sm font-medium text-slate-600">Click to upload images</p>
            <p className="text-xs text-slate-400 mt-1">JPEG, PNG, WebP, TIFF supported</p>
            <input
              id="inp-image-file"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/tiff"
              multiple
              onChange={onFileChange}
              className="hidden"
            />
          </label>

          {/* Image previews */}
          {images.length > 0 && (
            <div className="space-y-2">
              {images.map((img) => (
                <div key={img.id} className="flex items-center gap-3 rounded-md border border-slate-200 bg-slate-50 p-2">
                  <img src={img.preview} alt="" className="h-14 w-14 rounded object-cover flex-shrink-0 border border-slate-200" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-700 truncate">{img.file.name}</p>
                    <p className="text-xs text-slate-400">{(img.file.size / 1024).toFixed(1)} KB</p>
                  </div>
                  <select
                    value={img.viewType}
                    onChange={(e) => updateViewType(img.id, e.target.value as ViewType)}
                    className="rounded border border-slate-200 bg-white px-2 py-1 text-xs outline-none focus:border-blue-500"
                  >
                    {VIEW_TYPES.map((vt) => <option key={vt} value={vt}>{vt}</option>)}
                  </select>
                  <button onClick={() => removeImage(img.id)} className="rounded p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-between pt-2">
            <button
              onClick={() => navigate(`/inspections/${createdInspection.id}`)}
              className="text-sm text-slate-500 hover:text-slate-700"
            >
              Skip for now
            </button>
            <button
              id="btn-step3-upload"
              onClick={handleStep3}
              disabled={submitting || images.length === 0}
              className="flex items-center gap-2 rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60 transition-colors"
            >
              {submitting ? 'Uploading…' : `Upload ${images.length} Image${images.length !== 1 ? 's' : ''}`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
