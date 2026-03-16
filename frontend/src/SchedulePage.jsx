import React, { useEffect, useMemo, useState } from "react";

const API_PREFIX = "/api/v1";

const SchedulePage = ({ linkedPatients = [], myPatient = null, loginRole = "CAREGIVER" }) => {
  const patientsSource = useMemo(() => {
    if (loginRole === "PATIENT") {
      return myPatient ? [myPatient] : [];
    }
    return (linkedPatients || []).filter((patient) => patient?.id);
  }, [loginRole, linkedPatients, myPatient]);

  const normalizedPatients = useMemo(() => {
    return patientsSource.map((patient) => ({
      id: Number(patient.id),
      name: patient.name || `환자 ${patient.id}`,
    }));
  }, [patientsSource]);

  const defaultPatientId = normalizedPatients[0]?.id ?? "";
  const isCaregiver = loginRole === "CAREGIVER" || loginRole === "GUARDIAN";
  const initialSelectedPatientId = isCaregiver ? "all" : String(defaultPatientId || "");

  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState("month");
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(false);

  const [selectedPatientId, setSelectedPatientId] = useState(initialSelectedPatientId);

  const [showModal, setShowModal] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState(null);

  const [formData, setFormData] = useState({
    title: "",
    hospital_name: "",
    location: "",
    scheduled_at: "",
    description: "",
    patient_id: defaultPatientId || "",
  });

  const PATIENT_COLORS = [
    "#6c5ce7",
    "#00b894",
    "#e17055",
    "#0984e3",
    "#fdcb6e",
    "#d63031",
  ];

  useEffect(() => {
    if (!defaultPatientId) return;

    setSelectedPatientId((prev) => {
      if (prev) return prev;
      return isCaregiver ? "all" : String(defaultPatientId);
    });

    setFormData((prev) => ({
      ...prev,
      patient_id: prev.patient_id || defaultPatientId,
    }));
  }, [defaultPatientId, isCaregiver]);

  const readCookie = (name) => {
    if (typeof document === "undefined") return null;
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match ? decodeURIComponent(match[2]) : null;
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

  const loadSchedules = async () => {
    if (!normalizedPatients.length) {
      setSchedules([]);
      return;
    }

    setLoading(true);

    try {
      const responses = await Promise.all(
        normalizedPatients.map((patient) =>
          authFetch(`${API_PREFIX}/calendar/hospital?patient_id=${patient.id}`)
        )
      );

      const jsonList = await Promise.all(
        responses.map(async (res) => {
          if (!res.ok) {
            console.error("Failed to load schedules:", res.status);
            return { items: [] };
          }
          return res.json();
        })
      );

      const merged = jsonList.flatMap((data) => data.items || []);

      const dedupedMap = new Map();
      merged.forEach((item) => {
        dedupedMap.set(item.id, item);
      });

      const mergedSchedules = Array.from(dedupedMap.values()).sort(
        (a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at)
      );

      setSchedules(mergedSchedules);
    } catch (error) {
      console.error("Failed to load schedules:", error);
      setSchedules([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSchedules();
  }, [normalizedPatients]);

  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();

    const startingDayOfWeek = (firstDay.getDay() + 6) % 7;

    const days = [];

    for (let i = 0; i < startingDayOfWeek; i++) {
      const prevMonthDay = new Date(year, month, -startingDayOfWeek + i + 1);
      days.push({ date: prevMonthDay, isCurrentMonth: false });
    }

    for (let i = 1; i <= daysInMonth; i++) {
      days.push({ date: new Date(year, month, i), isCurrentMonth: true });
    }

    const remainingDays = 42 - days.length;
    for (let i = 1; i <= remainingDays; i++) {
      days.push({ date: new Date(year, month + 1, i), isCurrentMonth: false });
    }

    return days;
  };

  const filteredSchedules = useMemo(() => {
    if (selectedPatientId === "all") {
      return schedules;
    }

    if (!selectedPatientId) {
      return [];
    }

    return schedules.filter(
      (schedule) => schedule.patient_id === Number(selectedPatientId)
    );
  }, [schedules, selectedPatientId]);

  const getSchedulesForDate = (date) => {
    return filteredSchedules.filter((schedule) => {
      const scheduleDate = new Date(schedule.scheduled_at);

      return (
        scheduleDate.getFullYear() === date.getFullYear() &&
        scheduleDate.getMonth() === date.getMonth() &&
        scheduleDate.getDate() === date.getDate()
      );
    });
  };

  const getPatientName = (patientId) => {
    const patient = normalizedPatients.find((p) => p.id === Number(patientId));
    return patient?.name || `환자 ${patientId}`;
  };

  const getPatientColor = (patientId) => {
    const index = normalizedPatients.findIndex(
      (p) => p.id === Number(patientId)
    );

    if (index === -1) return "#6c5ce7";

    return PATIENT_COLORS[index % PATIENT_COLORS.length];
  };

  const handlePrevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const handleToday = () => {
    setCurrentDate(new Date());
  };

  const handleAddSchedule = () => {
    const targetPatientId =
      selectedPatientId === "all"
        ? defaultPatientId
        : Number(selectedPatientId);

    setSelectedSchedule(null);
    setFormData({
      title: "",
      hospital_name: "",
      location: "",
      scheduled_at: "",
      description: "",
      patient_id: targetPatientId || "",
    });
    setShowModal(true);
  };

  const handleEditSchedule = (schedule) => {
    setSelectedSchedule(schedule);
    setFormData({
      title: schedule.title || "",
      hospital_name: schedule.hospital_name || "",
      location: schedule.location || "",
      scheduled_at: schedule.scheduled_at ? schedule.scheduled_at.slice(0, 16) : "",
      description: schedule.description || "",
      patient_id: schedule.patient_id,
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      if (selectedSchedule) {
        const res = await authFetch(
          `${API_PREFIX}/calendar/hospital/${selectedSchedule.id}`,
          {
            method: "PATCH",
            body: JSON.stringify(formData),
          }
        );

        if (!res.ok) {
          console.error("Failed to update schedule:", res.status);
          return;
        }
      } else {
        const res = await authFetch(`${API_PREFIX}/calendar/hospital`, {
          method: "POST",
          body: JSON.stringify(formData),
        });

        if (!res.ok) {
          console.error("Failed to create schedule:", res.status);
          return;
        }
      }

      await loadSchedules();
      setShowModal(false);
    } catch (error) {
      console.error("Failed to save schedule:", error);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("일정을 삭제하시겠습니까?")) return;

    try {
      const res = await authFetch(`${API_PREFIX}/calendar/hospital/${id}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        console.error("Failed to delete schedule:", res.status);
        return;
      }

      await loadSchedules();
    } catch (error) {
      console.error("Failed to delete schedule:", error);
    }
  };

  const days = getDaysInMonth(currentDate);
  const monthYear = currentDate.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
  });

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
              <a className="btn btn-outline-light btn-sm" href="/auth-demo/app">
                대시보드
              </a>
              <a className="btn btn-outline-light btn-sm" href="/auth-demo/app/caregiver">
                보호자 모드
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
                <h5 className="fw-bold mb-3">복약관리시스템</h5>
                <div className="list-group list-group-flush">
                  <a
                    href="/auth-demo/app/dashboard"
                    className="list-group-item list-group-item-action"
                  >
                    대시보드
                  </a>
                  <a
                    href="/auth-demo/app/health-profile"
                    className="list-group-item list-group-item-action"
                  >
                    처방전 업로드
                  </a>
                  <a
                    href="/auth-demo/app/documents"
                    className="list-group-item list-group-item-action"
                  >
                    맞춤 복약 가이드
                  </a>
                  <a
                    href="/auth-demo/app/caregiver"
                    className="list-group-item list-group-item-action"
                  >
                    알림 센터
                  </a>
                  <a
                    href="/auth-demo/app/schedule"
                    className="list-group-item list-group-item-action active"
                  >
                    스케줄
                  </a>
                  <a
                    href="/auth-demo/app/profile"
                    className="list-group-item list-group-item-action"
                  >
                    건강 프로필
                  </a>
                </div>
              </div>
            </div>

            <div className="card border-0 shadow-sm">
              <div className="card-body">
                {isCaregiver && (
                  <div className="mb-3">
                    <label className="form-label fw-semibold">환자 선택</label>
                    <select
                      className="form-select"
                      value={selectedPatientId}
                      onChange={(e) => setSelectedPatientId(e.target.value)}
                      disabled={!normalizedPatients.length}
                    >
                      <option value="all">모두 보기</option>
                      {normalizedPatients.map((patient) => (
                        <option key={patient.id} value={String(patient.id)}>
                          {patient.name} ({patient.id})
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <button
                  className="btn btn-primary w-100 mb-3"
                  onClick={handleAddSchedule}
                  disabled={!normalizedPatients.length}
                >
                  + Add New Event
                </button>

                <h6 className="fw-bold mb-3">스케줄 요약 정보</h6>
                <div className="small text-muted">
                  {isCaregiver
                    ? selectedPatientId === "all"
                      ? `전체 환자의 등록된 병원 진료 예약 ${filteredSchedules.length}건`
                      : `선택한 환자의 등록된 병원 진료 예약 ${filteredSchedules.length}건`
                    : `내 등록된 병원 진료 예약 ${filteredSchedules.length}건`}
                </div>

                {filteredSchedules.slice(0, 3).map((schedule) => (
                  <div
                    key={schedule.id}
                    className="border-start border-3 border-primary ps-3 py-2 mt-2"
                  >
                    <div className="d-flex align-items-start">
                      <div className="flex-grow-1">
                        <div className="fw-semibold">{schedule.title}</div>
                        {isCaregiver && (
                          <div className="small text-muted">
                            {getPatientName(schedule.patient_id)}
                          </div>
                        )}
                        <div className="small text-muted">{schedule.hospital_name || "-"}</div>
                        <div className="small text-muted">{schedule.location || "-"}</div>
                        <div className="small text-muted">
                          {new Date(schedule.scheduled_at).toLocaleString("ko-KR")}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {!loading && filteredSchedules.length === 0 && (
                  <div className="small text-muted mt-3">등록된 일정이 없습니다.</div>
                )}
              </div>
            </div>
          </div>

          <div className="col-md-9">
            <div className="card border-0 shadow-sm">
              <div className="card-body">
                <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
                  <h4 className="fw-bold mb-0">스케줄</h4>

                  <div className="d-flex align-items-center gap-2 flex-wrap">
                    <button className="btn btn-sm btn-outline-secondary" onClick={handleToday}>
                      Today
                    </button>
                    <button className="btn btn-sm btn-outline-secondary" onClick={handlePrevMonth}>
                      &lt;
                    </button>
                    <span className="fw-semibold">{monthYear}</span>
                    <button className="btn btn-sm btn-outline-secondary" onClick={handleNextMonth}>
                      &gt;
                    </button>

                    <div className="btn-group" role="group">
                      <button
                        className={`btn btn-sm ${
                          viewMode === "day" ? "btn-primary" : "btn-outline-secondary"
                        }`}
                        onClick={() => setViewMode("day")}
                      >
                        Day
                      </button>
                      <button
                        className={`btn btn-sm ${
                          viewMode === "week" ? "btn-primary" : "btn-outline-secondary"
                        }`}
                        onClick={() => setViewMode("week")}
                      >
                        Week
                      </button>
                      <button
                        className={`btn btn-sm ${
                          viewMode === "month" ? "btn-primary" : "btn-outline-secondary"
                        }`}
                        onClick={() => setViewMode("month")}
                      >
                        Month
                      </button>
                    </div>
                  </div>
                </div>

                {loading ? (
                  <div className="text-center py-5">
                    <div className="spinner-border" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                  </div>
                ) : (
                  <div className="calendar-grid">
                    <div
                      className="row g-0 border-bottom fw-semibold text-center"
                      style={{ backgroundColor: "#f8f9fa" }}
                    >
                      <div className="col p-2">MON</div>
                      <div className="col p-2">TUE</div>
                      <div className="col p-2">WED</div>
                      <div className="col p-2">THU</div>
                      <div className="col p-2">FRI</div>
                      <div className="col p-2">SAT</div>
                      <div className="col p-2">SUN</div>
                    </div>

                    {Array.from({ length: 6 }).map((_, weekIndex) => (
                      <div
                        key={weekIndex}
                        className="row g-0 border-bottom"
                        style={{ minHeight: "110px" }}
                      >
                        {days.slice(weekIndex * 7, (weekIndex + 1) * 7).map((day, dayIndex) => {
                          const daySchedules = getSchedulesForDate(day.date);

                          return (
                            <div
                              key={dayIndex}
                              className={`col border-end p-2 ${
                                !day.isCurrentMonth ? "text-muted" : ""
                              }`}
                              style={{
                                backgroundColor: day.isCurrentMonth ? "#fff" : "#f8f9fa",
                              }}
                            >
                              <div className="text-end small mb-1">{day.date.getDate()}</div>

                              {daySchedules.map((schedule) => (
                                <div
                                  key={schedule.id}
                                  className="small p-1 mb-1 rounded text-white"
                                  style={{
                                    backgroundColor: getPatientColor(schedule.patient_id),
                                    cursor: "pointer",
                                  }}
                                  onClick={() => handleEditSchedule(schedule)}
                                  title={`${getPatientName(schedule.patient_id)} / ${schedule.title}`}
                                >
                                  {isCaregiver && selectedPatientId === "all"
                                    ? `[${getPatientName(schedule.patient_id)}] ${schedule.title}`
                                    : schedule.title}
                                </div>
                              ))}
                            </div>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {showModal && (
        <div className="modal show d-block" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">{selectedSchedule ? "일정 수정" : "일정 추가"}</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowModal(false)}
                ></button>
              </div>

              <form onSubmit={handleSubmit}>
                <div className="modal-body">
                  {isCaregiver && (
                    <div className="mb-3">
                      <label className="form-label">환자</label>
                      <select
                        className="form-select"
                        value={formData.patient_id}
                        onChange={(e) =>
                          setFormData({ ...formData, patient_id: Number(e.target.value) })
                        }
                        required
                      >
                        {normalizedPatients.map((patient) => (
                          <option key={patient.id} value={patient.id}>
                            {patient.name} ({patient.id})
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="mb-3">
                    <label className="form-label">제목</label>
                    <input
                      type="text"
                      className="form-control"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      required
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label">병원명</label>
                    <input
                      type="text"
                      className="form-control"
                      value={formData.hospital_name}
                      onChange={(e) =>
                        setFormData({ ...formData, hospital_name: e.target.value })
                      }
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label">장소</label>
                    <input
                      type="text"
                      className="form-control"
                      value={formData.location}
                      onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label">예약 일시</label>
                    <input
                      type="datetime-local"
                      className="form-control"
                      value={formData.scheduled_at}
                      onChange={(e) =>
                        setFormData({ ...formData, scheduled_at: e.target.value })
                      }
                      required
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label">메모</label>
                    <textarea
                      className="form-control"
                      rows="3"
                      value={formData.description}
                      onChange={(e) =>
                        setFormData({ ...formData, description: e.target.value })
                      }
                    ></textarea>
                  </div>
                </div>

                <div className="modal-footer">
                  {selectedSchedule && (
                    <button
                      type="button"
                      className="btn btn-danger me-auto"
                      onClick={async () => {
                        await handleDelete(selectedSchedule.id);
                        setShowModal(false);
                      }}
                    >
                      삭제
                    </button>
                  )}

                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setShowModal(false)}
                  >
                    취소
                  </button>

                  <button type="submit" className="btn btn-primary">
                    {selectedSchedule ? "수정" : "추가"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SchedulePage;