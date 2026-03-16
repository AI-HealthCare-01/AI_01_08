import React, { useEffect, useState } from "react";

const API_PREFIX = "/api/v1";

function HealthProfile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    height_cm: "",
    weight_kg: "",
    allergies: "",
    conditions: "",
    meds: "",
    is_smoker: null,
    avg_sleep_hours_per_day: "",
    avg_exercise_minutes_per_day: "",
    notes: "",
  });

  const authFetch = async (url, options = {}) => {
    const token = localStorage.getItem("access_token");
    const headers = {
      "Content-Type": "application/json",
      ...options.headers,
    };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return fetch(url, { ...options, headers, credentials: "include" });
  };

  const loadProfile = async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API_PREFIX}/users/me/health-profile`);
      if (res.ok) {
        const data = await res.json();
        setProfile(data.data);
        setFormData({
          height_cm: data.data?.height_cm || "",
          weight_kg: data.data?.weight_kg || "",
          allergies: data.data?.allergies?.join(", ") || "",
          conditions: data.data?.conditions?.join(", ") || "",
          meds: data.data?.meds?.join(", ") || "",
          is_smoker: data.data?.is_smoker,
          avg_sleep_hours_per_day: data.data?.avg_sleep_hours_per_day || "",
          avg_exercise_minutes_per_day: data.data?.avg_exercise_minutes_per_day || "",
          notes: data.data?.notes || "",
        });
      } else if (res.status === 404) {
        setProfile(null);
      } else {
        throw new Error(`status ${res.status}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = {
        height_cm: formData.height_cm ? parseFloat(formData.height_cm) : null,
        weight_kg: formData.weight_kg ? parseFloat(formData.weight_kg) : null,
        allergies: formData.allergies ? formData.allergies.split(",").map(s => s.trim()).filter(Boolean) : [],
        conditions: formData.conditions ? formData.conditions.split(",").map(s => s.trim()).filter(Boolean) : [],
        meds: formData.meds ? formData.meds.split(",").map(s => s.trim()).filter(Boolean) : [],
        is_smoker: formData.is_smoker,
        avg_sleep_hours_per_day: formData.avg_sleep_hours_per_day ? parseFloat(formData.avg_sleep_hours_per_day) : null,
        avg_exercise_minutes_per_day: formData.avg_exercise_minutes_per_day ? parseInt(formData.avg_exercise_minutes_per_day) : null,
        notes: formData.notes || null,
      };
      
      const method = profile ? "PATCH" : "POST";
      const res = await authFetch(`${API_PREFIX}/users/me/health-profile`, {
        method,
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        console.error('API Error:', body);
        const errorMsg = body.detail || body.message || JSON.stringify(body) || `status ${res.status}`;
        throw new Error(errorMsg);
      }
      await loadProfile();
      setEditing(false);
      setError(null);
    } catch (err) {
      console.error('Submit error:', err);
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("건강 프로필을 삭제하시겠습니까?")) return;
    setLoading(true);
    try {
      const res = await authFetch(`${API_PREFIX}/users/me/health-profile`, {
        method: "DELETE",
      });
      if (!res.ok) {
        throw new Error(`status ${res.status}`);
      }
      setProfile(null);
      setFormData({
        height_cm: "",
        weight_kg: "",
        allergies: "",
        conditions: "",
        meds: "",
        is_smoker: null,
        avg_sleep_hours_per_day: "",
        avg_exercise_minutes_per_day: "",
        notes: "",
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !profile) {
    return (
      <div className="container py-5">
        <div className="text-center">로딩 중...</div>
      </div>
    );
  }

  return (
    <div className="container py-5">
      <div className="d-flex align-items-center justify-content-center mb-4">
        <a href="/auth-demo/app" style={{ cursor: 'pointer', textDecoration: 'none' }}>
          <img src={`${import.meta.env.BASE_URL}mascot.png`} alt="약속이" style={{ width: '120px', height: 'auto', marginRight: '20px' }} />
        </a>
        <h2 className="mb-0">건강 프로필</h2>
      </div>
      <div className="row justify-content-center">
        <div className="col-lg-8">
          <div className="card shadow-sm">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center mb-4">
                <h3 className="mb-0">건강 프로필</h3>
                <div className="d-flex gap-2">
                  {profile && !editing && (
                    <>
                      <button className="btn btn-primary btn-sm" onClick={() => setEditing(true)}>
                        수정
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={handleDelete}>
                        삭제
                      </button>
                    </>
                  )}
                  {editing && (
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditing(false)}>
                      취소
                    </button>
                  )}
                </div>
              </div>

              {error && <div className="alert alert-danger">{error}</div>}

              {!profile && !editing ? (
                <div className="text-center py-5">
                  <p className="text-muted mb-3">등록된 건강 프로필이 없습니다.</p>
                  <button className="btn btn-primary" onClick={() => setEditing(true)}>
                    건강 프로필 등록
                  </button>
                </div>
              ) : editing ? (
                <form onSubmit={handleSubmit}>
                  <div className="row g-3">
                    <div className="col-md-6">
                      <label className="form-label">키 (cm)</label>
                      <input
                        type="number"
                        className="form-control"
                        name="height_cm"
                        value={formData.height_cm}
                        onChange={handleChange}
                        step="0.1"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label">몸무게 (kg)</label>
                      <input
                        type="number"
                        className="form-control"
                        name="weight_kg"
                        value={formData.weight_kg}
                        onChange={handleChange}
                        step="0.1"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label">알레르기 (쉼표로 구분)</label>
                      <input
                        type="text"
                        className="form-control"
                        name="allergies"
                        value={formData.allergies}
                        onChange={handleChange}
                        placeholder="예: 페니실린, 땅콩"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label">흡연 여부</label>
                      <select
                        className="form-select"
                        name="is_smoker"
                        value={formData.is_smoker === null ? "" : formData.is_smoker}
                        onChange={(e) => setFormData({...formData, is_smoker: e.target.value === "" ? null : e.target.value === "true"})}
                      >
                        <option value="">선택</option>
                        <option value="true">흡연</option>
                        <option value="false">비흡연</option>
                      </select>
                    </div>
                    <div className="col-12">
                      <label className="form-label">기저 질환 (쉼표로 구분)</label>
                      <textarea
                        className="form-control"
                        name="conditions"
                        value={formData.conditions}
                        onChange={handleChange}
                        rows="2"
                        placeholder="예: 고혈압, 당뇨"
                      />
                    </div>
                    <div className="col-12">
                      <label className="form-label">복용 중인 약 (쉼표로 구분)</label>
                      <textarea
                        className="form-control"
                        name="meds"
                        value={formData.meds}
                        onChange={handleChange}
                        rows="2"
                        placeholder="현재 복용 중인 약물"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label">하루 평균 수면 시간 (시간)</label>
                      <input
                        type="number"
                        className="form-control"
                        name="avg_sleep_hours_per_day"
                        value={formData.avg_sleep_hours_per_day}
                        onChange={handleChange}
                        step="0.5"
                        placeholder="7"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label">하루 평균 운동 시간 (분)</label>
                      <input
                        type="number"
                        className="form-control"
                        name="avg_exercise_minutes_per_day"
                        value={formData.avg_exercise_minutes_per_day}
                        onChange={handleChange}
                        placeholder="30"
                      />
                    </div>
                    <div className="col-12">
                      <label className="form-label">메모</label>
                      <textarea
                        className="form-control"
                        name="notes"
                        value={formData.notes}
                        onChange={handleChange}
                        rows="3"
                        placeholder="추가 정보"
                      />
                    </div>
                  </div>
                  <div className="d-grid gap-2 mt-4">
                    <button type="submit" className="btn btn-primary" disabled={loading}>
                      {loading ? "저장 중..." : profile ? "수정 완료" : "등록"}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="row g-3">
                  <div className="col-md-6">
                    <div className="border rounded p-3">
                      <div className="text-muted small">키</div>
                      <div className="fw-semibold">{profile.height_cm ? `${profile.height_cm} cm` : "—"}</div>
                    </div>
                  </div>
                  <div className="col-md-6">
                    <div className="border rounded p-3">
                      <div className="text-muted small">몸무게</div>
                      <div className="fw-semibold">{profile.weight_kg ? `${profile.weight_kg} kg` : "—"}</div>
                    </div>
                  </div>
                  <div className="col-md-6">
                    <div className="border rounded p-3">
                      <div className="text-muted small">BMI</div>
                      <div className="fw-semibold">{profile.bmi ? profile.bmi.toFixed(1) : "—"}</div>
                      {profile.bmi_status && <div className="small text-muted">{profile.bmi_status}</div>}
                    </div>
                  </div>
                  <div className="col-md-6">
                    <div className="border rounded p-3">
                      <div className="text-muted small">흡연 여부</div>
                      <div className="fw-semibold">{profile.is_smoker === null ? "—" : profile.is_smoker ? "흡연" : "비흡연"}</div>
                    </div>
                  </div>
                  <div className="col-12">
                    <div className="border rounded p-3">
                      <div className="text-muted small">알레르기</div>
                      <div className="fw-semibold">{profile.allergies?.length > 0 ? profile.allergies.join(", ") : "—"}</div>
                    </div>
                  </div>
                  <div className="col-12">
                    <div className="border rounded p-3">
                      <div className="text-muted small">기저 질환</div>
                      <div className="fw-semibold">{profile.conditions?.length > 0 ? profile.conditions.join(", ") : "—"}</div>
                    </div>
                  </div>
                  <div className="col-12">
                    <div className="border rounded p-3">
                      <div className="text-muted small">복용 중인 약</div>
                      <div className="fw-semibold">{profile.meds?.length > 0 ? profile.meds.join(", ") : "—"}</div>
                    </div>
                  </div>
                  <div className="col-md-6">
                    <div className="border rounded p-3">
                      <div className="text-muted small">평균 수면 시간</div>
                      <div className="fw-semibold">{profile.avg_sleep_hours_per_day ? `${profile.avg_sleep_hours_per_day}시간` : "—"}</div>
                    </div>
                  </div>
                  <div className="col-md-6">
                    <div className="border rounded p-3">
                      <div className="text-muted small">평균 운동 시간</div>
                      <div className="fw-semibold">{profile.avg_exercise_minutes_per_day ? `${profile.avg_exercise_minutes_per_day}분` : "—"}</div>
                    </div>
                  </div>
                  {profile.notes && (
                    <div className="col-12">
                      <div className="border rounded p-3">
                        <div className="text-muted small">메모</div>
                        <div className="fw-semibold">{profile.notes}</div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HealthProfile;
