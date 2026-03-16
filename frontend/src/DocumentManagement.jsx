import React, { useEffect, useState, useCallback } from "react";

const API_PREFIX = "/api/v1";
const MAX_UPLOAD_FILE_SIZE_BYTES = 10 * 1024 * 1024;

const authFetch = async (url, options = {}) => {
  const token = localStorage.getItem("access_token");
  const headers = { ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(url, { ...options, headers, credentials: "include" });
};

const SIDEBAR_ITEMS = [
  { key: "dashboard", label: "대시보드", href: "/auth-demo/app/dashboard" },
  { key: "documents", label: "처방전 업로드", href: null },
  { key: "drug-search", label: "약 검색", href: "/auth-demo/app/drug-search" },
  { key: "ai", label: "AI 가이드", href: "/auth-demo/app/ai" },
  { key: "notifications", label: "알림센터", href: "/auth-demo/app" },
  { key: "health", label: "건강 프로필", href: "/auth-demo/app/health-profile" },
];

function Sidebar() {
  return (
    <div className="doc-sidebar">
      <div className="doc-sidebar-brand">
        <strong>복약관리시스템</strong>
        <div className="text-muted small">보호자 모드</div>
      </div>
      <nav className="doc-sidebar-nav">
        {SIDEBAR_ITEMS.map((item) => (
          <a
            key={item.key}
            className={`doc-sidebar-link ${item.key === "documents" ? "active" : ""}`}
            href={item.href || "#"}
            onClick={item.href ? undefined : (e) => { e.preventDefault(); }}
          >
            {item.label}
          </a>
        ))}
      </nav>
      <div className="doc-sidebar-footer">
        <a className="doc-sidebar-link" href="/auth-demo/app/settings">Settings</a>
        <a className="doc-sidebar-link" href="#" onClick={(e) => {
          e.preventDefault();
          localStorage.removeItem("access_token");
          document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
          window.location.href = "/auth-demo/login";
        }}>Logout</a>
      </div>
    </div>
  );
}

function StatCard({ label, value, unit, color }) {
  return (
    <div className="doc-stat-card">
      <div className="text-muted small mb-1">{label}</div>
      <div className="doc-stat-value" style={{ color: color || "#2563eb" }}>{value}</div>
      {unit && <div className="text-muted small">{unit}</div>}
    </div>
  );
}

function DrugRow({ drug, index, onChange, onDelete }) {
  const timeSlots = ["아침", "점심", "저녁", "취침"];
  const freq = drug.frequency_text || "";

  return (
    <tr>
      <td>
        <input
          className={`form-control form-control-sm ${!drug.name ? "is-invalid" : ""}`}
          value={drug.name}
          onChange={(e) => onChange(index, "name", e.target.value)}
          placeholder="약명 입력"
        />
      </td>
      <td>
        <input
          className="form-control form-control-sm"
          value={drug.dosage_text || ""}
          onChange={(e) => onChange(index, "dosage_text", e.target.value)}
          placeholder=""
        />
      </td>
      <td>
        <input
          className="form-control form-control-sm"
          value={drug.frequency_text || ""}
          onChange={(e) => onChange(index, "frequency_text", e.target.value)}
          placeholder="예: 2회"
        />
      </td>
      <td>
        <div className="d-flex gap-1 align-items-center">
          {timeSlots.map((slot) => {
            const checked = freq.includes(slot);
            return (
              <div key={slot} className="text-center" style={{ minWidth: 28 }}>
                <div className="small text-muted" style={{ fontSize: "0.65rem", lineHeight: 1 }}>{slot}</div>
                <input
                  type="checkbox"
                  className="form-check-input"
                  checked={checked}
                  onChange={() => {}}
                  style={{ marginTop: 2 }}
                />
              </div>
            );
          })}
        </div>
      </td>
      <td>
        <input
          className="form-control form-control-sm"
          value={drug.duration_text || ""}
          onChange={(e) => onChange(index, "duration_text", e.target.value)}
          placeholder=""
        />
      </td>
      <td>
        <input
          className="form-control form-control-sm"
          value={drug.notes || ""}
          onChange={(e) => onChange(index, "notes", e.target.value)}
          placeholder="비고"
        />
      </td>
      <td>
        <button className="btn btn-outline-danger btn-sm" onClick={() => onDelete(index)}>🗑</button>
      </td>
    </tr>
  );
}

// 메인 뷰: 목록 or OCR 결과
function DocumentManagement() {
  const [view, setView] = useState("list"); // "list" | "ocr"
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [documentTitle, setDocumentTitle] = useState("");
  const [patientId, setPatientId] = useState("");
  const [uploadNotice, setUploadNotice] = useState(null);

  // OCR 결과 뷰 상태
  const [currentDoc, setCurrentDoc] = useState(null);
  const [ocrStatus, setOcrStatus] = useState(null);
  const [drugs, setDrugs] = useState([]);
  const [drugsLoading, setDrugsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);
  const [pollingId, setPollingId] = useState(null);
  const [showReviewOnly, setShowReviewOnly] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewMimeType, setPreviewMimeType] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API_PREFIX}/documents`);
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      setDocuments(data.items || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDocuments(); }, [loadDocuments]);

  useEffect(() => {
    if (view !== "list") return undefined;
    const hasPendingDocument = documents.some((doc) => {
      const status = doc.ocr_status || doc.status;
      return status === "queued" || status === "processing";
    });
    if (!hasPendingDocument) return undefined;

    const id = setInterval(() => {
      loadDocuments();
    }, 4000);
    return () => clearInterval(id);
  }, [documents, loadDocuments, view]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const validateUploadFile = useCallback((file) => {
    if (!file) return false;
    if (file.size > MAX_UPLOAD_FILE_SIZE_BYTES) {
      setError("파일 크기는 최대 10MB까지 업로드할 수 있습니다.");
      return false;
    }
    return true;
  }, []);

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      setSelectedFile(null);
      return;
    }
    if (!validateUploadFile(file)) {
      setSelectedFile(null);
      event.target.value = "";
      return;
    }
    setError(null);
    setSelectedFile(file);
  };

  const fetchDocumentBlob = useCallback(async (documentId) => {
    const response = await authFetch(`${API_PREFIX}/documents/${documentId}/file`);
    if (!response.ok) {
      throw new Error(`status ${response.status}`);
    }
    return response.blob();
  }, []);

  const loadDocumentPreview = useCallback(async (documentId) => {
    if (!documentId) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const blob = await fetchDocumentBlob(documentId);
      const objectUrl = URL.createObjectURL(blob);
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return objectUrl;
      });
      setPreviewMimeType(blob.type || "");
    } catch {
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
      setPreviewMimeType("");
      setPreviewError("미리보기를 불러오지 못했습니다.");
    } finally {
      setPreviewLoading(false);
    }
  }, [fetchDocumentBlob]);

  const handleOpenOriginalFile = useCallback(async (documentId) => {
    if (!documentId) return;
    try {
      const blob = await fetchDocumentBlob(documentId);
      const objectUrl = URL.createObjectURL(blob);
      const popup = window.open(objectUrl, "_blank", "noopener,noreferrer");
      if (!popup) {
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = currentDoc?.original_filename || `document-${documentId}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
      }
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (err) {
      setError(err.message || "원본 파일을 열지 못했습니다.");
    }
  }, [currentDoc, fetchDocumentBlob]);

  // 업로드: 목록 화면에서 처리 상태만 갱신
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;
    if (!validateUploadFile(selectedFile)) return;
    setUploading(true);
    setError(null);
    setUploadNotice(null);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (patientId) formData.append("patient_id", patientId);
      if (documentTitle.trim()) formData.append("title", documentTitle.trim());

      const res = await authFetch(`${API_PREFIX}/documents/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `status ${res.status}`);
      }
      await res.json();
      setSelectedFile(null);
      setDocumentTitle("");
      setPatientId("");
      if (document.getElementById("fileInput")) document.getElementById("fileInput").value = "";
      setUploadNotice("업로드가 완료되었습니다. 문서 인식은 백그라운드에서 진행됩니다.");
      loadDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  // OCR 뷰 열기
  const openOcrView = (doc) => {
    if (pollingId) clearInterval(pollingId);
    setCurrentDoc(doc);
    setView("ocr");
    setDrugs([]);
    setOcrStatus(null);
    setSaveMsg(null);
    setPreviewError(null);
    setPreviewMimeType("");
    setUploadNotice(null);
    loadDocumentPreview(doc.document_id);
    pollOcrStatus(doc.document_id);
  };

  // OCR 상태 폴링
  const pollOcrStatus = async (docId) => {
    if (pollingId) clearInterval(pollingId);
    const poll = async () => {
      try {
        const res = await authFetch(`${API_PREFIX}/documents/${docId}/status`);
        if (!res.ok) return;
        const data = await res.json();
        setOcrStatus(data);

        if (data.ocr_status === "success") {
          loadDrugs(docId);
          return true; // stop polling
        }
        if (data.ocr_status === "failed") return true;
      } catch { /* ignore */ }
      return false;
    };

    const done = await poll();
    if (done) return;

    const id = setInterval(async () => {
      const finished = await poll();
      if (finished) clearInterval(id);
    }, 2000);
    setPollingId(id);
  };

  useEffect(() => {
    return () => { if (pollingId) clearInterval(pollingId); };
  }, [pollingId]);

  // 약 목록 로드
  const loadDrugs = async (docId) => {
    setDrugsLoading(true);
    try {
      const res = await authFetch(`${API_PREFIX}/documents/${docId}/drugs?include_mfds=true`);
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      setDrugs((data.items || []).map((d) => ({
        extracted_med_id: d.extracted_med_id,
        name: d.name,
        dosage_text: d.dosage_text || "",
        frequency_text: d.frequency_text || "",
        duration_text: d.duration_text || "",
        confidence: d.confidence,
        notes: "",
        needs_review: d.validation?.needs_review || false,
      })));
    } catch { /* ignore */ }
    finally { setDrugsLoading(false); }
  };

  const handleDrugChange = (idx, field, value) => {
    setDrugs((prev) => prev.map((d, i) => i === idx ? { ...d, [field]: value } : d));
  };

  const handleDrugDelete = (idx) => {
    setDrugs((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleAddDrug = () => {
    setDrugs((prev) => [...prev, {
      extracted_med_id: null, name: "", dosage_text: "", frequency_text: "",
      duration_text: "", confidence: null, notes: "", needs_review: false,
    }]);
  };

  // 임시저장
  const handleTempSave = async () => {
    if (!currentDoc) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const payload = {
        items: drugs.map((d) => ({
          extracted_med_id: d.extracted_med_id || undefined,
          name: d.name,
          dosage_text: d.dosage_text || null,
          frequency_text: d.frequency_text || null,
          duration_text: d.duration_text || null,
          confidence: d.confidence,
        })),
        replace_all: true,
        confirm: false,
      };
      const res = await authFetch(`${API_PREFIX}/documents/${currentDoc.document_id}/drugs`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `status ${res.status}`);
      }
      setSaveMsg({ type: "success", text: "임시저장 완료" });
    } catch (err) {
      setSaveMsg({ type: "danger", text: err.message });
    } finally { setSaving(false); }
  };

  // 확정하기
  const handleConfirm = async () => {
    if (!currentDoc) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const payload = {
        items: drugs.map((d) => ({
          extracted_med_id: d.extracted_med_id || undefined,
          name: d.name,
          dosage_text: d.dosage_text || null,
          frequency_text: d.frequency_text || null,
          duration_text: d.duration_text || null,
          confidence: d.confidence,
        })),
        replace_all: true,
        confirm: true,
        force_confirm: true,
      };
      const res = await authFetch(`${API_PREFIX}/documents/${currentDoc.document_id}/drugs`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === "object" ? body.detail.message : (body.detail || `status ${res.status}`));
      }
      setSaveMsg({ type: "success", text: "확정 완료! 복약 가이드에 반영되었습니다." });
    } catch (err) {
      setSaveMsg({ type: "danger", text: err.message });
    } finally { setSaving(false); }
  };

  const handleReupload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !currentDoc) return;
    if (!validateUploadFile(file)) return;

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (currentDoc.patient_id) formData.append("patient_id", String(currentDoc.patient_id));
      if (currentDoc.original_filename) formData.append("title", currentDoc.original_filename);

      const res = await authFetch(`${API_PREFIX}/documents/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `status ${res.status}`);
      }

      setUploadNotice("문서를 다시 업로드했습니다. 문서 인식은 백그라운드에서 진행됩니다.");
      goBackToList();
    } catch (err) {
      setError(err.message || "재업로드에 실패했습니다.");
    }
  };

  const goBackToList = () => {
    setView("list");
    setCurrentDoc(null);
    setOcrStatus(null);
    setDrugs([]);
    if (pollingId) clearInterval(pollingId);
    setPollingId(null);
    setPreviewMimeType("");
    setPreviewError(null);
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    loadDocuments();
  };

  // 통계 계산
  const reviewCount = drugs.filter((d) => d.needs_review).length;
  const avgConfidence = drugs.length > 0
    ? Math.round(drugs.reduce((s, d) => s + (d.confidence || 0), 0) / drugs.length * 100)
    : 0;
  const freqCount = drugs.filter((d) => d.frequency_text).length;

  const displayDrugs = showReviewOnly ? drugs.filter((d) => d.needs_review) : drugs;

  // ─── OCR 결과 뷰 ───
  if (view === "ocr") {
    const isProcessing = !ocrStatus || ocrStatus.ocr_status === "queued" || ocrStatus.ocr_status === "processing";
    const isFailed = ocrStatus?.ocr_status === "failed";
    const isSuccess = ocrStatus?.ocr_status === "success";

    return (
      <div className="doc-layout">
        <Sidebar />
        <div className="doc-main">
          <div className="doc-header">
            <h4 className="fw-bold mb-0">처방전 업로드</h4>
            {isSuccess && (
              <span className="badge bg-success-subtle text-success px-3 py-2" style={{ fontSize: "0.85rem" }}>
                ✅ 문서 인식 완료
              </span>
            )}
          </div>

          {/* OCR 처리 중 */}
          {isProcessing && (
            <div className="text-center py-5">
              <div className="spinner-border text-primary mb-3" role="status" />
              <div className="text-muted">문서 인식 처리 중입니다... 잠시만 기다려주세요.</div>
            </div>
          )}

          {/* OCR 실패 */}
          {isFailed && (
            <div className="alert alert-danger">
              문서 인식에 실패했습니다. {ocrStatus.error_message || ""}
              <button className="btn btn-warning btn-sm ms-3" onClick={() => {
                authFetch(`${API_PREFIX}/documents/${currentDoc.document_id}/retry`, { method: "POST" })
                  .then(() => pollOcrStatus(currentDoc.document_id));
              }}>재시도</button>
            </div>
          )}

          {/* OCR 성공 */}
          {isSuccess && (
            <>
              <div className="mb-3">
                <h5 className="fw-bold">문서 인식 결과 확인</h5>
                <p className="text-muted mb-0">추출된 약 정보를 확인하고 필요 시 수정한 뒤 확정해주세요.</p>
              </div>

              {/* 상단 카드 영역 */}
              <div className="doc-top-cards">
                <div className="doc-info-card">
                  <div className="d-flex align-items-center gap-2 mb-3">
                    <span style={{ fontSize: "1.2rem" }}>📄</span>
                    <strong>문서 정보</strong>
                  </div>
                  <div className="doc-preview-box">
                    {previewLoading && (
                      <div className="text-center py-4 text-muted">
                        <div className="spinner-border spinner-border-sm text-primary mb-2" role="status" />
                        <div className="small">문서 미리보기를 불러오는 중입니다.</div>
                      </div>
                    )}
                    {!previewLoading && previewError && (
                      <div className="text-center py-4 text-muted">
                        <div style={{ fontSize: "1.5rem" }}>⚠️</div>
                        <div className="small">{previewError}</div>
                      </div>
                    )}
                    {!previewLoading && !previewError && previewUrl && previewMimeType.includes("pdf") && (
                      <iframe title="문서 미리보기" src={previewUrl} className="doc-preview-frame" />
                    )}
                    {!previewLoading && !previewError && previewUrl && previewMimeType.startsWith("image/") && (
                      <img src={previewUrl} alt="문서 미리보기" className="doc-preview-image" />
                    )}
                    {!previewLoading && !previewError && (!previewUrl || (!previewMimeType.includes("pdf") && !previewMimeType.startsWith("image/"))) && (
                      <div className="text-muted text-center py-4">
                        <div style={{ fontSize: "2rem" }}>📄</div>
                        <div className="small">원본 보기로 확인해주세요.</div>
                      </div>
                    )}
                  </div>
                  <div className="mt-3 small">
                    <div className="d-flex justify-content-between mb-1">
                      <span className="text-muted">파일명</span>
                      <span className="fw-semibold">{currentDoc.original_filename || "—"}</span>
                    </div>
                    <div className="d-flex justify-content-between mb-1">
                      <span className="text-muted">업로드 날짜</span>
                      <span className="fw-semibold">{currentDoc.created_at ? new Date(currentDoc.created_at).toLocaleString("ko-KR") : "—"}</span>
                    </div>
                    <div className="d-flex justify-content-between mb-1">
                      <span className="text-muted">업로드 주체</span>
                      <span className="fw-semibold">본인</span>
                    </div>
                    <div className="d-flex justify-content-between mb-1">
                      <span className="text-muted">대상 환자</span>
                      <span className="fw-semibold">환자 #{currentDoc.patient_id}</span>
                    </div>
                  </div>
                  <div className="d-flex gap-2 mt-3">
                    <button
                      className="btn btn-outline-primary btn-sm flex-fill"
                      onClick={() => handleOpenOriginalFile(currentDoc.document_id)}
                    >
                      👁 원본 보기
                    </button>
                    <button className="btn btn-outline-secondary btn-sm flex-fill" onClick={() => {
                      document.getElementById("reuploadInput")?.click();
                    }}>↑ 다시 업로드</button>
                    <input
                      type="file"
                      id="reuploadInput"
                      className="d-none"
                      accept="image/*,.pdf"
                      onChange={handleReupload}
                    />
                  </div>
                </div>

                <StatCard label="추출된 약 개수" value={drugs.length} unit="개" color="#2563eb" />
                <StatCard label="복용 일정 감지" value={freqCount} unit="개" color="#7c3aed" />
                <StatCard label="검토 필요 항목" value={reviewCount} unit="개" color="#dc2626" />
                <StatCard label="신뢰도" value={avgConfidence} unit="%" color="#2563eb" />
              </div>

              {/* 약 정보 테이블 */}
              <div className="doc-drugs-section">
                <div className="d-flex align-items-center justify-content-between mb-3">
                  <div className="d-flex align-items-center gap-2">
                    <h5 className="fw-bold mb-0">약 정보 목록</h5>
                    <button className="btn btn-primary btn-sm" onClick={handleAddDrug}>+ 약 추가</button>
                  </div>
                  <label className="form-check-label d-flex align-items-center gap-1 small">
                    <input type="checkbox" className="form-check-input" checked={showReviewOnly}
                      onChange={(e) => setShowReviewOnly(e.target.checked)} />
                    검토 필요 항목만 보기
                  </label>
                </div>

                <div className="small text-muted mb-2">
                  ⚠ 확정된 약 리스트가 이후 가이드 생성에 사용됩니다.
                </div>

                {drugsLoading ? (
                  <div className="text-center py-4 text-muted">약 정보 불러오는 중...</div>
                ) : (
                  <div className="table-responsive">
                    <table className="table table-sm align-middle doc-drug-table">
                      <thead>
                        <tr>
                          <th>약명 <span className="text-danger">*</span></th>
                          <th>용량/단위</th>
                          <th>1일 횟수</th>
                          <th>복용 시간</th>
                          <th>기간(일)</th>
                          <th>비고</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {displayDrugs.map((drug, idx) => {
                          const realIdx = showReviewOnly ? drugs.indexOf(drug) : idx;
                          return <DrugRow key={realIdx} drug={drug} index={realIdx} onChange={handleDrugChange} onDelete={handleDrugDelete} />;
                        })}
                        {displayDrugs.length === 0 && (
                          <tr><td colSpan={7} className="text-center text-muted py-3">추출된 약이 없습니다.</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* 하단 액션 */}
              {saveMsg && (
                <div className={`alert alert-${saveMsg.type} mt-3`}>{saveMsg.text}</div>
              )}
              <div className="doc-bottom-actions">
                <button className="btn btn-outline-secondary" onClick={handleTempSave} disabled={saving}>
                  📋 임시저장
                </button>
                <button className="btn btn-primary btn-lg px-5" onClick={handleConfirm} disabled={saving}>
                  확정하기
                </button>
                <button className="btn btn-outline-secondary" onClick={goBackToList}>
                  목록으로
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  // ─── 문서 목록 뷰 ───
  return (
    <div className="doc-layout">
      <Sidebar />
      <div className="doc-main">
        <div className="doc-header">
          <h4 className="fw-bold mb-0">처방전 업로드</h4>
        </div>

        {error && (
          <div className="alert alert-danger alert-dismissible">
            {error}
            <button type="button" className="btn-close" onClick={() => setError(null)} />
          </div>
        )}
        {uploadNotice && (
          <div className="alert alert-success alert-dismissible">
            {uploadNotice}
            <button type="button" className="btn-close" onClick={() => setUploadNotice(null)} />
          </div>
        )}

        {/* 업로드 폼 */}
        <div className="card border-0 shadow-sm mb-4">
          <div className="card-body">
            <h6 className="fw-bold mb-3">처방전 업로드</h6>
            <form onSubmit={handleUpload}>
              <div className="row g-3 align-items-end">
                <div className="col-md-4">
                  <label className="form-label small">파일 선택</label>
                  <input
                    type="file"
                    id="fileInput"
                    className="form-control"
                    onChange={handleFileChange}
                    accept="image/*,.pdf"
                    required
                  />
                  <div className="form-text">최대 10MB</div>
                </div>
                <div className="col-md-3">
                  <label className="form-label small">문서명 (선택)</label>
                  <input
                    type="text"
                    className="form-control"
                    value={documentTitle}
                    onChange={(e) => setDocumentTitle(e.target.value)}
                    placeholder="예: 3월 외래 처방전"
                    maxLength={255}
                  />
                </div>
                <div className="col-md-3">
                  <label className="form-label small">환자 ID (선택)</label>
                  <input type="number" className="form-control" value={patientId} onChange={(e) => setPatientId(e.target.value)} placeholder="본인이면 비워두세요" />
                </div>
                <div className="col-md-2">
                  <button type="submit" className="btn btn-primary w-100" disabled={uploading || !selectedFile}>
                    {uploading ? "업로드 중..." : "업로드"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

        {/* 문서 목록 */}
        <div className="card border-0 shadow-sm">
          <div className="card-body">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h6 className="fw-bold mb-0">처방전 목록</h6>
              <button className="btn btn-outline-secondary btn-sm" onClick={loadDocuments} disabled={loading}>
                {loading ? "로딩..." : "새로고침"}
              </button>
            </div>
            {documents.length === 0 ? (
              <div className="text-center py-5 text-muted">처방전이 없습니다.</div>
            ) : (
              <div className="table-responsive">
                <table className="table table-hover align-middle">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>파일명</th>
                      <th>환자 ID</th>
                      <th>상태</th>
                      <th>업로드 일시</th>
                      <th>작업</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((doc) => {
                      const docId = doc.document_id || doc.id;
                      const st = doc.ocr_status || doc.status;
                      const badgeCls = { queued: "bg-warning", processing: "bg-info", success: "bg-success", failed: "bg-danger" }[st] || "bg-secondary";
                      const stText = { queued: "대기 중", processing: "처리 중", success: "완료", failed: "실패" }[st] || st;
                      return (
                        <tr key={docId}>
                          <td>{docId}</td>
                          <td>{doc.original_filename || "—"}</td>
                          <td>{doc.patient_id}</td>
                          <td><span className={`badge ${badgeCls}`}>{stText}</span></td>
                          <td>{new Date(doc.created_at).toLocaleString("ko-KR")}</td>
                          <td>
                            <button className="btn btn-outline-primary btn-sm" onClick={() => openOcrView({
                              document_id: docId, patient_id: doc.patient_id,
                              original_filename: doc.original_filename, created_at: doc.created_at,
                              uploaded_by_user_id: doc.uploaded_by_user_id,
                            })}>
                              인식 결과
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DocumentManagement;
