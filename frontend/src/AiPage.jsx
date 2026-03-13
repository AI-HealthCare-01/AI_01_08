import React, { useEffect, useState } from "react";

const API_PREFIX = "/api/v1";

const safeJson = async (res) => {
  try {
    return await res.json();
  } catch {
    return null;
  }
};

const formatDateTime = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
};

const formatApiError = (value) => {
  if (!value) return "알 수 없는 오류가 발생했습니다.";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value.map((item) => item?.msg || JSON.stringify(item)).join(", ");
  }
  if (typeof value === "object") {
    if (value.detail) return formatApiError(value.detail);
    if (value.message) return formatApiError(value.message);
    return JSON.stringify(value);
  }
  return String(value);
};

function AiPage() {
  const readCookie = (name) => {
    if (typeof document === "undefined") return null;
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match ? decodeURIComponent(match[2]) : null;
  };

  const [accessToken, setAccessToken] = useState(() => {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem("access_token") || readCookie("access_token");
  });

  const [loginRole, setLoginRole] = useState(() => {
    if (typeof window === "undefined") return "PATIENT";
    return window.localStorage.getItem("login_role") || "PATIENT";
  });

  const [meState, setMeState] = useState({
    loading: false,
    data: null,
    error: null
  });

  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatContainerRef = React.useRef(null);

  // 챗 메시지가 추가될 때마다 스크롤 하단으로 이동
  React.useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatMessages, chatLoading]);

  const [inviteState, setInviteState] = useState({
    submitting: false,
    error: null,
    data: null
  });

  const [inviteCodeForm, setInviteCodeForm] = useState({
    expires_in_minutes: 10080
  });

  const [linkForm, setLinkForm] = useState({
    code: ""
  });

  const [linksState, setLinksState] = useState({
    loading: false,
    data: null,
    error: null
  });

  const [linkAction, setLinkAction] = useState({
    submitting: false,
    error: null,
    success: null
  });

  const refreshAccessToken = async () => {
    const res = await fetch(`${API_PREFIX}/auth/token/refresh`, {
      method: "GET",
      credentials: "include"
    });
    if (!res.ok) return null;
    const body = await safeJson(res);
    const token = body?.access_token;
    if (token) {
      if (typeof window !== "undefined") {
        window.localStorage.setItem("access_token", token);
      }
      setAccessToken(token);
    }
    return token || null;
  };

  const authFetch = async (path, options = {}, retryOnUnauthorized = true) => {
    const headers = new Headers(options.headers || {});
    if (!headers.has("Content-Type") && options.body) {
      headers.set("Content-Type", "application/json");
    }
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
    const res = await fetch(path, {
      ...options,
      headers,
      credentials: "include"
    });
    if (res.status === 401 && retryOnUnauthorized) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        headers.set("Authorization", `Bearer ${newToken}`);
        return fetch(path, {
          ...options,
          headers,
          credentials: "include"
        });
      }
    }
    return res;
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_PREFIX}/auth/logout`, { method: "POST", credentials: "include" });
    } catch {
      // ignore
    } finally {
      if (typeof window !== "undefined") {
        window.localStorage.removeItem("access_token");
        window.location.href = "/auth-demo/login";
      }
    }
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim() || chatLoading) return;

    const userMessage = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setChatLoading(true);

    try {
      console.log("Sending message to AI...", userMessage);
      const res = await authFetch(`${API_PREFIX}/ai-chat`, {
        method: "POST",
        body: JSON.stringify({
          message: userMessage,
          patient_context: meState.data ? `이름: ${meState.data.name}, 역할: ${loginRole}` : null
        })
      });

      console.log("Response status:", res.status);

      if (!res.ok) {
        const body = await safeJson(res);
        console.error("API Error:", body);
        throw new Error(formatApiError(body) || `HTTP ${res.status}`);
      }

      const data = await res.json();
      console.log("AI Response:", data);
      setChatMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage = error?.message || String(error);
      setChatMessages((prev) => [
        ...prev,
        { 
          role: "assistant", 
          content: `죄송합니다. 오류가 발생했습니다: ${errorMessage}\n\n다시 시도해주세요.` 
        }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  useEffect(() => {
    if (!accessToken) return;

    const loadMe = async () => {
      setMeState({ loading: true, data: null, error: null });
      try {
        const res = await authFetch(`${API_PREFIX}/users/me`);
        if (!res.ok) {
          const body = await safeJson(res);
          throw new Error(body?.detail || `status ${res.status}`);
        }
        const data = await res.json();
        setMeState({ loading: false, data, error: null });
      } catch (error) {
        setMeState({ loading: false, data: null, error: error.message });
      }
    };

    const loadLinks = async () => {
      setLinksState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const res = await authFetch(`${API_PREFIX}/users/links`);
        if (!res.ok) {
          const body = await safeJson(res);
          throw new Error(body?.detail || `status ${res.status}`);
        }
        const data = await res.json();
        setLinksState({ loading: false, data, error: null });
      } catch (error) {
        setLinksState({ loading: false, data: null, error: error.message });
      }
    };

    loadMe();
    loadLinks();
  }, [accessToken]);

  const createInviteCode = async () => {
    setInviteState({ submitting: true, error: null, data: null });
    try {
      const payload = {
        expires_in_minutes: Number(inviteCodeForm.expires_in_minutes) || 10080
      };
      const res = await authFetch(`${API_PREFIX}/users/invite-code`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      const data = await res.json();
      setInviteState({ submitting: false, error: null, data });
    } catch (error) {
      setInviteState({ submitting: false, error: formatApiError(error?.message || error), data: null });
    }
  };

  const deleteInviteCode = async () => {
    try {
      const res = await authFetch(`${API_PREFIX}/users/invite-code`, { method: "DELETE" });
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      setInviteState((prev) => ({ ...prev, data: null }));
    } catch (error) {
      alert(formatApiError(error?.message || error));
    }
  };

  const linkByInviteCode = async (event) => {
    event.preventDefault();
    setLinkAction({ submitting: true, error: null, success: null });
    try {
      const payload = { code: linkForm.code };
      const res = await authFetch(`${API_PREFIX}/users/link`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      await res.json();
      setLinkAction({ submitting: false, error: null, success: "연동 완료" });
      const reload = await authFetch(`${API_PREFIX}/users/links`);
      if (reload.ok) {
        const data = await reload.json();
        setLinksState({ loading: false, data, error: null });
      }
    } catch (error) {
      setLinkAction({ submitting: false, error: formatApiError(error?.message || error), success: null });
    }
  };

  const unlinkPatient = async (linkId) => {
    setLinkAction({ submitting: true, error: null, success: null });
    try {
      const res = await authFetch(`${API_PREFIX}/users/links/${linkId}`, {
        method: "DELETE"
      });
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      await res.json();
      setLinkAction({ submitting: false, error: null, success: "연동 해제 완료" });
      const reload = await authFetch(`${API_PREFIX}/users/links`);
      if (reload.ok) {
        const data = await reload.json();
        setLinksState({ loading: false, data, error: null });
      }
    } catch (error) {
      setLinkAction({ submitting: false, error: formatApiError(error?.message || error), success: null });
    }
  };

  if (!accessToken) {
    if (typeof window !== "undefined") {
      window.location.href = "/auth-demo/login";
    }
    return null;
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      {/* 좌측 사이드바 */}
      <aside style={{ width: '240px', backgroundColor: '#fff', borderRight: '1px solid #e0e0e0', padding: '20px' }}>
        <div style={{ marginBottom: '30px' }}>
          <h5 style={{ color: '#4a90e2', fontSize: '16px', fontWeight: 'bold' }}>복약관리시스템</h5>
          <div style={{ fontSize: '14px', color: '#666' }}>보호자 모드</div>
        </div>
        
        <nav>
          <a href="/auth-demo/app/dashboard" style={{ display: 'block', padding: '12px 16px', color: '#333', textDecoration: 'none', borderRadius: '8px', marginBottom: '4px' }}>
            대시보드
          </a>
          <a href="/auth-demo/app/health-profile" style={{ display: 'block', padding: '12px 16px', color: '#333', textDecoration: 'none', borderRadius: '8px', marginBottom: '4px' }}>
            처방전 업로드
          </a>
          <a href="/auth-demo/app/ai" style={{ display: 'block', padding: '12px 16px', backgroundColor: '#4a90e2', color: '#fff', textDecoration: 'none', borderRadius: '8px', marginBottom: '4px', fontWeight: '600' }}>
            맞춤 복약 가이드
          </a>
          <a href="/auth-demo/app/caregiver" style={{ display: 'block', padding: '12px 16px', color: '#333', textDecoration: 'none', borderRadius: '8px', marginBottom: '4px' }}>
            알림센터
          </a>
          <a href="/auth-demo/app/documents" style={{ display: 'block', padding: '12px 16px', color: '#333', textDecoration: 'none', borderRadius: '8px', marginBottom: '4px' }}>
            스케줄
          </a>
          <a href="/auth-demo/app/profile" style={{ display: 'block', padding: '12px 16px', color: '#333', textDecoration: 'none', borderRadius: '8px', marginBottom: '4px' }}>
            건강 프로필
          </a>
        </nav>
        
        <div style={{ position: 'absolute', bottom: '20px', left: '20px', right: '20px' }}>
          <a href="#" style={{ display: 'block', padding: '12px 16px', color: '#333', textDecoration: 'none', borderRadius: '8px', marginBottom: '4px' }}>
            Settings
          </a>
          <a href="#" onClick={handleLogout} style={{ display: 'block', padding: '12px 16px', color: '#333', textDecoration: 'none', borderRadius: '8px' }}>
            Logout
          </a>
        </div>
      </aside>

      {/* 우측 메인 콘텐츠 */}
      <main style={{ flex: 1, padding: '40px' }}>
        {/* 헤더 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
          <h1 style={{ fontSize: '32px', fontWeight: 'bold', margin: 0 }}>AI 가이드</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img src="/mascot.png" alt="프로필" style={{ width: '40px', height: '40px', borderRadius: '50%' }} />
            <div>
              <div style={{ fontSize: '14px', fontWeight: '600' }}>{meState.data?.name || '옥영향'}</div>
              <div style={{ fontSize: '12px', color: '#666' }}>보호자</div>
            </div>
          </div>
        </div>

        {/* 메인 카드 */}
        <div style={{ backgroundColor: '#f0f4f8', padding: '40px', borderRadius: '12px', marginBottom: '40px' }}>
          <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '12px' }}>AI 복약 및 생활습관 가이드</h2>
          <p style={{ color: '#666', marginBottom: 0 }}>처방 정보를 바탕으로 AI가 생성한 맞춤형 가이드입니다.</p>
        </div>

        {/* 환자 요약 정보 */}
        <div style={{ backgroundColor: '#fff', padding: '30px', borderRadius: '12px', marginBottom: '30px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px' }}>환자 요약 정보</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
            <div style={{ padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
              <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>김영희</div>
              <div style={{ fontSize: '12px', color: '#999' }}>여성나 72세 여성</div>
              <div style={{ fontSize: '12px', color: '#999' }}>고혈압, 당뇨</div>
              <div style={{ fontSize: '12px', color: '#999', marginTop: '8px' }}>처방일 2026.02.20</div>
              <div style={{ fontSize: '12px', color: '#999' }}>처방 약품 3종</div>
              <div style={{ fontSize: '12px', color: '#999' }}>복용기간 00 일</div>
            </div>
            <div style={{ padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
              <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>이철수</div>
              <div style={{ fontSize: '12px', color: '#999' }}>여성나 75세 남성</div>
              <div style={{ fontSize: '12px', color: '#999' }}>고지혈증</div>
              <div style={{ fontSize: '12px', color: '#999', marginTop: '8px' }}>처방일 2026.01.05</div>
              <div style={{ fontSize: '12px', color: '#999' }}>처방 약품 2종</div>
              <div style={{ fontSize: '12px', color: '#999' }}>복용기간 00 일</div>
            </div>
            <div style={{ padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
              <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>박지민</div>
              <div style={{ fontSize: '12px', color: '#999' }}>남 5세 여성</div>
              <div style={{ fontSize: '12px', color: '#999' }}>특이</div>
              <div style={{ fontSize: '12px', color: '#999', marginTop: '8px' }}>처방일 2026.01.21</div>
              <div style={{ fontSize: '12px', color: '#999' }}>처방 약품 4종</div>
              <div style={{ fontSize: '12px', color: '#999' }}>복용기간 00 일</div>
            </div>
          </div>
          <button style={{ marginTop: '20px', padding: '8px 16px', backgroundColor: '#e0e0e0', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>See More</button>
        </div>

        {/* 복약안내 섹션 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '30px' }}>
          <div style={{ backgroundColor: '#fff', padding: '30px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px' }}>복약안내</h3>
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: '600' }}>아모디핀 5mg</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>고혈압 치료제</div>
                </div>
                <div style={{ fontSize: '12px', color: '#666' }}>주의사항</div>
              </div>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>복용 방법</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 아침 식후 30분 이내</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 물과 함께 복용</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 발치 말고 삼킬 것</div>
              <div style={{ fontSize: '12px', color: '#666', marginTop: '12px' }}>주의사항</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 자몽주스와 함께 복용 금지</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 어지러움 주의</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 갑자기 일어나지 말 것</div>
              <button style={{ marginTop: '16px', padding: '8px 24px', backgroundColor: '#e8f0fe', color: '#4a90e2', border: 'none', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}>1일 1회</button>
            </div>
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: '600' }}>아모디핀 5mg</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>고혈압 치료제</div>
                </div>
                <div style={{ fontSize: '12px', color: '#666' }}>주의사항</div>
              </div>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>복용 방법</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 아침 식후 30분 이내</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 물과 함께 복용</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 발치 말고 삼킬 것</div>
              <div style={{ fontSize: '12px', color: '#666', marginTop: '12px' }}>주의사항</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 자몽주스와 함께 복용 금지</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 어지러움 주의</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 갑자기 일어나지 말 것</div>
              <button style={{ marginTop: '16px', padding: '8px 24px', backgroundColor: '#e8f0fe', color: '#4a90e2', border: 'none', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}>1일 1회</button>
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: '600' }}>아모디핀 5mg</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>고혈압 치료제</div>
                </div>
                <div style={{ fontSize: '12px', color: '#666' }}>주의사항</div>
              </div>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>복용 방법</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 아침 식후 30분 이내</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 물과 함께 복용</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 발치 말고 삼킬 것</div>
              <div style={{ fontSize: '12px', color: '#666', marginTop: '12px' }}>주의사항</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 자몽주스와 함께 복용 금지</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 어지러움 주의</div>
              <div style={{ fontSize: '12px', color: '#333' }}>• 갑자기 일어나지 말 것</div>
              <button style={{ marginTop: '16px', padding: '8px 24px', backgroundColor: '#e8f0fe', color: '#4a90e2', border: 'none', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}>1일 1회</button>
            </div>
          </div>

          {/* 생활습관 가이드 */}
          <div style={{ backgroundColor: '#fff', padding: '30px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px' }}>생활습관 가이드</h3>
            <div style={{ marginBottom: '24px' }}>
              <h4 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>식이요법</h4>
              <div style={{ fontSize: '14px', color: '#333', marginBottom: '8px' }}>• 하루 염분 섭취량 5g 이하로 제한</div>
              <div style={{ fontSize: '14px', color: '#333', marginBottom: '8px' }}>• 당분이 많은 음식 피하기</div>
              <div style={{ fontSize: '14px', color: '#333', marginBottom: '8px' }}>• 채소와 과일 충분히 섭취</div>
              <div style={{ fontSize: '14px', color: '#333', marginBottom: '8px' }}>• 가공식품 섭취 줄이기</div>
              <div style={{ fontSize: '14px', color: '#333', marginBottom: '8px' }}>• 하루 수분 섭취 1.5L 이상</div>
            </div>
            <div style={{ position: 'relative', textAlign: 'right' }}>
              <img src="/mascot.png" alt="약속이" style={{ width: '100px', height: 'auto' }} />
            </div>
          </div>
        </div>

        {/* AI 챗봇 섹션 */}
        <div style={{ backgroundColor: '#fff', padding: '30px', borderRadius: '12px', marginTop: '30px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
            <img src="/mascot.png" alt="약속이" style={{ width: '50px', height: '50px', marginRight: '12px' }} />
            <h3 style={{ fontSize: '18px', fontWeight: 'bold', margin: 0 }}>AI 상담 - 약속이</h3>
          </div>
          <div ref={chatContainerRef} style={{ height: '400px', overflowY: 'auto', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '20px', marginBottom: '16px', backgroundColor: '#f9f9f9' }}>
            {chatMessages.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#999', paddingTop: '150px' }}>
                <div style={{ fontSize: '16px', marginBottom: '8px' }}>안녕하세요! 저는 약속이에요 👋</div>
                <div style={{ fontSize: '14px' }}>복약 관리와 건강에 대해 무엇이든 물어보세요!</div>
              </div>
            ) : (
              chatMessages.map((msg, idx) => (
                <div key={idx} style={{ marginBottom: '16px', display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                  <div style={{ 
                    maxWidth: '70%', 
                    padding: '12px 16px', 
                    borderRadius: '12px', 
                    backgroundColor: msg.role === 'user' ? '#4a90e2' : '#fff',
                    color: msg.role === 'user' ? '#fff' : '#333',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
                  }}>
                    {msg.content}
                  </div>
                </div>
              ))
            )}
            {chatLoading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '16px' }}>
                <div style={{ padding: '12px 16px', borderRadius: '12px', backgroundColor: '#fff', boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }}>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#4a90e2', animation: 'bounce 1.4s infinite ease-in-out' }}></div>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#4a90e2', animation: 'bounce 1.4s infinite ease-in-out 0.2s' }}></div>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#4a90e2', animation: 'bounce 1.4s infinite ease-in-out 0.4s' }}></div>
                  </div>
                </div>
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
              placeholder="메시지를 입력하세요..."
              style={{ flex: 1, padding: '12px 16px', border: '1px solid #e0e0e0', borderRadius: '8px', fontSize: '14px' }}
              disabled={chatLoading}
            />
            <button
              onClick={sendChatMessage}
              disabled={chatLoading || !chatInput.trim()}
              style={{ 
                padding: '12px 24px', 
                backgroundColor: chatLoading || !chatInput.trim() ? '#ccc' : '#4a90e2', 
                color: '#fff', 
                border: 'none', 
                borderRadius: '8px', 
                cursor: chatLoading || !chatInput.trim() ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                fontWeight: '600'
              }}
            >
              {chatLoading ? '전송 중...' : '전송'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

export default AiPage;
