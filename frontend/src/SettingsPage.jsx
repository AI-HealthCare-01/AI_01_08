import React, { useEffect, useState } from "react";

const API_PREFIX = "/api/v1";

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    dark_mode: false,
    language: "ko",
    push_notifications: true
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const readCookie = (name) => {
    if (typeof document === "undefined") return null;
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match ? decodeURIComponent(match[2]) : null;
  };

  const accessToken = typeof window !== "undefined" 
    ? window.localStorage.getItem("access_token") || readCookie("access_token")
    : null;

  const authFetch = async (path, options = {}) => {
    const headers = new Headers(options.headers || {});
    if (!headers.has("Content-Type") && options.body) {
      headers.set("Content-Type", "application/json");
    }
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
    return fetch(path, { ...options, headers, credentials: "include" });
  };

  const loadSettings = async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API_PREFIX}/settings`);
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      }
    } catch (error) {
      console.error("Failed to load settings:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleToggle = async (key) => {
    const newValue = !settings[key];
    setSettings({ ...settings, [key]: newValue });
    
    setSaving(true);
    try {
      const res = await authFetch(`${API_PREFIX}/settings`, {
        method: "PATCH",
        body: JSON.stringify({ [key]: newValue })
      });
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      }
    } catch (error) {
      console.error("Failed to update settings:", error);
      setSettings({ ...settings, [key]: !newValue });
    } finally {
      setSaving(false);
    }
  };

  const handleLanguageChange = async (e) => {
    const newLanguage = e.target.value;
    setSettings({ ...settings, language: newLanguage });
    
    setSaving(true);
    try {
      const res = await authFetch(`${API_PREFIX}/settings`, {
        method: "PATCH",
        body: JSON.stringify({ language: newLanguage })
      });
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      }
    } catch (error) {
      console.error("Failed to update language:", error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="container py-4">
          <nav className="navbar navbar-expand-lg">
            <a className="navbar-brand fw-bold" href="/auth-demo/app" style={{ fontSize: "1.5rem" }}>
              복약관리시스템
            </a>
            <div className="ms-auto d-flex gap-2">
              <a className="btn btn-outline-light btn-sm" href="/auth-demo/app">대시보드</a>
              <a className="btn btn-outline-light btn-sm" href="/auth-demo/app/profile">개인정보</a>
            </div>
          </nav>
        </div>
      </header>

      <div className="container-fluid py-4">
        <div className="row">
          <div className="col-md-3">
            <div className="card border-0 shadow-sm">
              <div className="card-body">
                <h5 className="fw-bold mb-3 text-primary">복약관리시스템<br/>보호자 모드</h5>
                <div className="list-group list-group-flush">
                  <a href="/auth-demo/app/dashboard" className="list-group-item list-group-item-action">대시보드</a>
                  <a href="/auth-demo/app/health-profile" className="list-group-item list-group-item-action">처방전 업로드</a>
                  <a href="/auth-demo/app/documents" className="list-group-item list-group-item-action">맞춤 복약 가이드</a>
                  <a href="/auth-demo/app/caregiver" className="list-group-item list-group-item-action">알림 센터</a>
                  <a href="/auth-demo/app/schedule" className="list-group-item list-group-item-action">스케줄</a>
                  <a href="/auth-demo/app/profile" className="list-group-item list-group-item-action">건강 프로필</a>
                </div>
                <hr />
                <button className="btn btn-primary w-100 mb-2">settings</button>
                <button className="btn btn-outline-secondary w-100">Logout</button>
              </div>
            </div>
          </div>

          <div className="col-md-9">
            <div className="card border-0 shadow-sm">
              <div className="card-body">
                <h4 className="fw-bold mb-4">설정</h4>

                {loading ? (
                  <div className="text-center py-5">
                    <div className="spinner-border" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                  </div>
                ) : (
                  <>
                    {/* 개정 설정 */}
                    <div className="mb-4">
                      <h6 className="fw-semibold mb-3">개정 설정</h6>
                      
                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#e3f2fd", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-person" style={{ fontSize: "20px", color: "#2196f3" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">내 정보 수정</div>
                            <div className="small text-muted">이름, 전화번호, 이메일 등을 업데이트 하십니다</div>
                          </div>
                          <i className="bi bi-chevron-right text-muted"></i>
                        </div>
                      </div>

                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#e3f2fd", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-lock" style={{ fontSize: "20px", color: "#2196f3" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">비밀번호 변경</div>
                            <div className="small text-muted">계정 보안을 위해 주기적으로 변경하세요</div>
                          </div>
                          <i className="bi bi-chevron-right text-muted"></i>
                        </div>
                      </div>

                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#fff3e0", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-box-arrow-right" style={{ fontSize: "20px", color: "#ff9800" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">로그아웃</div>
                            <div className="small text-muted">현재 계정에서 로그아웃합니다</div>
                          </div>
                          <i className="bi bi-chevron-right text-muted"></i>
                        </div>
                      </div>

                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#ffebee", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-person-x" style={{ fontSize: "20px", color: "#f44336" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold text-danger">회원 탈퇴</div>
                            <div className="small text-muted">계정 및 모든 데이터가 삭제됩니다</div>
                          </div>
                          <i className="bi bi-chevron-right text-muted"></i>
                        </div>
                      </div>
                    </div>

                    {/* 앱 설정 */}
                    <div className="mb-4">
                      <h6 className="fw-semibold mb-3">앱 설정</h6>
                      
                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#f3e5f5", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-moon" style={{ fontSize: "20px", color: "#9c27b0" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">다크 모드</div>
                            <div className="small text-muted">야간은 테마로 변경합니다</div>
                          </div>
                          <div className="form-check form-switch">
                            <input
                              className="form-check-input"
                              type="checkbox"
                              role="switch"
                              checked={settings.dark_mode}
                              onChange={() => handleToggle("dark_mode")}
                              disabled={saving}
                              style={{ width: "48px", height: "24px" }}
                            />
                          </div>
                        </div>
                      </div>

                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#e8f5e9", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-globe" style={{ fontSize: "20px", color: "#4caf50" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">언어 설정</div>
                            <div className="small text-muted">앱에서 사용할 언어를 선택하세요</div>
                          </div>
                          <select
                            className="form-select form-select-sm"
                            style={{ width: "120px" }}
                            value={settings.language}
                            onChange={handleLanguageChange}
                            disabled={saving}
                          >
                            <option value="ko">한국어</option>
                            <option value="en">English</option>
                            <option value="ja">日本語</option>
                          </select>
                        </div>
                      </div>

                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#fff3e0", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-bell" style={{ fontSize: "20px", color: "#ff9800" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">알림 설정</div>
                            <div className="small text-muted">복약 알림 및 건강 정보 알림을 받습니다</div>
                          </div>
                          <div className="form-check form-switch">
                            <input
                              className="form-check-input"
                              type="checkbox"
                              role="switch"
                              checked={settings.push_notifications}
                              onChange={() => handleToggle("push_notifications")}
                              disabled={saving}
                              style={{ width: "48px", height: "24px" }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 서비스 정보 */}
                    <div className="mb-4">
                      <h6 className="fw-semibold mb-3">서비스 정보</h6>
                      
                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#e3f2fd", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-file-text" style={{ fontSize: "20px", color: "#2196f3" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">약관 보기</div>
                            <div className="small text-muted">서비스 이용약관을 확인합니다</div>
                          </div>
                          <i className="bi bi-chevron-right text-muted"></i>
                        </div>
                      </div>

                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#e8f5e9", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-shield-check" style={{ fontSize: "20px", color: "#4caf50" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">개인정보 처리방침</div>
                            <div className="small text-muted">개인정보 보호 정책을 확인합니다</div>
                          </div>
                          <i className="bi bi-chevron-right text-muted"></i>
                        </div>
                      </div>

                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#f3e5f5", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-info-circle" style={{ fontSize: "20px", color: "#9c27b0" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">버전 정보</div>
                            <div className="small text-muted">현재 앱 버전</div>
                          </div>
                          <span className="badge bg-primary">v1.0.0</span>
                        </div>
                      </div>
                    </div>

                    {/* 연동 관리 */}
                    <div className="mb-4">
                      <h6 className="fw-semibold mb-3">연동 관리</h6>
                      
                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#e3f2fd", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-people" style={{ fontSize: "20px", color: "#2196f3" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">초대코드로 연동하기</div>
                            <div className="small text-muted">환자 또는 보호자를 초대코드로 연결합니다</div>
                          </div>
                          <i className="bi bi-chevron-right text-muted"></i>
                        </div>
                      </div>

                      <div className="card mb-2">
                        <div className="card-body d-flex align-items-center">
                          <div className="me-3" style={{ width: "40px", height: "40px", backgroundColor: "#e8f5e9", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <i className="bi bi-link-45deg" style={{ fontSize: "20px", color: "#4caf50" }}></i>
                          </div>
                          <div className="flex-grow-1">
                            <div className="fw-semibold">연동 관리</div>
                            <div className="small text-muted">연결된 환자 및 보호자를 관리합니다</div>
                          </div>
                          <i className="bi bi-chevron-right text-muted"></i>
                        </div>
                      </div>
                    </div>

                    <div className="text-center text-muted small mt-5">
                      © 2026 Healthcare Dashboard. All rights reserved.
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
