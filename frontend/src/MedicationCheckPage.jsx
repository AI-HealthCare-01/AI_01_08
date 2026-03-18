import React, { useEffect, useMemo, useState } from "react";
import AppLayout from "./components/AppLayout.jsx";

const API_PREFIX = "/api/v1";

const STATUS_META = {
  taken: { label: "복용완료", color: "#2563eb", dot: "#14b8a6", bg: "#eef4ff" },
  pending: { label: "복용대기", color: "#b7791f", dot: "#f4b400", bg: "#fff8e8" },
  missed: { label: "미복용", color: "#ef4444", dot: "#ef4444", bg: "#fff1f2" },
  skipped: { label: "건너뜀", color: "#6b7280", dot: "#9ca3af", bg: "#f3f4f6" },
};

const MEAL_ORDER = ["아침", "점심", "저녁", "취침 전"];

const MedicationCheckPage = ({
  linkedPatients = [],
  myPatient = null,
  loginRole = "PATIENT",
  me = null,
  userName = "사용자",
  modeOptions = [],
  currentMode = "PATIENT",
  onModeChange,
}) => {
  const effectiveMode = currentMode || loginRole;
  const isCaregiver = effectiveMode === "CAREGIVER" || effectiveMode === "GUARDIAN";

  const patients = useMemo(() => {
    if (isCaregiver) {
      return (linkedPatients || [])
        .filter((patient) => patient?.id)
        .map((patient) => ({
          id: Number(patient.id),
          name: patient.name || patient.display_name || `피보호자 ${patient.id}`,
          ageLabel: patient.ageLabel || patient.subtitle || "",
          imageUrl: patient.imageUrl || "",
        }));
    }

    return myPatient?.id
      ? [
          {
            id: Number(myPatient.id),
            name: myPatient.name || myPatient.display_name || "복약자",
            ageLabel: myPatient.ageLabel || "",
            imageUrl: myPatient.imageUrl || "",
          },
        ]
      : [];
  }, [isCaregiver, linkedPatients, myPatient]);

  const [selectedPatientId, setSelectedPatientId] = useState(
    isCaregiver ? "all" : patients[0]?.id || ""
  );
  const [selectedDate, setSelectedDate] = useState(() =>
    new Date().toISOString().slice(0, 10)
  );

  const [statusData, setStatusData] = useState([]);
  const [summaryMap, setSummaryMap] = useState({});
  const [loading, setLoading] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const notificationTarget = useMemo(() => {
    if (typeof window === "undefined") return null;

    const params = new URLSearchParams(window.location.search);
    const patientId = params.get("patient_id");
    const scheduleId = params.get("schedule_id");
    const scheduleTimeId = params.get("schedule_time_id");
    const scheduledAt = params.get("scheduled_at");

    if (!patientId && !scheduleId && !scheduleTimeId && !scheduledAt) {
      return null;
    }

    return {
      patientId: patientId ? Number(patientId) : null,
      scheduleId: scheduleId ? Number(scheduleId) : null,
      scheduleTimeId: scheduleTimeId ? Number(scheduleTimeId) : null,
      scheduledAt,
      scheduledDate: scheduledAt ? String(scheduledAt).slice(0, 10) : null,
    };
  }, []);

  useEffect(() => {
    if (!isCaregiver && patients[0]?.id) {
      setSelectedPatientId(patients[0].id);
    }
  }, [isCaregiver, patients]);

  useEffect(() => {
    if (!notificationTarget?.scheduledDate) return;
    setSelectedDate((prev) =>
      prev === notificationTarget.scheduledDate ? prev : notificationTarget.scheduledDate
    );
  }, [notificationTarget]);

  useEffect(() => {
    if (!isCaregiver || !notificationTarget?.patientId) return;
    setSelectedPatientId((prev) =>
      String(prev) === String(notificationTarget.patientId) ? prev : String(notificationTarget.patientId)
    );
  }, [isCaregiver, notificationTarget]);

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

  const getErrorMessage = (body, status) => {
    if (Array.isArray(body?.detail)) {
      return body.detail
        .map((d) => d?.msg || d?.message || JSON.stringify(d))
        .join(", ");
    }

    if (typeof body?.detail === "string") {
      return body.detail;
    }

    if (typeof body?.message === "string") {
      return body.message;
    }

    if (typeof body?.error?.message === "string") {
      return body.error.message;
    }

    return `status ${status}`;
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

  const inferMealLabel = (scheduledAt) => {
    try {
      const date = new Date(scheduledAt);
      const hour = date.getHours();

      if (hour < 10) return "아침";
      if (hour < 15) return "점심";
      if (hour < 20) return "저녁";
      return "취침 전";
    } catch {
      return "복약";
    }
  };

  const formatTime = (scheduledAt) => {
    try {
      const date = new Date(scheduledAt);
      return date.toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    } catch {
      return "";
    }
  };

  const normalizeStatus = (raw) => {
    const value = String(raw || "").toLowerCase();
    if (value === "taken") return "taken";
    if (value === "missed") return "missed";
    if (value === "skipped") return "skipped";
    return "pending";
  };

  const flattenStatusResponse = (responseData, patientId) => {
    const days = responseData?.days || [];
    const patientInfo = patients.find((p) => p.id === Number(patientId));

    if (!Array.isArray(days)) return [];

    return days.flatMap((dayBlock) => {
      const day = dayBlock?.day;
      const items = Array.isArray(dayBlock?.items) ? dayBlock.items : [];

      return items.map((item, index) => ({
        id: `${patientId}-${item.schedule_id}-${item.schedule_time_id}-${item.scheduled_at || index}`,
        patient_id: Number(patientId),
        patient_name: patientInfo?.name || `복약자 ${patientId}`,
        patient_age_label: patientInfo?.ageLabel || "",
        imageUrl: patientInfo?.imageUrl || "",
        day,
        schedule_id: Number(item.schedule_id),
        schedule_time_id: Number(item.schedule_time_id),
        patient_med_id: Number(item.patient_med_id),
        scheduled_at: item.scheduled_at,
        scheduled_date: item.scheduled_at ? String(item.scheduled_at).slice(0, 10) : day,
        scheduled_time: formatTime(item.scheduled_at),
        meal_label: inferMealLabel(item.scheduled_at),
        status: normalizeStatus(item.status),
        taken_at: item.taken_at,
        note: item.note,
      }));
    });
  };

  const fetchPatientStatus = async (patientId) => {
    const params = new URLSearchParams();
    params.set("patient_id", String(patientId));
    params.set("from", selectedDate);
    params.set("to", selectedDate);

    const res = await authFetch(`${API_PREFIX}/schedules/status?${params.toString()}`);
    const body = await safeJson(res);

    if (!res.ok) {
      throw new Error(getErrorMessage(body, res.status));
    }

    const data = body?.data || body || {};

    return {
      patientId,
      items: flattenStatusResponse(data, patientId),
      summary: data?.summary || null,
    };
  };

  const loadStatus = async () => {
    setLoading(true);
    setError(null);

    try {
      let targets = [];

      if (isCaregiver) {
        if (selectedPatientId === "all") {
          targets = patients.map((p) => p.id);
        } else if (selectedPatientId) {
          targets = [Number(selectedPatientId)];
        }
      } else if (patients[0]?.id) {
        targets = [patients[0].id];
      }

      if (targets.length === 0) {
        setStatusData([]);
        setSummaryMap({});
        return;
      }

      const results = await Promise.all(targets.map((patientId) => fetchPatientStatus(patientId)));

      const mergedItems = results.flatMap((result) => result.items);
      const nextSummaryMap = {};
      results.forEach((result) => {
        nextSummaryMap[result.patientId] = result.summary;
      });

      setStatusData(mergedItems);
      setSummaryMap(nextSummaryMap);
    } catch (err) {
      setError(err.message || "복약 현황을 불러오지 못했습니다.");
      setStatusData([]);
      setSummaryMap({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, [selectedPatientId, selectedDate, isCaregiver, patients.length]);

  const filteredItems = useMemo(() => {
    if (!isCaregiver || selectedPatientId === "all") return statusData;
    return statusData.filter((item) => String(item.patient_id) === String(selectedPatientId));
  }, [statusData, selectedPatientId, isCaregiver]);

  const groupedByPatient = useMemo(() => {
    const map = new Map();

    filteredItems.forEach((item) => {
      const current = map.get(item.patient_id) || {
        patient_id: item.patient_id,
        patient_name: item.patient_name,
        patient_age_label: item.patient_age_label,
        imageUrl: item.imageUrl,
        items: [],
      };
      current.items.push(item);
      map.set(item.patient_id, current);
    });

    return Array.from(map.values()).map((group) => ({
      ...group,
      items: group.items.sort((a, b) => {
        const aIndex = MEAL_ORDER.includes(a.meal_label) ? MEAL_ORDER.indexOf(a.meal_label) : 999;
        const bIndex = MEAL_ORDER.includes(b.meal_label) ? MEAL_ORDER.indexOf(b.meal_label) : 999;
        if (aIndex !== bIndex) return aIndex - bIndex;
        return String(a.scheduled_at).localeCompare(String(b.scheduled_at));
      }),
    }));
  }, [filteredItems]);

  const summary = useMemo(() => {
    const patientCount = groupedByPatient.length;
    const takenCount = filteredItems.filter((item) => item.status === "taken").length;
    const missedCount = filteredItems.filter((item) => item.status === "missed").length;
    return { patientCount, takenCount, missedCount };
  }, [filteredItems, groupedByPatient]);

  const highlightedItemId = useMemo(() => {
    if (!notificationTarget) return null;

    const targetScheduledAt = notificationTarget.scheduledAt
      ? String(notificationTarget.scheduledAt)
      : null;

    const matched = filteredItems.find((item) => {
      if (
        notificationTarget.patientId &&
        Number(item.patient_id) !== Number(notificationTarget.patientId)
      ) {
        return false;
      }

      if (
        notificationTarget.scheduleId &&
        Number(item.schedule_id) !== Number(notificationTarget.scheduleId)
      ) {
        return false;
      }

      if (
        notificationTarget.scheduleTimeId &&
        Number(item.schedule_time_id) !== Number(notificationTarget.scheduleTimeId)
      ) {
        return false;
      }

      if (targetScheduledAt && String(item.scheduled_at) !== targetScheduledAt) {
        return false;
      }

      return true;
    });

    return matched?.id || null;
  }, [filteredItems, notificationTarget]);

  useEffect(() => {
    if (!highlightedItemId) return;

    const timer = window.setTimeout(() => {
      const target = document.getElementById(`medication-item-${highlightedItemId}`);
      target?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 150);

    return () => window.clearTimeout(timer);
  }, [highlightedItemId]);

  const toggleSelectedPatient = (patientId) => {
    setSelectedIds((prev) =>
      prev.includes(patientId)
        ? prev.filter((id) => id !== patientId)
        : [...prev, patientId]
    );
  };

  const toggleAllSelected = () => {
    const allIds = groupedByPatient.map((group) => group.patient_id);
    if (selectedIds.length === allIds.length) {
      setSelectedIds([]);
      return;
    }
    setSelectedIds(allIds);
  };

  const handleCheck = async (item) => {
    setActionLoadingId(item.id);
    setError(null);
    setSuccessMessage(null);

    try {
      const res = await authFetch(`${API_PREFIX}/schedules/${item.schedule_id}/check`, {
        method: "POST",
        body: JSON.stringify({
          schedule_time_id: item.schedule_time_id,
          scheduled_date: item.scheduled_date,
        }),
      });

      const body = await safeJson(res);

      if (!res.ok) {
        throw new Error(getErrorMessage(body, res.status));
      }

      setStatusData((prev) =>
        prev.map((current) =>
          current.id === item.id
            ? {
                ...current,
                status: "taken",
                taken_at: body?.data?.taken_at || body?.taken_at || new Date().toISOString(),
              }
            : current
        )
      );
      setSuccessMessage(`${item.scheduled_time} 복약 상태를 복용 완료로 반영했습니다.`);
    } catch (err) {
      setError(err.message || "복용 완료 처리에 실패했습니다.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleSkip = async (item) => {
    setActionLoadingId(item.id);
    setError(null);
    setSuccessMessage(null);

    try {
      const res = await authFetch(`${API_PREFIX}/schedules/${item.schedule_id}/skip`, {
        method: "POST",
        body: JSON.stringify({
          schedule_time_id: item.schedule_time_id,
          scheduled_date: item.scheduled_date,
        }),
      });

      const body = await safeJson(res);

      if (!res.ok) {
        throw new Error(getErrorMessage(body, res.status));
      }

      setStatusData((prev) =>
        prev.map((current) =>
          current.id === item.id
            ? {
                ...current,
                status: "skipped",
                taken_at: null,
              }
            : current
        )
      );
      setSuccessMessage(`${item.scheduled_time} 복약 상태를 건너뜀으로 반영했습니다.`);
    } catch (err) {
      setError(err.message || "건너뛰기 처리에 실패했습니다.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleUndo = async (item) => {
    setActionLoadingId(item.id);
    setError(null);
    setSuccessMessage(null);

    try {
      const res = await authFetch(`${API_PREFIX}/schedules/${item.schedule_id}/check`, {
        method: "DELETE",
        body: JSON.stringify({
          schedule_time_id: item.schedule_time_id,
          scheduled_date: item.scheduled_date,
        }),
      });

      const body = await safeJson(res);

      if (!res.ok) {
        throw new Error(getErrorMessage(body, res.status));
      }

      setStatusData((prev) =>
        prev.map((current) =>
          current.id === item.id
            ? { ...current, status: "pending", taken_at: null }
            : current
        )
      );
      setSuccessMessage(`${item.scheduled_time} 복약 상태를 다시 확인 전으로 되돌렸습니다.`);
    } catch (err) {
      setError(err.message || "복약 기록 취소에 실패했습니다.");
    } finally {
      setActionLoadingId(null);
    }
  };

  useEffect(() => {
    if (!successMessage) return undefined;

    const timer = window.setTimeout(() => {
      setSuccessMessage(null);
    }, 2500);

    return () => window.clearTimeout(timer);
  }, [successMessage]);

  const goToNotificationPage = (patientId, item) => {
    const patientName =
      item?.patient_name ||
      patients.find((p) => p.id === Number(patientId))?.name ||
      "";

    const params = new URLSearchParams();

    if (patientId) params.set("patient_id", String(patientId));
    if (item?.schedule_id) params.set("schedule_id", String(item.schedule_id));

    params.set("prefill", "1");
    params.set("type", "missed_alert");
    params.set("title", "복약 확인 요청");
    params.set(
      "message",
      `${patientName ? `${patientName} ` : ""}복용 기록이 없어 확인이 필요합니다. 복용 여부를 확인해 주세요.`
    );

    window.location.href = `/auth-demo/app/notifications?${params.toString()}`;
  };

  const formatSelectedDate = () => {
    try {
      return new Intl.DateTimeFormat("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
        weekday: "long",
      }).format(new Date(selectedDate));
    } catch {
      return selectedDate;
    }
  };

  const renderStatusLegend = () => (
    <div className="d-flex align-items-center justify-content-end gap-3 flex-wrap small text-muted mt-3">
      {Object.entries(STATUS_META).map(([key, value]) => (
        <div className="d-flex align-items-center gap-1" key={key}>
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: "999px",
              display: "inline-block",
              backgroundColor: value.dot,
            }}
          />
          {value.label}
        </div>
      ))}
    </div>
  );

  return (
    <AppLayout
      activeKey="medication-check"
      title="복약 체크"
      description={isCaregiver ? "연동 복약자의 복약 상태를 확인하고 필요한 알림을 보낼 수 있습니다." : "오늘 복약 일정을 확인하고 상태를 기록하세요."}
      loginRole={loginRole}
      userName={userName}
      modeOptions={modeOptions}
      currentMode={currentMode}
      onModeChange={onModeChange}
    >
      <div className="row g-4">
        <div className="col-xl-4">
          <div className="card border-0 shadow-sm mb-3">
            <div className="card-body">
              <h6 className="fw-bold mb-3">기준 날짜</h6>
              <input
                className="form-control"
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
              />
            </div>
          </div>

            {isCaregiver && (
              <div className="card border-0 shadow-sm mb-3">
                <div className="card-body">
                  <h6 className="fw-bold mb-3">피보호자 선택</h6>
                  <select
                    className="form-select mb-3"
                    value={selectedPatientId}
                    onChange={(e) => setSelectedPatientId(e.target.value)}
                  >
                    <option value="all">전체 보기</option>
                    {patients.map((patient) => (
                      <option key={patient.id} value={patient.id}>
                        {patient.name}
                      </option>
                    ))}
                  </select>

                  <button
                    type="button"
                    className="btn btn-primary btn-sm w-100"
                    onClick={toggleAllSelected}
                    disabled={groupedByPatient.length === 0}
                  >
                    {selectedIds.length === groupedByPatient.length ? "전체 선택 해제" : "전체 알림 보내기"}
                  </button>
                </div>
              </div>
            )}

            <div className="card border-0 shadow-sm">
              <div className="card-body">
                <h6 className="fw-bold mb-3">오늘 요약</h6>
                <div className="mb-2 small text-muted">대상 복약자 {summary.patientCount}명</div>
                <div className="mb-2 small text-muted">복용 완료 {summary.takenCount}건</div>
                <div className="small text-muted">미복용 {summary.missedCount}건</div>
              </div>
            </div>
          </div>

          <div className="col-xl-8">
            <div className="card border-0 shadow-sm">
              <div className="card-body">
                <div className="d-flex justify-content-between align-items-start gap-3 flex-wrap mb-4">
                  <div>
                    <h2 className="fw-bold mb-1">복약 체크</h2>
                    <div className="text-muted">{formatSelectedDate()}</div>
                  </div>
                </div>

                {error && <div className="alert alert-danger">{error}</div>}
                {successMessage && <div className="alert alert-success py-2">{successMessage}</div>}

                {loading ? (
                  <div className="text-center py-5">
                    <div className="spinner-border" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                  </div>
                ) : groupedByPatient.length === 0 ? (
                  <div className="text-center py-5 text-muted">표시할 복약 일정이 없습니다.</div>
                ) : isCaregiver ? (
                  <>
                    <div className="row g-3 mb-4">
                      <div className="col-md-4">
                        <div className="card border-0" style={{ backgroundColor: "#f8fafc" }}>
                          <div className="card-body">
                            <div className="small text-muted mb-2">총 피보호자</div>
                            <div className="fs-2 fw-bold">{summary.patientCount}명</div>
                          </div>
                        </div>
                      </div>
                      <div className="col-md-4">
                        <div className="card border-0" style={{ backgroundColor: "#f8fafc" }}>
                          <div className="card-body">
                            <div className="small text-muted mb-2">오늘 복용 완료</div>
                            <div className="fs-2 fw-bold">{summary.takenCount}건</div>
                          </div>
                        </div>
                      </div>
                      <div className="col-md-4">
                        <div className="card border-0" style={{ backgroundColor: "#f8fafc" }}>
                          <div className="card-body">
                            <div className="small text-muted mb-2">미복용</div>
                            <div className="fs-2 fw-bold">{summary.missedCount}건</div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="card border-0" style={{ backgroundColor: "#f9fbff" }}>
                      <div className="card-body">
                        <div className="fw-bold fs-5 mb-3">피보호자 목록</div>

                        {groupedByPatient.map((group) => (
                          <div
                            key={group.patient_id}
                            className="border rounded-4 p-3 mb-3"
                            style={{ backgroundColor: "#fff" }}
                          >
                            <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
                              <div className="d-flex align-items-center gap-2">
                                <input
                                  type="checkbox"
                                  className="form-check-input mt-0"
                                  checked={selectedIds.includes(group.patient_id)}
                                  onChange={() => toggleSelectedPatient(group.patient_id)}
                                />
                                <div
                                  className="rounded-circle bg-light d-flex align-items-center justify-content-center"
                                  style={{ width: 36, height: 36, overflow: "hidden" }}
                                >
                                  {group.imageUrl ? (
                                    <img
                                      src={group.imageUrl}
                                      alt={group.patient_name}
                                      style={{ width: "100%", height: "100%", objectFit: "cover" }}
                                    />
                                  ) : (
                                    <span className="small">{group.patient_name.slice(0, 1)}</span>
                                  )}
                                </div>
                                <div>
                                  <div className="fw-semibold">{group.patient_name}</div>
                                  {group.patient_age_label && (
                                    <div className="small text-muted">{group.patient_age_label}</div>
                                  )}
                                </div>
                              </div>

                              <div className="d-flex gap-2">
                                <button
                                  className="btn btn-outline-secondary btn-sm"
                                  onClick={() => goToNotificationPage(group.patient_id)}
                                >
                                  알림센터
                                </button>
                              </div>
                            </div>

                            <div className="row g-2">
                              {group.items.map((item) => {
                                const meta = STATUS_META[item.status] || STATUS_META.pending;
                                const isHighlighted = highlightedItemId === item.id;

                                return (
                                  <div className="col-md-4" key={item.id}>
                                    <div
                                      id={`medication-item-${item.id}`}
                                      className="rounded-4 p-3 h-100"
                                      style={{
                                        backgroundColor: isHighlighted ? "#fff7d6" : meta.bg,
                                        border: isHighlighted ? "2px solid #f59e0b" : "1px solid transparent",
                                        boxShadow: isHighlighted
                                          ? "0 0 0 4px rgba(245, 158, 11, 0.18)"
                                          : "none",
                                        transition: "all 0.2s ease",
                                      }}
                                    >
                                      <div className="d-flex justify-content-between align-items-center mb-2">
                                        <div>
                                          <div className="small fw-semibold">{item.meal_label}</div>
                                          <div className="small text-muted">{item.scheduled_time}</div>
                                        </div>
                                        <span
                                          style={{
                                            width: 12,
                                            height: 12,
                                            borderRadius: "999px",
                                            display: "inline-block",
                                            backgroundColor: meta.dot,
                                          }}
                                        />
                                      </div>

                                      <div className="small text-muted mb-2">복약 항목 #{item.patient_med_id}</div>

                                      {item.status === "taken" ? (
                                        <button
                                          className="btn btn-sm w-100 mb-2"
                                          style={{
                                            backgroundColor: meta.color,
                                            color: "#fff",
                                            border: "none",
                                          }}
                                          disabled={actionLoadingId === item.id}
                                          onClick={() => handleUndo(item)}
                                        >
                                          {actionLoadingId === item.id ? "처리 중..." : "복용완료"}
                                        </button>
                                      ) : item.status === "skipped" ? (
                                        <button
                                          className="btn btn-secondary btn-sm w-100 mb-2"
                                          onClick={() => handleUndo(item)}
                                          disabled={actionLoadingId === item.id}
                                        >
                                          {actionLoadingId === item.id ? "처리 중..." : "건너뜀 (취소)"}
                                        </button>
                                      ) : (
                                        <>
                                          <button
                                            className="btn btn-sm w-100 mb-2"
                                            style={{
                                              backgroundColor: item.status === "missed" ? "#ef4444" : "#2563eb",
                                              color: "#fff",
                                              border: "none",
                                            }}
                                            disabled={actionLoadingId === item.id}
                                            onClick={() => handleCheck(item)}
                                          >
                                            {actionLoadingId === item.id
                                              ? "처리 중..."
                                              : item.status === "missed"
                                              ? "지금 복용 체크"
                                              : "복용하기"}
                                          </button>

                                          <button
                                            className="btn btn-outline-secondary btn-sm w-100"
                                            disabled={actionLoadingId === item.id}
                                            onClick={() => handleSkip(item)}
                                          >
                                            건너뛰기
                                          </button>
                                        </>
                                      )}

                                      {item.status === "missed" && (
                                        <button
                                          className="btn btn-link btn-sm w-100 text-decoration-none mt-1"
                                          onClick={() => goToNotificationPage(group.patient_id, item)}
                                        >
                                          알림 보내기
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ))}

                        {renderStatusLegend()}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="card border-0" style={{ backgroundColor: "#f9fbff" }}>
                    <div className="card-body">
                      <div
                        className="rounded-4 p-4 mb-4"
                        style={{ backgroundColor: "#fff" }}
                      >
                        <div className="fs-2 fw-bold mb-2">
                          안녕하세요, {me?.name || patients[0]?.name || "회원"}님
                        </div>
                        <div className="text-muted">
                          오늘도 건강한 하루 되세요. 오늘 복약 일정을 확인해보세요.
                        </div>
                      </div>

                      <div className="fw-bold fs-2 mb-1">오늘의 복약 스케줄</div>
                      <div className="text-muted mb-4">{formatSelectedDate()}</div>

                      <div className="d-flex flex-column gap-3">
                        {filteredItems.map((item) => {
                          const meta = STATUS_META[item.status] || STATUS_META.pending;

                          return (
                            <div
                              key={item.id}
                              className="rounded-4 p-4"
                              style={{ backgroundColor: "#fff" }}
                            >
                              <div className="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                                <div>
                                  <div className="d-flex align-items-center gap-2 mb-1">
                                    <div className="fs-2 fw-bold">{item.scheduled_time}</div>
                                    <div className="small text-muted">{item.meal_label}</div>
                                  </div>
                                  <div className="fw-semibold mb-2">복용 정보</div>
                                  <div className="d-flex gap-2 flex-wrap">
                                    <span
                                      className="badge rounded-pill text-dark"
                                      style={{ backgroundColor: "#e5e7eb" }}
                                    >
                                      복약 항목 #{item.patient_med_id}
                                    </span>
                                  </div>
                                </div>

                                <div className="d-flex align-items-center gap-3">
                                  <span
                                    style={{
                                      width: 14,
                                      height: 14,
                                      borderRadius: "999px",
                                      display: "inline-block",
                                      backgroundColor: meta.dot,
                                    }}
                                  />

                                  {item.status === "taken" ? (
                                    <button
                                      className="btn btn-sm"
                                      style={{
                                        backgroundColor: meta.color,
                                        color: "#fff",
                                        border: "none",
                                        minWidth: 110,
                                      }}
                                      onClick={() => handleUndo(item)}
                                      disabled={actionLoadingId === item.id}
                                    >
                                      {actionLoadingId === item.id ? "처리 중..." : "복용완료"}
                                    </button>
                                  ) : item.status === "skipped" ? (
                                    <button
                                      className="btn btn-secondary btn-sm"
                                      onClick={() => handleUndo(item)}
                                      disabled={actionLoadingId === item.id}
                                    >
                                      {actionLoadingId === item.id ? "처리 중..." : "건너뜀 (취소)"}
                                    </button>
                                  ) : (
                                    <div className="d-flex flex-column gap-2">
                                      <button
                                        className="btn btn-sm"
                                        style={{
                                          backgroundColor: item.status === "missed" ? "#ef4444" : "#2563eb",
                                          color: "#fff",
                                          border: "none",
                                          minWidth: 110,
                                        }}
                                        onClick={() => handleCheck(item)}
                                        disabled={actionLoadingId === item.id}
                                      >
                                        {actionLoadingId === item.id
                                          ? "처리 중..."
                                          : item.status === "missed"
                                          ? "지금 복용 체크"
                                          : "복용하기"}
                                      </button>

                                      <button
                                        className="btn btn-outline-secondary btn-sm"
                                        onClick={() => handleSkip(item)}
                                        disabled={actionLoadingId === item.id}
                                      >
                                        건너뛰기
                                      </button>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {renderStatusLegend()}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
    </AppLayout>
  );
};

export default MedicationCheckPage;
