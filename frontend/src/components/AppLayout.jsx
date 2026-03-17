import React, { useMemo } from "react";

const BASE_MENU = [
  { key: "home", label: "홈", href: "/auth-demo/app" },
  { key: "documents", label: "처방전 업로드", href: "/auth-demo/app/documents" },
  { key: "ai", label: "AI 가이드", href: "/auth-demo/app/ai" },
  { key: "drug-search", label: "약 검색", href: "/auth-demo/app/drug-search" },
  { key: "caregiver", label: "알림센터", href: "/auth-demo/app/caregiver" },
  { key: "medication-check", label: "복약 체크", href: "/auth-demo/app/medication-check" },
  { key: "schedule", label: "스케줄", href: "/auth-demo/app/schedule" },
  { key: "health", label: "건강 프로필", href: "/auth-demo/app/health-profile" },
];

const handleLogout = async () => {
  try {
    await fetch("/api/v1/auth/logout", {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // 네트워크 오류가 있어도 로컬 인증 정보는 정리
  } finally {
    localStorage.removeItem("access_token");
    localStorage.removeItem("login_role");
    document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    document.cookie = "refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    window.location.href = "/auth-demo/login";
  }
};

function AppLayout({
  activeKey,
  title,
  description,
  children,
  loginRole,
  userName,
  modeOptions = [],
  currentMode,
  onModeChange,
}) {
  const normalizeMode = (role) => {
    if (!role) return "PATIENT";
    return role === "GUARDIAN" ? "CAREGIVER" : role;
  };
  const modeLabelMap = {
    PATIENT: "복약자모드",
    CAREGIVER: "보호자모드",
    ADMIN: "관리자모드",
  };
  const resolvedLoginRole = normalizeMode(loginRole || localStorage.getItem("login_role") || "PATIENT");
  const resolvedUserName = userName || "사용자";
  const profileInitial = resolvedUserName?.trim()?.[0] || "U";
  const normalizedModeOptions = (Array.isArray(modeOptions) ? modeOptions : [])
    .map((option) => ({
      value: normalizeMode(option.value),
      label: option.label || modeLabelMap[normalizeMode(option.value)] || `${normalizeMode(option.value)}모드`,
    }))
    .filter((option, index, list) => option.value && list.findIndex((item) => item.value === option.value) === index);
  const effectiveModeOptions =
    normalizedModeOptions.length > 0
      ? normalizedModeOptions
      : [{ value: resolvedLoginRole, label: modeLabelMap[resolvedLoginRole] || `${resolvedLoginRole}모드` }];
  const effectiveCurrentMode = normalizeMode(currentMode || resolvedLoginRole);
  const sidebarModeLabel =
    effectiveModeOptions.find((option) => option.value === effectiveCurrentMode)?.label ||
    modeLabelMap[effectiveCurrentMode] ||
    `${effectiveCurrentMode}모드`;
  const canSwitchMode = typeof onModeChange === "function" && effectiveModeOptions.length > 1;

  const menuItems = useMemo(() => {
    if (effectiveCurrentMode === "ADMIN") {
      return [
        ...BASE_MENU,
        { key: "admin-dashboard", label: "관리자 대시보드", href: "/auth-demo/app/dashboard" },
      ];
    }
    return BASE_MENU;
  }, [effectiveCurrentMode]);

  return (
    <div className="doc-layout">
      <aside className="doc-sidebar">
        <div className="doc-sidebar-brand">
          <strong>복약관리시스템</strong>
          <div className="text-muted small">{sidebarModeLabel}</div>
        </div>
        <nav className="doc-sidebar-nav">
          {menuItems.map((item) => (
            <a
              key={item.key}
              className={`doc-sidebar-link ${item.key === activeKey ? "active" : ""}`}
              href={item.href}
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="doc-sidebar-footer">
          <a className={`doc-sidebar-link ${activeKey === "settings" ? "active" : ""}`} href="/auth-demo/app/settings">
            설정
          </a>
        </div>
      </aside>

      <main className="doc-main">
        <header className="app-page-header">
          <div>
            <h2 className="app-page-title">{title}</h2>
            {description && <p className="app-page-description">{description}</p>}
          </div>
          <div className="app-page-actions">
            <div className="app-selector-group">
              <label className="app-selector-label">현재 모드</label>
              <select
                className="form-select form-select-sm app-patient-select"
                value={effectiveCurrentMode}
                onChange={(event) => onModeChange?.(event.target.value)}
                disabled={!canSwitchMode}
              >
                {effectiveModeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <a className="app-profile-button" href="/auth-demo/app/profile" title="프로필">
              {profileInitial}
            </a>
            <button className="btn btn-outline-secondary btn-sm" type="button" onClick={handleLogout}>
              로그아웃
            </button>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

export default AppLayout;
