import React, { useEffect, useState } from "react";

const API_PREFIX = "/api/v1";

const StatCard = ({ icon, title, value, change, isNegative }) => (
  <div className="col-md-6 col-lg">
    <div className="card border-0 shadow-sm h-100">
      <div className="card-body">
        <div className="d-flex align-items-center mb-2">
          <div className="text-primary me-2">{icon}</div>
          <div className="text-muted small">{title}</div>
        </div>
        <div className="h3 fw-bold mb-1">{value}</div>
        <div className={`small ${isNegative ? "text-danger" : "text-success"}`}>
          {isNegative ? "▼" : "▲"} {Math.abs(change)}% 전일 대비
        </div>
      </div>
    </div>
  </div>
);

const LineChart = ({ title, data }) => {
  const maxValue = Math.max(...data.map((d) => d.value), 1);
  const minValue = Math.min(...data.map((d) => d.value), 0);
  const range = maxValue - minValue || 1;

  return (
    <div className="card border-0 shadow-sm h-100">
      <div className="card-body">
        <h6 className="fw-semibold mb-4">{title}</h6>
        <div style={{ position: "relative", height: "200px" }}>
          <svg width="100%" height="100%" viewBox="0 0 700 200" preserveAspectRatio="none">
            <polyline
              fill="none"
              stroke={title.includes("가이드") ? "#2563eb" : "#10b981"}
              strokeWidth="3"
              points={data
                .map((d, i) => {
                  const x = (i / (data.length - 1)) * 700;
                  const y = 180 - ((d.value - minValue) / range) * 160;
                  return `${x},${y}`;
                })
                .join(" ")}
            />
            {data.map((d, i) => {
              const x = (i / (data.length - 1)) * 700;
              const y = 180 - ((d.value - minValue) / range) * 160;
              return (
                <circle
                  key={i}
                  cx={x}
                  cy={y}
                  r="5"
                  fill={title.includes("가이드") ? "#2563eb" : "#10b981"}
                />
              );
            })}
          </svg>
          <div className="d-flex justify-content-between mt-2 small text-muted">
            {data.map((d, i) => (
              <span key={i}>{d.date.slice(5)}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const DonutChart = ({ successRate }) => {
  const successAngle = (successRate / 100) * 360;
  const failureAngle = 360 - successAngle;

  return (
    <svg width="200" height="200" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="80" fill="none" stroke="#e5e7eb" strokeWidth="40" />
      <circle
        cx="100"
        cy="100"
        r="80"
        fill="none"
        stroke="#3b82f6"
        strokeWidth="40"
        strokeDasharray={`${(successAngle / 360) * 502.65} 502.65`}
        transform="rotate(-90 100 100)"
      />
      <circle
        cx="100"
        cy="100"
        r="80"
        fill="none"
        stroke="#ef4444"
        strokeWidth="40"
        strokeDasharray={`${(failureAngle / 360) * 502.65} 502.65`}
        strokeDashoffset={`-${(successAngle / 360) * 502.65}`}
        transform="rotate(-90 100 100)"
      />
    </svg>
  );
};

function AdminDashboard() {
  const [period, setPeriod] = useState(7);
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    window.location.href = "/auth-demo/login";
  };

  const fetchDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_PREFIX}/dashboard?period=${period}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error(`status ${res.status}`);
      }
      const data = await res.json();
      setDashboardData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [period]);

  if (loading) {
    return (
      <div className="container py-5">
        <div className="text-center text-muted">데이터 로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container py-5">
        <div className="alert alert-danger">오류: {error}</div>
      </div>
    );
  }

  if (!dashboardData) {
    return null;
  }

  const { stats, guide_trend, chatbot_trend, ocr_analysis } = dashboardData;

  return (
    <div className="container-fluid py-4" style={{ backgroundColor: "#f8f9fa", minHeight: "100vh" }}>
      <nav className="navbar navbar-expand-lg navbar-light bg-white shadow-sm mb-4">
        <div className="container-fluid">
          <a className="navbar-brand fw-bold" href="/auth-demo/app">AI Health</a>
          <div className="ms-auto d-flex gap-2">
            <a className="btn btn-outline-primary btn-sm" href="/auth-demo/app">홈</a>
            <a className="btn btn-outline-primary btn-sm" href="/auth-demo/app/profile">개인정보</a>
            <button className="btn btn-outline-danger btn-sm" onClick={handleLogout}>로그아웃</button>
          </div>
        </div>
      </nav>

      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-1">대시보드</h2>
          <h4 className="text-muted">관리자 대시보드</h4>
        </div>
        <div className="btn-group">
          <button
            className={`btn ${period === 7 ? "btn-primary" : "btn-outline-secondary"}`}
            onClick={() => setPeriod(7)}
          >
            7일
          </button>
          <button
            className={`btn ${period === 30 ? "btn-primary" : "btn-outline-secondary"}`}
            onClick={() => setPeriod(30)}
          >
            30일
          </button>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <StatCard
          icon="👥"
          title="총 사용자 수"
          value={stats.total_users.toLocaleString()}
          change={stats.total_users_change}
          isNegative={stats.total_users_change < 0}
        />
        <StatCard
          icon="📄"
          title="오늘 가이드 생성"
          value={stats.today_guides}
          change={stats.today_guides_change}
          isNegative={stats.today_guides_change < 0}
        />
        <StatCard
          icon="✓"
          title="OCR 성공률"
          value={`${stats.ocr_success_rate}%`}
          change={stats.ocr_success_rate_change}
          isNegative={stats.ocr_success_rate_change < 0}
        />
        <StatCard
          icon="💬"
          title="오늘 챗봇 요청"
          value={stats.today_chatbot_requests}
          change={stats.today_chatbot_requests_change}
          isNegative={stats.today_chatbot_requests_change < 0}
        />
        <StatCard
          icon="⚠"
          title="시스템 에러"
          value={stats.system_errors}
          change={stats.system_errors_change}
          isNegative={stats.system_errors_change > 0}
        />
      </div>

      <div className="row g-4 mb-4">
        <div className="col-lg-6">
          <LineChart title="가이드 생성 추이" data={guide_trend} />
        </div>
        <div className="col-lg-6">
          <LineChart title="챗봇 요청 추이" data={chatbot_trend} />
        </div>
      </div>

      <div className="card border-0 shadow-sm">
        <div className="card-body">
          <h5 className="fw-semibold mb-4">OCR 성능 분석</h5>
          <div className="row">
            <div className="col-lg-5 text-center">
              <DonutChart successRate={ocr_analysis.success_rate} />
            </div>
            <div className="col-lg-7">
              <div className="mb-3">
                <div className="d-flex justify-content-between mb-1">
                  <span className="text-muted">총 처리 건수</span>
                  <span className="fw-bold">{ocr_analysis.total_processed.toLocaleString()}</span>
                </div>
                <div className="d-flex justify-content-between mb-1">
                  <span className="text-muted">성공 건수</span>
                  <span className="fw-bold text-primary">{ocr_analysis.success_count.toLocaleString()}</span>
                </div>
                <div className="d-flex justify-content-between mb-1">
                  <span className="text-muted">실패 건수</span>
                  <span className="fw-bold text-danger">{ocr_analysis.failure_count}</span>
                </div>
                <div className="d-flex justify-content-between mb-3">
                  <span className="text-muted">성공률</span>
                  <span className="fw-bold">{ocr_analysis.success_rate}%</span>
                </div>
              </div>
              <div>
                <h6 className="fw-semibold mb-2">실패 사유 Top 3</h6>
                {ocr_analysis.top_failures.map(([reason, count], idx) => (
                  <div key={idx} className="d-flex justify-content-between mb-1">
                    <span>
                      {idx + 1}. {reason}
                    </span>
                    <span className="fw-semibold">{count}건</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AdminDashboard;
