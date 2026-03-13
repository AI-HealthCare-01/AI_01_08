import React, { useEffect, useState } from "react";

const API_PREFIX = "/api/v1";

function DocumentManagement() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [patientId, setPatientId] = useState("");
  const [filters, setFilters] = useState({
    patient_id: "",
    status: "",
    page: 1,
    page_size: 10,
  });

  const authFetch = async (url, options = {}) => {
    const token = localStorage.getItem("access_token");
    const headers = { ...options.headers };
    if (token && !options.skipAuth) {
      headers.Authorization = `Bearer ${token}`;
    }
    return fetch(url, { ...options, headers, credentials: "include" });
  };

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.patient_id) params.set("patient_id", filters.patient_id);
      if (filters.status) params.set("status", filters.status);
      params.set("page", filters.page);
      params.set("page_size", filters.page_size);

      const res = await authFetch(`${API_PREFIX}/documents?${params.toString()}`);
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [filters]);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (patientId) formData.append("patient_id", patientId);

      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_PREFIX}/documents/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
        credentials: "include",
      });

      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail || `status ${res.status}`);
      }

      setSelectedFile(null);
      setPatientId("");
      document.getElementById("fileInput").value = "";
      await loadDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentId) => {
    if (!confirm("문서를 삭제하시겠습니까?")) return;

    try {
      const res = await authFetch(`${API_PREFIX}/documents/${documentId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      await loadDocuments();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRetry = async (documentId) => {
    try {
      const res = await authFetch(`${API_PREFIX}/documents/${documentId}/retry`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      alert("OCR 재시도 요청이 완료되었습니다.");
      await loadDocuments();
    } catch (err) {
      setError(err.message);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: "badge bg-warning",
      processing: "badge bg-info",
      completed: "badge bg-success",
      failed: "badge bg-danger",
    };
    return badges[status] || "badge bg-secondary";
  };

  const getStatusText = (status) => {
    const texts = {
      pending: "대기 중",
      processing: "처리 중",
      completed: "완료",
      failed: "실패",
    };
    return texts[status] || status;
  };

  return (
    <div className="container py-5">
      <div className="d-flex align-items-center mb-4">
        <a href="/auth-demo/app" style={{ cursor: 'pointer', textDecoration: 'none' }}>
          <img src="/mascot.png" alt="약승이" style={{ width: '120px', height: 'auto', marginRight: '20px' }} />
        </a>
        <h2 className="mb-0">문서 관리</h2>
      </div>

      {error && (
        <div className="alert alert-danger alert-dismissible">
          {error}
          <button type="button" className="btn-close" onClick={() => setError(null)}></button>
        </div>
      )}

      {/* 업로드 폼 */}
      <div className="card mb-4">
        <div className="card-body">
          <h5 className="card-title">문서 업로드</h5>
          <form onSubmit={handleUpload}>
            <div className="row g-3">
              <div className="col-md-6">
                <label className="form-label">파일 선택</label>
                <input
                  type="file"
                  id="fileInput"
                  className="form-control"
                  onChange={handleFileChange}
                  accept="image/*,.pdf"
                  required
                />
              </div>
              <div className="col-md-4">
                <label className="form-label">환자 ID (선택)</label>
                <input
                  type="number"
                  className="form-control"
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  placeholder="본인이면 비워두세요"
                />
              </div>
              <div className="col-md-2 d-flex align-items-end">
                <button type="submit" className="btn btn-primary w-100" disabled={uploading || !selectedFile}>
                  {uploading ? "업로드 중..." : "업로드"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* 필터 */}
      <div className="card mb-4">
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-4">
              <label className="form-label">환자 ID</label>
              <input
                type="number"
                className="form-control"
                value={filters.patient_id}
                onChange={(e) => setFilters({ ...filters, patient_id: e.target.value, page: 1 })}
                placeholder="전체"
              />
            </div>
            <div className="col-md-4">
              <label className="form-label">상태</label>
              <select
                className="form-select"
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value, page: 1 })}
              >
                <option value="">전체</option>
                <option value="pending">대기 중</option>
                <option value="processing">처리 중</option>
                <option value="completed">완료</option>
                <option value="failed">실패</option>
              </select>
            </div>
            <div className="col-md-4 d-flex align-items-end">
              <button className="btn btn-secondary w-100" onClick={loadDocuments} disabled={loading}>
                {loading ? "로딩 중..." : "새로고침"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 문서 목록 */}
      <div className="card">
        <div className="card-body">
          <h5 className="card-title">문서 목록</h5>
          {loading && documents.length === 0 ? (
            <div className="text-center py-5">로딩 중...</div>
          ) : documents.length === 0 ? (
            <div className="text-center py-5 text-muted">문서가 없습니다.</div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover">
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
                  {documents.map((doc) => (
                    <tr key={doc.id}>
                      <td>{doc.id}</td>
                      <td>{doc.original_filename || doc.file_url}</td>
                      <td>{doc.patient_id}</td>
                      <td>
                        <span className={getStatusBadge(doc.status)}>{getStatusText(doc.status)}</span>
                      </td>
                      <td>{new Date(doc.created_at).toLocaleString("ko-KR")}</td>
                      <td>
                        <div className="btn-group btn-group-sm">
                          {doc.status === "failed" && (
                            <button className="btn btn-warning" onClick={() => handleRetry(doc.id)}>
                              재시도
                            </button>
                          )}
                          <button className="btn btn-danger" onClick={() => handleDelete(doc.id)}>
                            삭제
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 페이지네이션 */}
          <div className="d-flex justify-content-center gap-2 mt-3">
            <button
              className="btn btn-outline-primary btn-sm"
              onClick={() => setFilters({ ...filters, page: Math.max(1, filters.page - 1) })}
              disabled={filters.page === 1}
            >
              이전
            </button>
            <span className="align-self-center">페이지 {filters.page}</span>
            <button
              className="btn btn-outline-primary btn-sm"
              onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
              disabled={documents.length < filters.page_size}
            >
              다음
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DocumentManagement;
