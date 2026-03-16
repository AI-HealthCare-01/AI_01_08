import React, { useEffect, useMemo, useState } from "react";

const API_PREFIX = "/api/v1";

const TYPE_META = {
  intake_reminder: {
    label: "복약 리마인드",
    bg: "#dbeafe",
    color: "#2563eb",
  },
  missed_alert: {
    label: "미복용 알림",
    bg: "#ffedd5",
    color: "#ea580c",
  },
  ocr_done: {
    label: "처방전 업데이트",
    bg: "#f3e8ff",
    color: "#a855f7",
  },
  guide_ready: {
    label: "AI 가이드",
    bg: "#dcfce7",
    color: "#16a34a",
  },
  taken: {
    label: "복용 완료",
    bg: "#ccfbf1",
    color: "#0f766e",
  },
  default: {
    label: "알림",
    bg: "#e5e7eb",
    color: "#374151",
  },
};

const NotificationPage = ({
  linkedPatients = [],
  myPatient = null,
  loginRole = "PATIENT",
  me = null,
}) => {
  const isCaregiver = loginRole === "CAREGIVER" || loginRole === "GUARDIAN";

  const patientsSource = useMemo(() => {
    if (isCaregiver) {
      return (linkedPatients || []).filter((patient) => patient?.id);
    }
    return myPatient ? [myPatient] : [];
  }, [isCaregiver, linkedPatients, myPatient]);

  const normalizedPatients = useMemo(() => {
    return patientsSource.map((patient) => ({
      id: Number(patient.id),
      name: patient.name || `환자 ${patient.id}`,
    }));
  }, [patientsSource]);

  const [notifications, setNotifications] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);

  const [unreadCount, setUnreadCount] = useState(0);

  const [settings, setSettings] = useState({
    intake_reminder: true,
    missed_alert: true,
    ocr_done: true,
    guide_ready: true,
  });
  const [settingsSubmitting, setSettingsSubmitting] = useState(false);

  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [patientFilter, setPatientFilter] = useState("all");

  const [remindForm, setRemindForm] = useState({
    patient_id: normalizedPatients[0]?.id || "",
    type: "intake_reminder",
    title: "복약 리마인드",
    message: "복약 시간이예요! 확인해 주세요.",
    payload: "",
  });
  const [remindSubmitting, setRemindSubmitting] = useState(false);
  const [remindMessage, setRemindMessage] = useState(null);

  useEffect(() => {
    if (!remindForm.patient_id && normalizedPatients[0]?.id) {
      setRemindForm((prev) => ({
        ...prev,
        patient_id: normalizedPatients[0].id,
      }));
    }
  }, [normalizedPatients, remindForm.patient_id]);

  const readCookie = (name) => {
    if (typeof document === "undefined") return null;
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match ? decodeURIComponent(match[2]) : null;
  };

  const safeJson = async (res) => {
    try {
      return await res.json();
    } catch {
      return null;
    }
  };

  const authFetch = async (path, options = {}) => {
    const headers = new Headers(options.headers || {});

    if (!headers.has("Content-Type") && options.body) {
      headers.set("Content-Type", "application/json");
    }

    const accessToken =
      typeof window !== "undefined"
        ? window.localStorage.getItem("access_token") || readCookie("access_token")
        : null;

    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }

    return fetch(path, {
      ...options,
      headers,
      credentials: "include",
    });
  };

  const loadNotifications = async (cursor = null, append = false) => {
    if (!append) {
      setLoading(true);
    } else {
      setActionLoading(true);
    }

    setError(null);

    try {
      const params = new URLSearchParams();
      params.set("limit", "20");
      if (cursor) {
        params.set("cursor", String(cursor));
      }

      const res = await authFetch(`${API_PREFIX}/notifications?${params.toString()}`);
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(body?.detail || `status ${res.status}`);
      }

      const body = await safeJson(res);
      const data = body?.data || body || {};

      const items = data?.items || [];
      const cursorValue = data?.next_cursor ?? null;

      setNotifications((prev) => (append ? [...prev, ...items] : items));
      setNextCursor(cursorValue);
    } catch (err) {
      setError(err.message || "알림을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
      setActionLoading(false);
    }
  };

  const loadUnreadCount = async () => {
    try {
      const res = await authFetch(`${API_PREFIX}/notifications/unread-count`);
      if (!res.ok) return;

      const body = await safeJson(res);
      const data = body?.data || body || {};
      setUnreadCount(data?.count ?? 0);
    } catch {
      // ignore
    }
  };

  const loadSettings = async () => {
    try {
      const res = await authFetch(`${API_PREFIX}/notifications/settings`);
      if (!res.ok) return;

      const body = await safeJson(res);
      const data = body?.data || body;
      if (data) {
        setSettings({
          intake_reminder: !!data.intake_reminder,
          missed_alert: !!data.missed_alert,
          ocr_done: !!data.ocr_done,
          guide_ready: !!data.guide_ready,
        });
      }
    } catch {
      // ignore
    }
  };

  const loadAll = async () => {
    await Promise.all([
      loadNotifications(),
      loadUnreadCount(),
      loadSettings(),
    ]);
  };

  useEffect(() => {
    loadAll();
  }, []);

  const getPatientName = (patientId) => {
    const patient = normalizedPatients.find((p) => p.id === Number(patientId));
    return patient?.name || null;
  };

  const resolvePatientLabel = (item) => {
    const payload = item?.payload || {};
    const payloadPatientId = payload?.patient_id;
    const payloadPatientName = payload?.patient_name;

    if (payloadPatientName) return payloadPatientName;
    if (payloadPatientId) return getPatientName(payloadPatientId) || `환자 ${payloadPatientId}`;

    if (!isCaregiver && myPatient?.name) return myPatient.name;

    return null;
  };

  const filteredNotifications = useMemo(() => {
    return notifications.filter((item) => {
      const keyword = search.trim().toLowerCase();

      const patientLabel = resolvePatientLabel(item) || "";
      const title = item.title || "";
      const body = item.body || "";
      const type = item.type || "";

      if (typeFilter !== "all" && type !== typeFilter) {
        return false;
      }

      if (patientFilter !== "all") {
        const payloadPatientId = item?.payload?.patient_id;
        if (String(payloadPatientId || "") !== String(patientFilter)) {
          return false;
        }
      }

      if (!keyword) return true;

      return [patientLabel, title, body, type]
        .join(" ")
        .toLowerCase()
        .includes(keyword);
    });
  }, [notifications, search, typeFilter, patientFilter, isCaregiver, myPatient, normalizedPatients]);

  const getTypeMeta = (type) => {
    return TYPE_META[type] || TYPE_META.default;
  };

  const markRead = async (notificationId) => {
    setActionLoading(true);
    try {
      const res = await authFetch(`${API_PREFIX}/notifications/${notificationId}/read`, {
        method: "PATCH",
      });

      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(body?.detail || `status ${res.status}`);
      }

      setNotifications((prev) =>
        prev.map((item) =>
          item.id === notificationId
            ? { ...item, read_at: item.read_at || new Date().toISOString() }
            : item
        )
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      setError(err.message || "읽음 처리에 실패했습니다.");
    } finally {
      setActionLoading(false);
    }
  };

  const markAllRead = async () => {
    setActionLoading(true);
    try {
      const res = await authFetch(`${API_PREFIX}/notifications/read-all`, {
        method: "PATCH",
      });

      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(body?.detail || `status ${res.status}`);
      }

      setNotifications((prev) =>
        prev.map((item) => ({
          ...item,
          read_at: item.read_at || new Date().toISOString(),
        }))
      );
      setUnreadCount(0);
    } catch (err) {
      setError(err.message || "전체 읽음 처리에 실패했습니다.");
    } finally {
      setActionLoading(false);
    }
  };

  const submitSettings = async (e) => {
    e.preventDefault();
    setSettingsSubmitting(true);
    setError(null);

    try {
      const res = await authFetch(`${API_PREFIX}/notifications/settings`, {
        method: "PATCH",
        body: JSON.stringify(settings),
      });

      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(body?.detail || `status ${res.status}`);
      }

      await loadSettings();
    } catch (err) {
      setError(err.message || "설정 저장에 실패했습니다.");
    } finally {
      setSettingsSubmitting(false);
    }
  };

  const submitRemind = async (e) => {
    e.preventDefault();

    if (!remindForm.patient_id) {
      setRemindMessage("환자를 선택해주세요.");
      return;
    }

    setRemindSubmitting(true);
    setRemindMessage(null);
    setError(null);

    try {
      const payload = {
        patient_id: Number(remindForm.patient_id),
        type: remindForm.type,
        title: remindForm.title,
        message: remindForm.message,
      };

      if (remindForm.payload?.trim()) {
        payload.payload = JSON.parse(remindForm.payload);
      }

      const res = await authFetch(`${API_PREFIX}/notifications/remind`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(body?.detail || `status ${res.status}`);
      }

      setRemindMessage("리마인드를 전송했습니다.");
    } catch (err) {
      setRemindMessage(err.message || "리마인드 전송에 실패했습니다.");
    } finally {
      setRemindSubmitting(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="container py-4">
          <nav className="navbar navbar-expand-lg">
            <a
              className="navbar-brand fw-bold"
              href="/auth-demo/app"
              style={{ fontSize: "1.5rem" }}
            >
              복약관리시스템
            </a>
            <div className="ms-auto d-flex gap-2">
              <a className="btn btn-outline-light btn-sm" href="/auth-demo/app/dashboard">
                대시보드
              </a>
              <a className="btn btn-outline-light btn-sm" href="/auth-demo/app/schedule">
                스케줄
              </a>
            </div>
          </nav>
        </div>
      </header>

      <div className="container-fluid py-4">
        <div className="row">
          <div className="col-md-3">
            <div className="card border-0 shadow-sm mb-3">
              <div className="card-body">
                <h5 className="fw-bold mb-3">
                  복약관리시스템
                  <div className="small text-primary mt-1">
                    {isCaregiver ? "보호자 모드" : "복약자 모드"}
                  </div>
                </h5>

                <div className="list-group list-group-flush">
                  <a href="/auth-demo/app/dashboard" className="list-group-item list-group-item-action">
                    대시보드
                  </a>
                  <a href="/auth-demo/app/health-profile" className="list-group-item list-group-item-action">
                    처방전 업로드
                  </a>
                  <a href="/auth-demo/app/documents" className="list-group-item list-group-item-action">
                    맞춤 복약 가이드
                  </a>
                  <a href="/auth-demo/app/caregiver" className="list-group-item list-group-item-action active">
                    알림 센터
                  </a>
                  <a href="/auth-demo/app/schedule" className="list-group-item list-group-item-action">
                    스케줄
                  </a>
                  <a href="/auth-demo/app/profile" className="list-group-item list-group-item-action">
                    건강 프로필
                  </a>
                </div>
              </div>
            </div>

            <div className="card border-0 shadow-sm mb-3">
              <div className="card-body">
                <h6 className="fw-bold mb-3">알림 요약</h6>
                <div className="small text-muted mb-2">총 알림 {notifications.length}건</div>
                <div className="small text-muted">미읽음 알림 {unreadCount}건</div>
              </div>
            </div>

            <div className="card border-0 shadow-sm mb-3">
              <div className="card-body">
                <h6 className="fw-bold mb-3">알림 설정</h6>

                <form onSubmit={submitSettings}>
                  <div className="form-check mb-2">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="intake_reminder"
                      checked={settings.intake_reminder}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, intake_reminder: e.target.checked }))
                      }
                    />
                    <label className="form-check-label" htmlFor="intake_reminder">
                      복약 리마인드
                    </label>
                  </div>

                  <div className="form-check mb-2">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="missed_alert"
                      checked={settings.missed_alert}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, missed_alert: e.target.checked }))
                      }
                    />
                    <label className="form-check-label" htmlFor="missed_alert">
                      미복용 알림
                    </label>
                  </div>

                  <div className="form-check mb-2">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="ocr_done"
                      checked={settings.ocr_done}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, ocr_done: e.target.checked }))
                      }
                    />
                    <label className="form-check-label" htmlFor="ocr_done">
                      OCR 완료
                    </label>
                  </div>

                  <div className="form-check mb-3">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="guide_ready"
                      checked={settings.guide_ready}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, guide_ready: e.target.checked }))
                      }
                    />
                    <label className="form-check-label" htmlFor="guide_ready">
                      가이드 준비 완료
                    </label>
                  </div>

                  <button
                    type="submit"
                    className="btn btn-outline-primary btn-sm w-100"
                    disabled={settingsSubmitting}
                  >
                    {settingsSubmitting ? "저장 중..." : "설정 저장"}
                  </button>
                </form>
              </div>
            </div>

            {isCaregiver && (
              <div className="card border-0 shadow-sm">
                <div className="card-body">
                  <h6 className="fw-bold mb-3">수동 리마인드</h6>

                  <form onSubmit={submitRemind}>
                    <div className="mb-2">
                      <label className="form-label">환자</label>
                      <select
                        className="form-select"
                        value={remindForm.patient_id}
                        onChange={(e) =>
                          setRemindForm((prev) => ({
                            ...prev,
                            patient_id: e.target.value,
                          }))
                        }
                      >
                        <option value="">환자 선택</option>
                        {normalizedPatients.map((patient) => (
                          <option key={patient.id} value={patient.id}>
                            {patient.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="mb-2">
                      <label className="form-label">알림 타입</label>
                      <select
                        className="form-select"
                        value={remindForm.type}
                        onChange={(e) =>
                          setRemindForm((prev) => ({
                            ...prev,
                            type: e.target.value,
                          }))
                        }
                      >
                        <option value="intake_reminder">복약 리마인드</option>
                        <option value="missed_alert">미복용 알림</option>
                        <option value="ocr_done">OCR 완료</option>
                        <option value="guide_ready">가이드 준비 완료</option>
                      </select>
                    </div>

                    <div className="mb-2">
                      <label className="form-label">제목</label>
                      <input
                        className="form-control"
                        value={remindForm.title}
                        onChange={(e) =>
                          setRemindForm((prev) => ({
                            ...prev,
                            title: e.target.value,
                          }))
                        }
                      />
                    </div>

                    <div className="mb-2">
                      <label className="form-label">메시지</label>
                      <textarea
                        className="form-control"
                        rows="3"
                        value={remindForm.message}
                        onChange={(e) =>
                          setRemindForm((prev) => ({
                            ...prev,
                            message: e.target.value,
                          }))
                        }
                      />
                    </div>

                    <div className="mb-3">
                      <label className="form-label">payload(JSON, 선택)</label>
                      <input
                        className="form-control"
                        placeholder='{"patient_id":10001}'
                        value={remindForm.payload}
                        onChange={(e) =>
                          setRemindForm((prev) => ({
                            ...prev,
                            payload: e.target.value,
                          }))
                        }
                      />
                    </div>

                    <button
                      type="submit"
                      className="btn btn-primary btn-sm w-100"
                      disabled={remindSubmitting}
                    >
                      {remindSubmitting ? "전송 중..." : "리마인드 전송"}
                    </button>

                    {remindMessage && (
                      <div className="small mt-2 text-muted">{remindMessage}</div>
                    )}
                  </form>
                </div>
              </div>
            )}
          </div>

          <div className="col-md-9">
            <div className="card border-0 shadow-sm">
              <div className="card-body">
                <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
                  <div>
                    <h3 className="fw-bold mb-1">알림 센터</h3>
                    <div className="text-muted">
                      총 {notifications.length}개의 알림 / 미읽음 {unreadCount}건
                    </div>
                  </div>

                  <div className="d-flex gap-2">
                    <button
                      className="btn btn-outline-secondary btn-sm"
                      onClick={loadAll}
                      disabled={loading || actionLoading}
                    >
                      새로고침
                    </button>
                    <button
                      className="btn btn-outline-primary btn-sm"
                      onClick={markAllRead}
                      disabled={actionLoading}
                    >
                      모두 읽음 처리
                    </button>
                  </div>
                </div>

                <div className="row g-2 mb-4">
                  <div className="col-md-5">
                    <input
                      className="form-control"
                      placeholder="알림 검색"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </div>

                  <div className="col-md-3">
                    <select
                      className="form-select"
                      value={typeFilter}
                      onChange={(e) => setTypeFilter(e.target.value)}
                    >
                      <option value="all">알림 종류 전체</option>
                      <option value="intake_reminder">복약 리마인드</option>
                      <option value="missed_alert">미복용 알림</option>
                      <option value="ocr_done">OCR 완료</option>
                      <option value="guide_ready">가이드 준비 완료</option>
                    </select>
                  </div>

                  {isCaregiver && (
                    <div className="col-md-3">
                      <select
                        className="form-select"
                        value={patientFilter}
                        onChange={(e) => setPatientFilter(e.target.value)}
                      >
                        <option value="all">환자 전체</option>
                        {normalizedPatients.map((patient) => (
                          <option key={patient.id} value={String(patient.id)}>
                            {patient.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="col-md-1 d-grid">
                    <button
                      type="button"
                      className="btn btn-light border"
                      onClick={() => {
                        setSearch("");
                        setTypeFilter("all");
                        setPatientFilter("all");
                      }}
                    >
                      초기화
                    </button>
                  </div>
                </div>

                {error && <div className="alert alert-danger">{error}</div>}

                {loading ? (
                  <div className="text-center py-5">
                    <div className="spinner-border" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                  </div>
                ) : (
                  <div className="border rounded-4 overflow-hidden">
                    <div
                      className="d-flex align-items-center px-4 py-3 border-bottom"
                      style={{ backgroundColor: "#f8fafc" }}
                    >
                      <div className="fw-semibold">알림 목록</div>
                    </div>

                    {filteredNotifications.length === 0 ? (
                      <div className="px-4 py-5 text-center text-muted">
                        표시할 알림이 없습니다.
                      </div>
                    ) : (
                      filteredNotifications.map((item) => {
                        const meta = getTypeMeta(item.type);
                        const patientLabel = resolvePatientLabel(item);

                        return (
                          <div
                            key={item.id}
                            className="px-4 py-3 border-bottom"
                            style={{
                              backgroundColor: item.read_at ? "#ffffff" : "#f8fbff",
                            }}
                          >
                            <div className="d-flex justify-content-between align-items-start gap-3">
                              <div className="flex-grow-1">
                                <div className="d-flex align-items-center gap-2 flex-wrap mb-2">
                                  {!item.read_at && (
                                    <span
                                      style={{
                                        width: 8,
                                        height: 8,
                                        borderRadius: "999px",
                                        backgroundColor: "#2563eb",
                                        display: "inline-block",
                                      }}
                                    />
                                  )}

                                  {isCaregiver && patientLabel && (
                                    <span className="fw-semibold">{patientLabel}</span>
                                  )}

                                  <span
                                    className="px-2 py-1 rounded-pill small fw-semibold"
                                    style={{
                                      backgroundColor: meta.bg,
                                      color: meta.color,
                                    }}
                                  >
                                    {meta.label}
                                  </span>
                                </div>

                                <div className="fw-semibold mb-1">
                                  {item.title || meta.label}
                                </div>
                                <div className="text-muted small">
                                  {item.body || "알림 내용이 없습니다."}
                                </div>
                              </div>

                              <div className="d-flex flex-column align-items-end gap-2">
                                <div className="small text-muted">
                                  {new Date(item.created_at).toLocaleString("ko-KR")}
                                </div>

                                {!item.read_at ? (
                                  <button
                                    className="btn btn-outline-primary btn-sm"
                                    onClick={() => markRead(item.id)}
                                    disabled={actionLoading}
                                  >
                                    읽음 처리
                                  </button>
                                ) : (
                                  <span className="small text-muted">읽음</span>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}

                    {nextCursor && (
                      <div className="px-4 py-3 text-center">
                        <button
                          className="btn btn-outline-primary btn-sm"
                          onClick={() => loadNotifications(nextCursor, true)}
                          disabled={actionLoading}
                        >
                          더 보기
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotificationPage;