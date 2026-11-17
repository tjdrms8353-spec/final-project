import React, { useMemo, useRef, useState } from 'react';
import { CheckCircle2, Download, Play, Plus, Trash2, Upload } from 'lucide-react';
import { usePlatform } from '../context/PlatformContext';
import { SAMPLE_RECEIPT_PRESETS } from '../data/mockDb';
import { ReceiptLineItem, ReceiptRecord } from '../types/platform';
import { ResilientImage } from './ResilientImage';

export const ReceiptOcrView: React.FC = () => {
  const { receipts, registerReceipt, runPlaywrightRpa } = usePlatform();

  const initialPreset = SAMPLE_RECEIPT_PRESETS[0];

  const [previewImageUrl, setPreviewImageUrl] = useState<string>(initialPreset.imageUrl);
  const [merchantName, setMerchantName] = useState<string>(initialPreset.merchantName);
  const [businessNo, setBusinessNo] = useState<string>(initialPreset.businessNo);
  const [transactionDate, setTransactionDate] = useState<string>(initialPreset.transactionDate);
  const [category, setCategory] = useState<ReceiptRecord['category']>(initialPreset.category);
  const [supplyAmount, setSupplyAmount] = useState<number>(initialPreset.supplyAmount);
  const [vatAmount, setVatAmount] = useState<number>(initialPreset.vatAmount);
  const [totalAmount, setTotalAmount] = useState<number>(initialPreset.totalAmount);
  const [paymentMethod, setPaymentMethod] = useState<string>(initialPreset.paymentMethod);
  const [approvalNo, setApprovalNo] = useState<string>(initialPreset.approvalNo);
  const [ocrConfidence, setOcrConfidence] = useState<number>(initialPreset.ocrConfidence);
  const [items, setItems] = useState<ReceiptLineItem[]>(initialPreset.items);
  const [isScanning, setIsScanning] = useState<boolean>(false);

  const [ledgerSearch, setLedgerSearch] = useState<string>('');
  const [ledgerCategory, setLedgerCategory] = useState<string>('전체');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadPreset = (presetId: string) => {
    const preset = SAMPLE_RECEIPT_PRESETS.find((p) => p.id === presetId);
    if (!preset) return;
    setIsScanning(true);
    setTimeout(() => {
      setPreviewImageUrl(preset.imageUrl);
      setMerchantName(preset.merchantName);
      setBusinessNo(preset.businessNo);
      setTransactionDate(preset.transactionDate);
      setCategory(preset.category);
      setSupplyAmount(preset.supplyAmount);
      setVatAmount(preset.vatAmount);
      setTotalAmount(preset.totalAmount);
      setPaymentMethod(preset.paymentMethod);
      setApprovalNo(preset.approvalNo);
      setOcrConfidence(preset.ocrConfidence);
      setItems(preset.items);
      setIsScanning(false);
    }, 350);
  };

  const handleUploadReceipt = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsScanning(true);
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = typeof reader.result === 'string' ? reader.result : '';
      setTimeout(() => {
        if (file.type.startsWith('image/') && dataUrl) {
          setPreviewImageUrl(dataUrl);
        } else {
          setPreviewImageUrl('');
        }
        const cleanName = file.name.replace(/\.[^/.]+$/, '');
        setMerchantName(cleanName || '스캔 가맹점 (OCR)');
        setBusinessNo('314-81-50291');
        setTransactionDate('2026-11-16 16:20');
        setCategory('IT/사무용품');
        setSupplyAmount(110000);
        setVatAmount(11000);
        setTotalAmount(121000);
        setPaymentMethod('법인카드 (****-1234)');
        setApprovalNo(String(Math.floor(100000 + Math.random() * 899999)));
        setOcrConfidence(95.8);
        setItems([
          {
            id: `itm-${Date.now()}`,
            name: `${cleanName} 구매 항목`,
            quantity: 1,
            unitPrice: 110000,
            amount: 110000,
          },
        ]);
        setIsScanning(false);
      }, 450);
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const handleAddItemRow = () => {
    setItems((prev) => [
      ...prev,
      { id: `itm-${Date.now()}`, name: '신규 품목', quantity: 1, unitPrice: 10000, amount: 10000 },
    ]);
  };

  const handleUpdateItem = (id: string, field: keyof ReceiptLineItem, value: string | number) => {
    setItems((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        const next = { ...item, [field]: value };
        if (field === 'quantity' || field === 'unitPrice') {
          next.amount = Number(next.quantity) * Number(next.unitPrice);
        }
        return next;
      })
    );
  };

  const handleRemoveItem = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const handleSubmitReceipt = (e: React.FormEvent) => {
    e.preventDefault();
    const created = registerReceipt({
      merchantName,
      businessNo,
      transactionDate,
      category,
      supplyAmount: Number(supplyAmount),
      vatAmount: Number(vatAmount),
      totalAmount: Number(totalAmount),
      paymentMethod,
      approvalNo,
      ocrConfidence,
      imageUrl: previewImageUrl || undefined,
      items,
    });
    if (created) {
      // Increment approval number slightly for convenience if user tests consecutive entries
      setApprovalNo(String(Number(approvalNo || 887766) + 1));
    }
  };

  const filteredLedger = useMemo(() => {
    const q = ledgerSearch.trim().toLowerCase();
    return receipts.filter((r) => {
      const catMatch = ledgerCategory === '전체' || r.category === ledgerCategory;
      const queryMatch =
        !q ||
        r.merchantName.toLowerCase().includes(q) ||
        r.id.toLowerCase().includes(q) ||
        r.approvalNo.includes(q);
      return catMatch && queryMatch;
    });
  }, [receipts, ledgerSearch, ledgerCategory]);

  const totalRegisteredExpense = useMemo(
    () => filteredLedger.reduce((acc, r) => acc + r.totalAmount, 0),
    [filteredLedger]
  );

  const exportCsv = () => {
    const header = '전표ID,가맹점,사업자번호,거래일시,분류,공급가액,부가세,합계금액,승인번호,RPA상태\n';
    const rows = filteredLedger
      .map(
        (r) =>
          `${r.id},"${r.merchantName}",${r.businessNo},${r.transactionDate},${r.category},${r.supplyAmount},${r.vatAmount},${r.totalAmount},${r.approvalNo},${r.rpaStatus}`
      )
      .join('\n');
    const blob = new Blob(['\uFEFF' + header + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'datapulse_expense_ledger.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-medium text-blue-700 mb-1">
          시나리오 D · 영수증 OCR 자동 인식 및 Playwright RPA 전표 입력
        </p>
        <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 text-balance">
          영수증 이미지 OCR 추출 · 검증 및 지출 내역 자동 등록
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Tesseract OCR이 영수증 이미지나 PDF에서 가맹점·금액·세액을 추출하고, 사용자 검토와 중복 검증을 거쳐 지출 원장 및 ERP에 자동 등록합니다.
        </p>
      </div>

      {/* Main OCR Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 5 Cols: Sample Selector + Upload + Original Receipt Image */}
        <section className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-base font-semibold text-slate-900">
              원본 영수증 스캔 뷰어
            </h2>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,.pdf"
              onChange={handleUploadReceipt}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors cursor-pointer whitespace-nowrap"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>영수증 업로드</span>
            </button>
          </div>

          <div className="space-y-1.5">
            <p className="text-xs font-medium text-slate-600">테스트용 실물 영수증 샘플 선택</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {SAMPLE_RECEIPT_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => loadPreset(preset.id)}
                  className={`text-left px-3 py-2 text-xs font-medium rounded-lg border transition-colors cursor-pointer ${
                    previewImageUrl === preset.imageUrl
                      ? 'bg-blue-50 border-blue-500 text-blue-800'
                      : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-100">
            <ResilientImage
              src={previewImageUrl}
              alt={merchantName || '업로드된 영수증'}
              fallbackTitle="PDF 또는 스캔 문서 (텍스트 추출 완료)"
              className="w-full max-h-[460px] object-contain mx-auto"
            />
            {isScanning && (
              <div className="absolute inset-0 bg-slate-900/60 flex items-center justify-center text-white text-xs font-medium">
                Tesseract OCR 텍스트 영역 분석 중...
              </div>
            )}
          </div>

          <div className="flex items-center justify-between text-xs text-slate-600 pt-1">
            <span>Tesseract OCR 평균 신뢰도</span>
            <span className="font-mono tabular-nums font-semibold text-emerald-700">
              {ocrConfidence}%
            </span>
          </div>
        </section>

        {/* Right 7 Cols: Editable OCR Extraction Review Form */}
        <section className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6">
          <form onSubmit={handleSubmitReceipt} className="space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-200 pb-4">
              <div>
                <h2 className="font-display text-base font-semibold text-slate-900">
                  OCR 추출 데이터 검토 및 수정
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  추출된 항목을 검토·수정한 뒤 TiDB 지출 원장에 등록하세요.
                </p>
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Pandera 전표 스키마 준비됨
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">가맹점명</label>
                <input
                  type="text"
                  required
                  value={merchantName}
                  onChange={(e) => setMerchantName(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">사업자등록번호</label>
                <input
                  type="text"
                  value={businessNo}
                  onChange={(e) => setBusinessNo(e.target.value)}
                  className="w-full px-3 py-2 text-sm font-mono tabular-nums border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">거래 일시</label>
                <input
                  type="text"
                  value={transactionDate}
                  onChange={(e) => setTransactionDate(e.target.value)}
                  className="w-full px-3 py-2 text-sm font-mono tabular-nums border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">계정 과목</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as ReceiptRecord['category'])}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-600"
                >
                  <option value="식비/접대비">식비/접대비</option>
                  <option value="IT/사무용품">IT/사무용품</option>
                  <option value="클라우드/구독">클라우드/구독</option>
                  <option value="교통/출장">교통/출장</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">결제 수단</label>
                <input
                  type="text"
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">카드 승인번호</label>
                <input
                  type="text"
                  value={approvalNo}
                  onChange={(e) => setApprovalNo(e.target.value)}
                  className="w-full px-3 py-2 text-sm font-mono tabular-nums border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
            </div>

            {/* Amount Breakdown */}
            <div className="grid grid-cols-3 gap-4 p-4 rounded-lg bg-slate-50 border border-slate-200">
              <div>
                <label className="block text-xs text-slate-600 mb-1">공급가액 (원)</label>
                <input
                  type="number"
                  value={supplyAmount}
                  onChange={(e) => {
                    const s = Number(e.target.value) || 0;
                    const v = Math.round(s * 0.1);
                    setSupplyAmount(s);
                    setVatAmount(v);
                    setTotalAmount(s + v);
                  }}
                  className="w-full px-2.5 py-1.5 text-sm font-mono tabular-nums bg-white border border-slate-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-600 mb-1">부가세 10% (원)</label>
                <input
                  type="number"
                  value={vatAmount}
                  onChange={(e) => {
                    const v = Number(e.target.value) || 0;
                    setVatAmount(v);
                    setTotalAmount(supplyAmount + v);
                  }}
                  className="w-full px-2.5 py-1.5 text-sm font-mono tabular-nums bg-white border border-slate-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-800 mb-1">합계 금액 (원)</label>
                <input
                  type="number"
                  value={totalAmount}
                  onChange={(e) => setTotalAmount(Number(e.target.value) || 0)}
                  className="w-full px-2.5 py-1.5 text-sm font-mono tabular-nums font-bold text-blue-700 bg-white border border-blue-300 rounded-md"
                />
              </div>
            </div>

            {/* 1:N Line Items Table */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-800">
                  세부 구매 품목 (1:N 매핑 항목)
                </h3>
                <button
                  type="button"
                  onClick={handleAddItemRow}
                  className="inline-flex items-center gap-1 text-xs font-medium text-blue-700 hover:underline cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>품목 추가</span>
                </button>
              </div>
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium">품목명</th>
                      <th className="text-right px-3 py-2 font-medium w-16">수량</th>
                      <th className="text-right px-3 py-2 font-medium w-28">단가</th>
                      <th className="text-right px-3 py-2 font-medium w-28">금액</th>
                      <th className="w-9" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {items.map((item) => (
                      <tr key={item.id}>
                        <td className="px-2 py-1.5">
                          <input
                            type="text"
                            value={item.name}
                            onChange={(e) => handleUpdateItem(item.id, 'name', e.target.value)}
                            className="w-full px-2 py-1 text-xs border border-transparent hover:border-slate-300 focus:border-blue-500 rounded focus:outline-none"
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <input
                            type="number"
                            min={1}
                            value={item.quantity}
                            onChange={(e) =>
                              handleUpdateItem(item.id, 'quantity', Number(e.target.value) || 1)
                            }
                            className="w-full text-right font-mono tabular-nums px-1.5 py-1 text-xs border border-transparent hover:border-slate-300 focus:border-blue-500 rounded focus:outline-none"
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <input
                            type="number"
                            value={item.unitPrice}
                            onChange={(e) =>
                              handleUpdateItem(item.id, 'unitPrice', Number(e.target.value) || 0)
                            }
                            className="w-full text-right font-mono tabular-nums px-1.5 py-1 text-xs border border-transparent hover:border-slate-300 focus:border-blue-500 rounded focus:outline-none"
                          />
                        </td>
                        <td className="px-3 py-1.5 text-right font-mono tabular-nums font-medium text-slate-800">
                          {item.amount.toLocaleString()}
                        </td>
                        <td className="px-1.5 py-1.5 text-center">
                          <button
                            type="button"
                            onClick={() => handleRemoveItem(item.id)}
                            aria-label="품목 삭제"
                            className="text-slate-400 hover:text-red-600 cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="submit"
                className="px-5 py-2.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors cursor-pointer"
              >
                검증 후 지출 내역 등록
              </button>
            </div>
          </form>
        </section>
      </div>

      {/* Expense Ledger Table */}
      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="font-display text-base font-semibold text-slate-900">
              등록된 지출 내역 원장 (TiDB Cloud)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5 font-mono tabular-nums">
              조회 {filteredLedger.length}건 · 총 합계 {totalRegisteredExpense.toLocaleString()}원
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              value={ledgerSearch}
              onChange={(e) => setLedgerSearch(e.target.value)}
              placeholder="가맹점, 전표ID, 승인번호 검색"
              className="px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
            <select
              aria-label="지출 분류 필터"
              value={ledgerCategory}
              onChange={(e) => setLedgerCategory(e.target.value)}
              className="px-3 py-1.5 text-xs border border-slate-300 rounded-lg bg-white"
            >
              <option value="전체">전체 분류</option>
              <option value="식비/접대비">식비/접대비</option>
              <option value="IT/사무용품">IT/사무용품</option>
              <option value="클라우드/구독">클라우드/구독</option>
              <option value="교통/출장">교통/출장</option>
            </select>
            <button
              type="button"
              onClick={exportCsv}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer whitespace-nowrap"
            >
              <Download className="w-3.5 h-3.5" />
              <span>CSV 내보내기</span>
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="text-left px-5 py-3 font-medium">전표 ID</th>
                <th className="text-left px-4 py-3 font-medium">가맹점 · 거래일시</th>
                <th className="text-left px-4 py-3 font-medium">분류</th>
                <th className="text-right px-4 py-3 font-medium">공급가 / 부가세</th>
                <th className="text-right px-4 py-3 font-medium">합계금액</th>
                <th className="text-left px-4 py-3 font-medium">RPA 동기화</th>
                <th className="text-right px-5 py-3 font-medium">업무 자동화</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filteredLedger.map((rec) => (
                <tr key={rec.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3 font-mono tabular-nums font-semibold text-slate-900">
                    {rec.id}
                  </td>
                  <td className="px-4 py-3">
                    <p className="font-semibold text-slate-900">{rec.merchantName}</p>
                    <p className="text-[11px] font-mono tabular-nums text-slate-500">
                      {rec.transactionDate} · 승인 {rec.approvalNo} · OCR {rec.ocrConfidence}%
                    </p>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{rec.category}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-600">
                    {rec.supplyAmount.toLocaleString()} / {rec.vatAmount.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums font-bold text-slate-900">
                    {rec.totalAmount.toLocaleString()}원
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`font-medium ${
                        rec.rpaStatus === 'RPA 입력완료' ? 'text-emerald-700' : 'text-amber-700'
                      }`}
                    >
                      {rec.rpaStatus}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right">
                    {rec.rpaStatus === 'RPA 입력완료' ? (
                      <span className="text-[11px] text-slate-400">ERP 기표 완료</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => runPlaywrightRpa(rec.id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-md transition-colors cursor-pointer whitespace-nowrap"
                      >
                        <Play className="w-3 h-3" />
                        <span>Playwright RPA 입력</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
