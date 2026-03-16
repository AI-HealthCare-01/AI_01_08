import React, { useEffect, useMemo, useState } from "react";
import AdminDashboard from "./AdminDashboard.jsx";
import HealthProfile from "./HealthProfile.jsx";
import DocumentManagement from "./DocumentManagement.jsx";
import CaregiverManagement from "./CaregiverManagement.jsx";
import AiPage from "./AiPage.jsx";
import SchedulePage from "./SchedulePage.jsx";
import SettingsPage from "./SettingsPage.jsx";

const API_PREFIX = "/api/v1";



const safeJson = async (res) => {
  try {
    return await res.json();
  } catch {
    return null;
  }
};

const formatDateTime = (value) => {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
};

function App() {
  const [healthStatus, setHealthStatus] = useState({
    loading: false,
    data: null,
    error: null
  });
  const [roles, setRoles] = useState([]);
  const [rolesError, setRolesError] = useState(null);
  const [loginForm, setLoginForm] = useState({
    email: "",
    password: "",
    role: "PATIENT"
  });
  const [loginState, setLoginState] = useState({
    submitting: false,
    error: null
  });
  const [findEmailForm, setFindEmailForm] = useState({
    name: "",
    phoneNumber: ""
  });
  const [findEmailState, setFindEmailState] = useState({
    submitting: false,
    error: null,
    email: null
  });
  const [resetPasswordForm, setResetPasswordForm] = useState({
    email: "",
    name: "",
    phoneNumber: "",
    newPassword: "",
    newPasswordConfirm: ""
  });
  const [resetPasswordState, setResetPasswordState] = useState({
    submitting: false,
    error: null,
    success: false
  });
  const [showFindModal, setShowFindModal] = useState(false);
  const [findModalTab, setFindModalTab] = useState("email");
  const [authChecking, setAuthChecking] = useState(true);
  const readCookie = (name) => {
    if (typeof document === "undefined") {
      return null;
    }
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match ? decodeURIComponent(match[2]) : null;
  };

  const [accessToken, setAccessToken] = useState(() => {
    if (typeof window === "undefined") {
      return null;
    }
    return window.localStorage.getItem("access_token") || readCookie("access_token");
  });
  const [loginRole, setLoginRole] = useState(() => {
    if (typeof window === "undefined") {
      return "PATIENT";
    }
    return window.localStorage.getItem("login_role") || "PATIENT";
  });
  const [signupForm, setSignupForm] = useState({
    name: "",
    role: "PATIENT",
    email: "",
    password: "",
    passwordConfirm: "",
    gender: "MALE",
    birthDate: "",
    phoneNumber: "",
    privacyConsent: false
  });
  const [signupState, setSignupState] = useState({
    submitting: false,
    error: null,
    success: false
  });

  const [meState, setMeState] = useState({
    loading: false,
    data: null,
    error: null
  });
  const [profileForm, setProfileForm] = useState({
    name: "",
    email: "",
    phone_number: "",
    birthday: "",
    gender: "MALE"
  });
  const [profileState, setProfileState] = useState({
    submitting: false,
    error: null,
    success: false
  });

  const [inviteState, setInviteState] = useState({
    submitting: false,
    error: null,
    data: null
  });
  const [inviteDeleteState, setInviteDeleteState] = useState({
    submitting: false,
    error: null,
    success: false
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

  const [notificationsState, setNotificationsState] = useState({
    loading: false,
    items: [],
    nextCursor: null,
    error: null
  });
  const [notificationsAction, setNotificationsAction] = useState({
    submitting: false,
    error: null
  });
  const [unreadCountState, setUnreadCountState] = useState({
    loading: false,
    count: 0,
    error: null
  });
  const [settingsState, setSettingsState] = useState({
    loading: false,
    data: null,
    error: null,
    submitting: false,
    success: false
  });
  const [remindForm, setRemindForm] = useState({
    patient_id: "",
    type: "intake_reminder",
    title: "복약 리마인드",
    message: "복약 시간이예요! 확인해 주세요.",
    payload: '{"schedule_id":123}'
  });
  const [remindState, setRemindState] = useState({
    submitting: false,
    error: null,
    success: null
  });

  const pathname = typeof window !== "undefined" ? window.location.pathname : "/";
  const isLoginPage = useMemo(() => {
    return pathname.startsWith("/auth-demo/login") || pathname.startsWith("/auth-demo/app/login");
  }, [pathname]);
  const isSignupPage = useMemo(() => {
    return pathname.startsWith("/auth-demo/signup") || pathname.startsWith("/auth-demo/app/signup");
  }, [pathname]);
  const isProfilePage = useMemo(() => {
    return pathname.startsWith("/auth-demo/profile") || pathname.startsWith("/auth-demo/app/profile");
  }, [pathname]);
  const isDashboardPage = useMemo(() => {
    return pathname.startsWith("/auth-demo/dashboard") || pathname.startsWith("/auth-demo/app/dashboard");
  }, [pathname]);
  const isHealthProfilePage = useMemo(() => {
    return pathname.startsWith("/auth-demo/health-profile") || pathname.startsWith("/auth-demo/app/health-profile");
  }, [pathname]);
  const isDocumentsPage = useMemo(() => {
    return pathname.startsWith("/auth-demo/documents") || pathname.startsWith("/auth-demo/app/documents");
  }, [pathname]);
  const isCaregiverPage = useMemo(() => {
    return pathname.startsWith("/auth-demo/caregiver") || pathname.startsWith("/auth-demo/app/caregiver");
  }, [pathname]);
  const isAiPage = useMemo(() => {
    return pathname.startsWith("/auth-demo/ai") || pathname.startsWith("/auth-demo/app/ai");
  }, [pathname]);
  const isSchedulePage = useMemo(() => {
    return pathname.startsWith("/auth-demo/schedule") || pathname.startsWith("/auth-demo/app/schedule");
  }, [pathname]);
  const isSettingsPage = useMemo(() => {
    return pathname.startsWith("/auth-demo/settings") || pathname.startsWith("/auth-demo/app/settings");
  }, [pathname]);

  const persistAccessToken = (token) => {
    if (typeof window !== "undefined") {
      if (token) {
        window.localStorage.setItem("access_token", token);
      } else {
        window.localStorage.removeItem("access_token");
      }
    }
    if (typeof document !== "undefined") {
      if (token) {
        document.cookie = `access_token=${encodeURIComponent(token)}; path=/;`;
      } else {
        document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
      }
    }
    setAccessToken(token);
  };

  const persistLoginRole = (role) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("login_role", role);
    }
    setLoginRole(role);
  };

  const refreshAccessToken = async () => {
    const res = await fetch(`${API_PREFIX}/auth/token/refresh`, {
      method: "GET",
      credentials: "include"
    });
    if (!res.ok) {
      return null;
    }
    const body = await safeJson(res);
    const token = body?.access_token;
    if (token) {
      persistAccessToken(token);
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

  useEffect(() => {
    if (!isSignupPage) {
      return;
    }
    let isMounted = true;
    const loadRoles = async () => {
      try {
        const res = await fetch("/api/v1/public/roles");
        if (!res.ok) {
          throw new Error(`status ${res.status}`);
        }
        const data = await res.json();
        if (isMounted) {
          setRoles(data);
          setRolesError(null);
        }
      } catch (error) {
        if (isMounted) {
          setRolesError(error.message);
        }
      }
    };
    loadRoles();
    return () => {
      isMounted = false;
    };
  }, [isSignupPage]);

  useEffect(() => {
    if (!accessToken) {
      return;
    }
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
    // 알림 기능은 DB 스키마 문제로 비활성화
    // loadNotifications();
    // loadUnreadCount();
    // loadSettings();
  }, [accessToken]);

  useEffect(() => {
    let active = true;
    const bootstrapAuth = async () => {
      if (accessToken) {
        if (active) {
          setAuthChecking(false);
        }
        return;
      }
      try {
        await refreshAccessToken();
      } catch {
        // ignore refresh failures
      } finally {
        if (active) {
          setAuthChecking(false);
        }
      }
    };
    bootstrapAuth();
    return () => {
      active = false;
    };
  }, [accessToken]);

  useEffect(() => {
    if (!meState.data) {
      return;
    }
    setProfileForm({
      name: meState.data.name || "",
      email: meState.data.email || "",
      phone_number: meState.data.phone_number || "",
      birthday: meState.data.birthday || "",
      gender: meState.data.gender || "MALE"
    });
  }, [meState.data]);

  const checkHealth = async () => {
    setHealthStatus({ loading: true, data: null, error: null });
    try {
      const res = await fetch("/api/health");
      if (!res.ok) {
        throw new Error(`status ${res.status}`);
      }
      const body = await res.json();
      setHealthStatus({ loading: false, data: body, error: null });
    } catch (error) {
      setHealthStatus({ loading: false, data: null, error: error.message });
    }
  };

  const handleSignupChange = (event) => {
    const { name, value } = event.target;
    setSignupForm((prev) => ({
      ...prev,
      [name]: event.target.type === "checkbox" ? event.target.checked : value
    }));
  };

  const handleLoginChange = (event) => {
    const { name, value } = event.target;
    setLoginForm((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const handleProfileChange = (event) => {
    const { name, value } = event.target;
    setProfileForm((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const resolveRoleLabel = (role) => {
    if (!role) {
      return "";
    }
    if (role.description) {
      return role.description;
    }
    const code = role.code || role.name || "";
    const normalized = code.toUpperCase();
    if (normalized === "PATIENT") {
      return "환자";
    }
    if (normalized === "CAREGIVER" || normalized === "GUARDIAN") {
      return "보호자";
    }
    if (normalized === "ADMIN") {
      return "관리자";
    }
    return code;
  };

  const formatValidationError = (item) => {
    if (!item || typeof item !== "object") {
      return null;
    }
    const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : null;
    if (item.type === "string_too_short" && item.ctx?.min_length) {
      if (field === "password") {
        return `비밀번호는 최소 ${item.ctx.min_length}자 이상이어야 합니다.`;
      }
      return `${field ?? "입력값"}은(는) 최소 ${item.ctx.min_length}자 이상이어야 합니다.`;
    }
    if (item.type === "value_error.email") {
      return "이메일 형식이 올바르지 않습니다.";
    }
    if (field === "phone_number" && item.type === "value_error") {
      return "휴대폰 번호 형식이 올바르지 않습니다.";
    }
    if (field === "birth_date" || field === "birthday") {
      return "생년월일 형식이 올바르지 않습니다.";
    }
    if (item.msg) {
      return item.msg;
    }
    return null;
  };

  const formatApiError = (value) => {
    if (!value) {
      return "알 수 없는 오류가 발생했습니다.";
    }
    if (typeof value === "string") {
      return value;
    }
    if (Array.isArray(value)) {
      const messages = value.map((item) => formatValidationError(item) || formatApiError(item));
      return messages.filter(Boolean).join(", ");
    }
    if (typeof value === "object") {
      if (Object.keys(value).length === 0) {
        return null;
      }
      if (value.detail) {
        return formatApiError(value.detail);
      }
      if (value.message) {
        return formatApiError(value.message);
      }
      return JSON.stringify(value);
    }
    return String(value);
  };

  const handleSignupSubmit = async (event) => {
    if (event?.preventDefault) {
      event.preventDefault();
    }
    if (signupForm.password !== signupForm.passwordConfirm) {
      setSignupState({ submitting: false, error: "비밀번호가 일치하지 않습니다.", success: false });
      return;
    }
    if (!signupForm.privacyConsent) {
      setSignupState({ submitting: false, error: "개인정보 수집·이용에 동의해 주세요.", success: false });
      return;
    }
    setSignupState({ submitting: true, error: null, success: false });
    try {
      const payload = {
        email: signupForm.email,
        password: signupForm.password,
        name: signupForm.name,
        gender: signupForm.gender,
        birth_date: signupForm.birthDate,
        phone_number: signupForm.phoneNumber
      };
      const res = await fetch("/api/v1/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const message = formatApiError(body) || `status ${res.status}`;
        throw new Error(message);
      }
      setSignupState({ submitting: false, error: null, success: true });
      window.location.href = "/auth-demo/login";
    } catch (error) {
      setSignupState({
        submitting: false,
        error: formatApiError(error?.message || error),
        success: false
      });
    }
  };

  const handleLoginSubmit = async (event) => {
    if (event?.preventDefault) {
      event.preventDefault();
    }
    setLoginState({ submitting: true, error: null });
    try {
      const payload = {
        email: loginForm.email,
        password: loginForm.password,
        role: loginForm.role
      };
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const message = formatApiError(body) || `status ${res.status}`;
        throw new Error(message);
      }
      const body = await res.json().catch(() => ({}));
      const token = body?.access_token;
      const role = body?.login_role || loginForm.role;
      if (token) {
        persistAccessToken(token);
      }
      if (role) {
        persistLoginRole(role);
      }
      setLoginState({ submitting: false, error: null });
      window.location.href = "/auth-demo/app";
    } catch (error) {
      setLoginState({ submitting: false, error: formatApiError(error?.message || error) });
    }
  };

  const handleFindEmailSubmit = async (event) => {
    event.preventDefault();
    setFindEmailState({ submitting: true, error: null, email: null });
    try {
      const payload = {
        name: findEmailForm.name,
        phone_number: findEmailForm.phoneNumber
      };
      const res = await fetch("/api/v1/auth/find-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      const body = await res.json();
      setFindEmailState({ submitting: false, error: null, email: body.email });
    } catch (error) {
      setFindEmailState({ submitting: false, error: formatApiError(error?.message || error), email: null });
    }
  };

  const handleResetPasswordSubmit = async (event) => {
    event.preventDefault();
    if (resetPasswordForm.newPassword !== resetPasswordForm.newPasswordConfirm) {
      setResetPasswordState({ submitting: false, error: "비밀번호가 일치하지 않습니다.", success: false });
      return;
    }
    setResetPasswordState({ submitting: true, error: null, success: false });
    try {
      const payload = {
        email: resetPasswordForm.email,
        name: resetPasswordForm.name,
        phone_number: resetPasswordForm.phoneNumber,
        new_password: resetPasswordForm.newPassword
      };
      const res = await fetch("/api/v1/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      setResetPasswordState({ submitting: false, error: null, success: true });
      setTimeout(() => {
        setShowFindModal(false);
        setResetPasswordState({ submitting: false, error: null, success: false });
        setResetPasswordForm({ email: "", name: "", phoneNumber: "", newPassword: "", newPasswordConfirm: "" });
      }, 2000);
    } catch (error) {
      setResetPasswordState({ submitting: false, error: formatApiError(error?.message || error), success: false });
    }
  };

  const startSocialLogin = async (provider, role) => {
    setLoginState({ submitting: true, error: null });
    try {
      const params = new URLSearchParams();
      if (role) {
        params.set("role", role);
      }
      const res = await fetch(`${API_PREFIX}/auth/social/${provider}/login?${params.toString()}`);
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      const body = await safeJson(res);
      const authorizeUrl = body?.authorize_url;
      if (!authorizeUrl) {
        throw new Error("소셜 로그인 URL을 가져오지 못했습니다.");
      }
      persistLoginRole(role || loginForm.role || "PATIENT");
      window.location.href = authorizeUrl;
    } catch (error) {
      setLoginState({ submitting: false, error: formatApiError(error?.message || error) });
    }
  };

  const handleLogout = async (event) => {
    if (event?.preventDefault) {
      event.preventDefault();
    }
    try {
      await fetch(`${API_PREFIX}/auth/logout`, { method: "POST", credentials: "include" });
    } catch {
      // ignore network failures; still clear local auth state
    } finally {
      persistAccessToken(null);
      setMeState({ loading: false, data: null, error: null });
      setLinksState({ loading: false, data: null, error: null });
      setNotificationsState({ loading: false, items: [], nextCursor: null, error: null });
      setUnreadCountState({ loading: false, count: 0, error: null });
      if (typeof window !== "undefined") {
        window.location.href = "/auth-demo/login";
      }
    }
  };

  const submitProfileUpdate = async (event) => {
    event.preventDefault();
    setProfileState({ submitting: true, error: null, success: false });
    try {
      const payload = {};
      if (profileForm.name) payload.name = profileForm.name;
      if (profileForm.email) payload.email = profileForm.email;
      if (profileForm.phone_number) payload.phone_number = profileForm.phone_number;
      if (profileForm.birthday) payload.birthday = profileForm.birthday;
      if (profileForm.gender) payload.gender = profileForm.gender;

      const res = await authFetch(`${API_PREFIX}/users/me`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      const data = await res.json();
      setMeState({ loading: false, data, error: null });
      setProfileState({ submitting: false, error: null, success: true });
    } catch (error) {
      setProfileState({ submitting: false, error: formatApiError(error?.message || error), success: false });
    }
  };

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
    setInviteDeleteState({ submitting: true, error: null, success: false });
    try {
      const res = await authFetch(`${API_PREFIX}/users/invite-code`, { method: "DELETE" });
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      setInviteDeleteState({ submitting: false, error: null, success: true });
      setInviteState((prev) => ({ ...prev, data: null }));
    } catch (error) {
      setInviteDeleteState({
        submitting: false,
        error: formatApiError(error?.message || error),
        success: false
      });
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

  const loadMoreNotifications = async () => {
    if (notificationsState.loading) {
      return;
    }
    setNotificationsState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const params = new URLSearchParams();
      params.set("limit", "20");
      if (notificationsState.nextCursor) {
        params.set("cursor", notificationsState.nextCursor);
      }
      const res = await authFetch(`${API_PREFIX}/notifications?${params.toString()}`);
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      const body = await safeJson(res);
      const data = body?.data || body;
      setNotificationsState((prev) => ({
        loading: false,
        items: [...prev.items, ...(data?.items || [])],
        nextCursor: data?.next_cursor ?? null,
        error: null
      }));
    } catch (error) {
      setNotificationsState((prev) => ({ ...prev, loading: false, error: error.message }));
    }
  };

  const markNotificationRead = async (notificationId) => {
    setNotificationsAction({ submitting: true, error: null });
    try {
      const res = await authFetch(`${API_PREFIX}/notifications/${notificationId}/read`, {
        method: "PATCH"
      });
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      setNotificationsState((prev) => ({
        ...prev,
        items: prev.items.map((item) =>
          item.id === notificationId ? { ...item, read_at: item.read_at || new Date().toISOString() } : item
        )
      }));
      setUnreadCountState((prev) => ({ ...prev, count: Math.max(0, prev.count - 1) }));
      setNotificationsAction({ submitting: false, error: null });
    } catch (error) {
      setNotificationsAction({ submitting: false, error: formatApiError(error?.message || error) });
    }
  };

  const markAllNotificationsRead = async () => {
    setNotificationsAction({ submitting: true, error: null });
    try {
      const res = await authFetch(`${API_PREFIX}/notifications/read-all`, {
        method: "PATCH"
      });
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      setNotificationsState((prev) => ({
        ...prev,
        items: prev.items.map((item) => ({ ...item, read_at: item.read_at || new Date().toISOString() }))
      }));
      setUnreadCountState((prev) => ({ ...prev, count: 0 }));
      setNotificationsAction({ submitting: false, error: null });
    } catch (error) {
      setNotificationsAction({ submitting: false, error: formatApiError(error?.message || error) });
    }
  };

  const handleSettingsChange = (event) => {
    const { name, checked } = event.target;
    setSettingsState((prev) => ({
      ...prev,
      data: {
        ...(prev.data || {}),
        [name]: checked
      },
      success: false
    }));
  };

  const submitSettingsUpdate = async (event) => {
    event.preventDefault();
    if (!settingsState.data) {
      return;
    }
    setSettingsState((prev) => ({ ...prev, submitting: true, error: null, success: false }));
    try {
      const res = await authFetch(`${API_PREFIX}/notifications/settings`, {
        method: "PATCH",
        body: JSON.stringify(settingsState.data)
      });
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      const body = await safeJson(res);
      const data = body?.data || body;
      setSettingsState((prev) => ({
        ...prev,
        submitting: false,
        data,
        success: true,
        error: null
      }));
    } catch (error) {
      setSettingsState((prev) => ({
        ...prev,
        submitting: false,
        error: formatApiError(error?.message || error),
        success: false
      }));
    }
  };

  const handleRemindChange = (event) => {
    const { name, value } = event.target;
    setRemindForm((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const submitRemind = async (event) => {
    event.preventDefault();
    
    if (!remindForm.patient_id) {
      setRemindState({ submitting: false, error: "환자를 선택해주세요.", success: null });
      return;
    }
    
    setRemindState({ submitting: true, error: null, success: null });
    try {
      const payload = {
        patient_id: Number(remindForm.patient_id),
        type: remindForm.type,
        title: remindForm.title || "복약 리마인드",
        message: remindForm.message || "복약 시간이예요! 확인해 주세요."
      };
      
      if (remindForm.payload && remindForm.payload.trim()) {
        try {
          payload.payload = JSON.parse(remindForm.payload);
        } catch {
          throw new Error("payload는 유효한 JSON 형식이어야 합니다.");
        }
      }
      
      const res = await authFetch(`${API_PREFIX}/notifications/remind`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const body = await safeJson(res);
        throw new Error(formatApiError(body) || `status ${res.status}`);
      }
      
      setRemindState({ submitting: false, error: null, success: "리마인드 전송 완료" });
      
      // 성공 후 폼 초기화
      setTimeout(() => {
        setRemindState({ submitting: false, error: null, success: null });
      }, 3000);
    } catch (error) {
      setRemindState({ submitting: false, error: formatApiError(error?.message || error), success: null });
    }
  };

  if (isSignupPage) {
    return (
      <div className="login-page">
        <div className="container">
          <div className="row justify-content-center">
            <div className="col-lg-6">
              <div className="card shadow-lg border-0">
                <div className="card-body p-4">
                  <h2 className="fw-bold mb-2">회원가입</h2>
                  <p className="text-muted mb-4">팀 계정을 생성하세요.</p>
                  <form onSubmit={handleSignupSubmit}>
                    <div className="row g-3">
                      <div className="col-md-6">
                        <label className="form-label">이름</label>
                        <input
                          type="text"
                          className="form-control"
                          name="name"
                          value={signupForm.name}
                          onChange={handleSignupChange}
                          placeholder="홍길동"
                          required
                        />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label">역할</label>
                        <select
                          className="form-select"
                          name="role"
                          value={signupForm.role}
                          onChange={handleSignupChange}
                        >
                          {roles.length > 0 ? (
                            roles.map((role) => (
                              <option key={`${role.code}-${role.name}`} value={role.code || role.name}>
                                {resolveRoleLabel(role)}
                              </option>
                            ))
                          ) : (
                            <>
                              <option value="PATIENT">환자</option>
                              <option value="CAREGIVER">보호자</option>
                              <option value="ADMIN">관리자</option>
                            </>
                          )}
                        </select>
                        {rolesError && <div className="text-danger small mt-1">역할 로딩 실패</div>}
                      </div>
                      <div className="col-12">
                        <label className="form-label">이메일</label>
                        <input
                          type="email"
                          className="form-control"
                          name="email"
                          value={signupForm.email}
                          onChange={handleSignupChange}
                          placeholder="name@clinic.com"
                          required
                        />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label">성별</label>
                        <select
                          className="form-select"
                          name="gender"
                          value={signupForm.gender}
                          onChange={handleSignupChange}
                        >
                          <option value="MALE">남성</option>
                          <option value="FEMALE">여성</option>
                        </select>
                      </div>
                      <div className="col-md-6">
                        <label className="form-label">생년월일</label>
                        <input
                          type="date"
                          className="form-control"
                          name="birthDate"
                          value={signupForm.birthDate}
                          onChange={handleSignupChange}
                          required
                        />
                      </div>
                      <div className="col-12">
                        <label className="form-label">휴대폰 번호</label>
                        <input
                          type="tel"
                          className="form-control"
                          name="phoneNumber"
                          value={signupForm.phoneNumber}
                          onChange={handleSignupChange}
                          placeholder="01012345678"
                          required
                        />
                      </div>
                      <div className="col-12">
                        <div className="form-check">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id="privacyConsent"
                            name="privacyConsent"
                            checked={signupForm.privacyConsent}
                            onChange={handleSignupChange}
                            required
                          />
                          <label className="form-check-label" htmlFor="privacyConsent">
                            개인정보 수집·이용에 동의합니다(필수)
                          </label>
                        </div>
                        <div className="small text-muted mt-1">
                          <div>수집·이용 목적: 회원가입, 본인확인, 서비스 제공 및 고객지원</div>
                          <div>수집 항목: 이름, 이메일(아이디), 비밀번호, 성별, 생년월일, 휴대폰 번호</div>
                          <div>보유·이용 기간: 회원 탈퇴 시까지(단, 관계법령에 따라 보관이 필요한 경우 해당 기간 보관)</div>
                          <div>동의 거부 권리: 개인정보 수집·이용에 대한 동의를 거부할 수 있으나, 동의 거부 시 회원가입이 제한됩니다.</div>
                        </div>
                      </div>
                      <div className="col-md-6">
                        <label className="form-label">비밀번호</label>
                        <input
                          type="password"
                          className="form-control"
                          name="password"
                          value={signupForm.password}
                          onChange={handleSignupChange}
                          placeholder="비밀번호 입력"
                          required
                        />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label">비밀번호 확인</label>
                        <input
                          type="password"
                          className="form-control"
                          name="passwordConfirm"
                          value={signupForm.passwordConfirm}
                          onChange={handleSignupChange}
                          placeholder="비밀번호 확인"
                          required
                        />
                      </div>
                    </div>
                    <div className="d-grid gap-2 mt-4">
                      <button type="submit" className="btn btn-primary btn-lg" disabled={signupState.submitting}>
                        {signupState.submitting ? "처리 중..." : "회원가입"}
                      </button>
                      <a className="btn btn-outline-secondary" href="/auth-demo/login">
                        로그인으로 돌아가기
                      </a>
                    </div>
                  </form>
                  {signupState.error && <div className="alert alert-danger mt-3">{signupState.error}</div>}
                  {signupState.success && <div className="alert alert-success mt-3">회원가입 완료</div>}
                  <div className="mt-4 small text-muted">
                    계정 생성 시 약관에 동의한 것으로 간주합니다.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isLoginPage) {
    if (accessToken) {
      window.location.href = "/auth-demo/app";
      return null;
    }
    if (authChecking) {
      return (
        <div className="login-page">
          <div className="container text-center">
            <div className="py-5 text-muted">로그인 상태 확인 중...</div>
          </div>
        </div>
      );
    }
    return (
      <div className="login-page">
        <div className="container">
          <div className="row justify-content-center">
            <div className="col-lg-5">
              <div className="card shadow-lg border-0">
                <div className="card-body p-4">
                  <h2 className="fw-bold mb-2">로그인</h2>
                  <p className="text-muted mb-4">팀 계정으로 로그인하세요.</p>
                  <div>
                    <div className="mb-3">
                      <label className="form-label">이메일</label>
                      <input
                        type="email"
                        className="form-control"
                        name="email"
                        value={loginForm.email}
                        onChange={handleLoginChange}
                        placeholder="name@clinic.com"
                        required
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label">비밀번호</label>
                      <input
                        type="password"
                        className="form-control"
                        name="password"
                        value={loginForm.password}
                        onChange={handleLoginChange}
                        placeholder="비밀번호 입력"
                        required
                      />
                    </div>
                    <div className="mb-4">
                      <label className="form-label">역할</label>
                      <select
                        className="form-select"
                        name="role"
                        value={loginForm.role}
                        onChange={handleLoginChange}
                      >
                        <option value="PATIENT">환자</option>
                        <option value="CAREGIVER">보호자</option>
                        <option value="GUARDIAN">보호자(보조)</option>
                      </select>
                    </div>
                    <div className="d-grid gap-2">
                      <button
                        type="button"
                        className="btn btn-primary btn-lg"
                        disabled={loginState.submitting}
                        onClick={handleLoginSubmit}
                      >
                        {loginState.submitting ? "처리 중..." : "로그인"}
                      </button>
                      <button
                        type="button"
                        className="btn btn-kakao btn-lg"
                        onClick={() => startSocialLogin("kakao", loginForm.role)}
                        disabled={loginState.submitting}
                      >
                        카카오톡 간편로그인
                      </button>
                      <a className="btn btn-outline-secondary" href="/auth-demo/signup">
                        회원가입
                      </a>
                      <button
                        type="button"
                        className="btn btn-link text-muted"
                        onClick={() => {
                          setShowFindModal(true);
                          setFindModalTab("email");
                        }}
                      >
                        아이디/비밀번호 찾기
                      </button>
                      <a className="btn btn-outline-secondary" href="/auth-demo/app">
                        대시보드로 이동
                      </a>
                    </div>
                  </div>
                  {loginState.error && <div className="alert alert-danger mt-3">{loginState.error}</div>}
                  <div className="mt-4 small text-muted">테스트 계정이 필요하면 관리자에게 문의하세요.</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        {showFindModal && (
          <div className="modal show d-block" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
            <div className="modal-dialog modal-dialog-centered">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">아이디/비밀번호 찾기</h5>
                  <button
                    type="button"
                    className="btn-close"
                    onClick={() => {
                      setShowFindModal(false);
                      setFindEmailState({ submitting: false, error: null, email: null });
                      setResetPasswordState({ submitting: false, error: null, success: false });
                      setFindEmailForm({ name: "", phoneNumber: "" });
                      setResetPasswordForm({ email: "", name: "", phoneNumber: "", newPassword: "", newPasswordConfirm: "" });
                    }}
                  ></button>
                </div>
                <div className="modal-body">
                  <ul className="nav nav-tabs mb-3">
                    <li className="nav-item">
                      <button
                        className={`nav-link ${findModalTab === "email" ? "active" : ""}`}
                        onClick={() => setFindModalTab("email")}
                      >
                        아이디 찾기
                      </button>
                    </li>
                    <li className="nav-item">
                      <button
                        className={`nav-link ${findModalTab === "password" ? "active" : ""}`}
                        onClick={() => setFindModalTab("password")}
                      >
                        비밀번호 재설정
                      </button>
                    </li>
                  </ul>
                  {findModalTab === "email" && (
                    <form onSubmit={handleFindEmailSubmit}>
                      <div className="mb-3">
                        <label className="form-label">이름</label>
                        <input
                          type="text"
                          className="form-control"
                          value={findEmailForm.name}
                          onChange={(e) => setFindEmailForm({ ...findEmailForm, name: e.target.value })}
                          required
                        />
                      </div>
                      <div className="mb-3">
                        <label className="form-label">휴대폰 번호</label>
                        <input
                          type="tel"
                          className="form-control"
                          value={findEmailForm.phoneNumber}
                          onChange={(e) => setFindEmailForm({ ...findEmailForm, phoneNumber: e.target.value })}
                          placeholder="01012345678"
                          required
                        />
                      </div>
                      <button type="submit" className="btn btn-primary w-100" disabled={findEmailState.submitting}>
                        {findEmailState.submitting ? "확인 중..." : "아이디 찾기"}
                      </button>
                      {findEmailState.error && <div className="alert alert-danger mt-3">{findEmailState.error}</div>}
                      {findEmailState.email && (
                        <div className="alert alert-success mt-3">
                          회원님의 아이디는 <strong>{findEmailState.email}</strong> 입니다.
                        </div>
                      )}
                    </form>
                  )}
                  {findModalTab === "password" && (
                    <form onSubmit={handleResetPasswordSubmit}>
                      <div className="mb-3">
                        <label className="form-label">이메일</label>
                        <input
                          type="email"
                          className="form-control"
                          value={resetPasswordForm.email}
                          onChange={(e) => setResetPasswordForm({ ...resetPasswordForm, email: e.target.value })}
                          required
                        />
                      </div>
                      <div className="mb-3">
                        <label className="form-label">이름</label>
                        <input
                          type="text"
                          className="form-control"
                          value={resetPasswordForm.name}
                          onChange={(e) => setResetPasswordForm({ ...resetPasswordForm, name: e.target.value })}
                          required
                        />
                      </div>
                      <div className="mb-3">
                        <label className="form-label">휴대폰 번호</label>
                        <input
                          type="tel"
                          className="form-control"
                          value={resetPasswordForm.phoneNumber}
                          onChange={(e) => setResetPasswordForm({ ...resetPasswordForm, phoneNumber: e.target.value })}
                          placeholder="01012345678"
                          required
                        />
                      </div>
                      <div className="mb-3">
                        <label className="form-label">새 비밀번호</label>
                        <input
                          type="password"
                          className="form-control"
                          value={resetPasswordForm.newPassword}
                          onChange={(e) => setResetPasswordForm({ ...resetPasswordForm, newPassword: e.target.value })}
                          required
                        />
                      </div>
                      <div className="mb-3">
                        <label className="form-label">새 비밀번호 확인</label>
                        <input
                          type="password"
                          className="form-control"
                          value={resetPasswordForm.newPasswordConfirm}
                          onChange={(e) => setResetPasswordForm({ ...resetPasswordForm, newPasswordConfirm: e.target.value })}
                          required
                        />
                      </div>
                      <button type="submit" className="btn btn-primary w-100" disabled={resetPasswordState.submitting}>
                        {resetPasswordState.submitting ? "처리 중..." : "비밀번호 재설정"}
                      </button>
                      {resetPasswordState.error && <div className="alert alert-danger mt-3">{resetPasswordState.error}</div>}
                      {resetPasswordState.success && <div className="alert alert-success mt-3">비밀번호가 재설정되었습니다.</div>}
                    </form>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (!isLoginPage && !isSignupPage && !accessToken) {
    if (authChecking) {
      return (
        <div className="login-page">
          <div className="container text-center">
            <div className="py-5 text-muted">인증 상태 확인 중...</div>
          </div>
        </div>
      );
    }
    window.location.href = "/auth-demo/login";
    return null;
  }

  if (isProfilePage && !accessToken) {
    if (authChecking) {
      return (
        <div className="login-page">
          <div className="container text-center">
            <div className="py-5 text-muted">인증 상태 확인 중...</div>
          </div>
        </div>
      );
    }
    window.location.href = "/auth-demo/login";
    return null;
  }

  if (isDashboardPage) {
    if (!accessToken) {
      if (authChecking) {
        return (
          <div className="login-page">
            <div className="container text-center">
              <div className="py-5 text-muted">인증 상태 확인 중...</div>
            </div>
          </div>
        );
      }
      window.location.href = "/auth-demo/login";
      return null;
    }
    return <AdminDashboard />;
  }

  if (isHealthProfilePage) {
    if (!accessToken) {
      if (authChecking) {
        return (
          <div className="login-page">
            <div className="container text-center">
              <div className="py-5 text-muted">인증 상태 확인 중...</div>
            </div>
          </div>
        );
      }
      window.location.href = "/auth-demo/login";
      return null;
    }
    return <HealthProfile />;
  }

  if (isDocumentsPage) {
    if (!accessToken) {
      if (authChecking) {
        return (
          <div className="login-page">
            <div className="container text-center">
              <div className="py-5 text-muted">인증 상태 확인 중...</div>
            </div>
          </div>
        );
      }
      window.location.href = "/auth-demo/login";
      return null;
    }
    return <DocumentManagement />;
  }

  if (isCaregiverPage) {
    if (!accessToken) {
      if (authChecking) {
        return (
          <div className="login-page">
            <div className="container text-center">
              <div className="py-5 text-muted">인증 상태 확인 중...</div>
            </div>
          </div>
        );
      }
      window.location.href = "/auth-demo/login";
      return null;
    }
    return <CaregiverManagement />;
  }

  if (isAiPage) {
    if (!accessToken) {
      if (authChecking) {
        return (
          <div className="login-page">
            <div className="container text-center">
              <div className="py-5 text-muted">인증 상태 확인 중...</div>
            </div>
          </div>
        );
      }
      window.location.href = "/auth-demo/login";
      return null;
    }
    return <AiPage />;
  }

  if (isSchedulePage) {
    if (!accessToken) {
      if (authChecking) {
        return (
          <div className="login-page">
            <div className="container text-center">
              <div className="py-5 text-muted">인증 상태 확인 중...</div>
            </div>
          </div>
        );
      }
      window.location.href = "/auth-demo/login";
      return null;
    }
    return <SchedulePage />;
  }

  if (isSettingsPage) {
    if (!accessToken) {
      if (authChecking) {
        return (
          <div className="login-page">
            <div className="container text-center">
              <div className="py-5 text-muted">인증 상태 확인 중...</div>
            </div>
          </div>
        );
      }
      window.location.href = "/auth-demo/login";
      return null;
    }
    return <SettingsPage />;
  }

  if (isProfilePage) {
    return (
      <div className="app-shell">
        <header className="hero">
          <div className="container py-5">
            <nav className="navbar navbar-expand-lg">
              <a className="navbar-brand fw-bold" href="/auth-demo/app" style={{ fontSize: '1.5rem' }}>
                (주)케어브릿지
              </a>
              <div className="ms-auto d-flex gap-2">
                <a className="btn btn-outline-light btn-sm" href="/auth-demo/app">
                  대시보드
                </a>
                <button className="btn btn-light btn-sm text-primary" onClick={handleLogout}>
                  로그아웃
                </button>
              </div>
            </nav>
            <div className="row align-items-center mt-4">
              <div className="col-lg-8">
                <h1 className="display-6 fw-bold">개인정보</h1>
                <p className="lead mt-3">계정 정보와 보안 설정을 관리하세요.</p>
              </div>
            </div>
          </div>
        </header>

        <main className="container my-5">
          <div className="row g-4">
            <div className="col-lg-7">
              <div className="card border-0 shadow-sm">
                <div className="card-body">
                  <h5 className="card-title">기본 정보</h5>
                  <p className="text-muted">계정에 등록된 기본 정보를 확인하세요.</p>
                  {meState.loading && <div className="text-muted">불러오는 중...</div>}
                  {meState.error && <div className="alert alert-danger">{meState.error}</div>}
                  {meState.data && (
                    <div className="row g-3">
                      <div className="col-md-6">
                        <div className="border rounded-3 p-3 h-100">
                          <div className="text-muted small">이메일</div>
                          <div className="fw-semibold">{meState.data.email}</div>
                        </div>
                      </div>
                      <div className="col-md-6">
                        <div className="border rounded-3 p-3 h-100">
                          <div className="text-muted small">역할</div>
                          <div className="fw-semibold">{loginRole}</div>
                        </div>
                      </div>
                      <div className="col-md-6">
                        <div className="border rounded-3 p-3 h-100">
                          <div className="text-muted small">계정 상태</div>
                          <div className="fw-semibold">활성</div>
                        </div>
                      </div>
                      <div className="col-md-6">
                        <div className="border rounded-3 p-3 h-100">
                          <div className="text-muted small">연락처</div>
                          <div className="fw-semibold">{meState.data.phone_number || "—"}</div>
                        </div>
                      </div>
                    </div>
                  )}
                  <form className="mt-4" onSubmit={submitProfileUpdate}>
                    <div className="row g-3">
                      <div className="col-md-6">
                        <label className="form-label">이름</label>
                        <input
                          className="form-control"
                          name="name"
                          value={profileForm.name}
                          onChange={handleProfileChange}
                        />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label">이메일</label>
                        <input
                          type="email"
                          className="form-control"
                          name="email"
                          value={profileForm.email}
                          onChange={handleProfileChange}
                        />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label">휴대폰 번호</label>
                        <input
                          className="form-control"
                          name="phone_number"
                          value={profileForm.phone_number}
                          onChange={handleProfileChange}
                        />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label">생년월일</label>
                        <input
                          type="date"
                          className="form-control"
                          name="birthday"
                          value={profileForm.birthday || ""}
                          onChange={handleProfileChange}
                        />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label">성별</label>
                        <select
                          className="form-select"
                          name="gender"
                          value={profileForm.gender}
                          onChange={handleProfileChange}
                        >
                          <option value="MALE">남성</option>
                          <option value="FEMALE">여성</option>
                        </select>
                      </div>
                    </div>
                    <div className="d-flex gap-2 mt-4">
                      <button className="btn btn-outline-primary" type="submit" disabled={profileState.submitting}>
                        {profileState.submitting ? "저장 중..." : "정보 수정"}
                      </button>
                      <button
                        className="btn btn-outline-secondary"
                        type="button"
                        onClick={() => {
                          if (!meState.data) {
                            return;
                          }
                          setProfileForm({
                            name: meState.data.name || "",
                            email: meState.data.email || "",
                            phone_number: meState.data.phone_number || "",
                            birthday: meState.data.birthday || "",
                            gender: meState.data.gender || "MALE"
                          });
                        }}
                      >
                        초기화
                      </button>
                    </div>
                    {profileState.error && <div className="alert alert-danger mt-3">{profileState.error}</div>}
                    {profileState.success && <div className="alert alert-success mt-3">저장 완료</div>}
                  </form>
                </div>
              </div>
            </div>
            <div className="col-lg-5">
              <div className="card border-0 shadow-sm mb-4">
                <div className="card-body">
                  <h5 className="card-title">보안 설정</h5>
                  <p className="text-muted">최근 로그인 활동과 보안 옵션을 관리하세요.</p>
                  <ul className="list-group list-group-flush">
                    <li className="list-group-item d-flex justify-content-between">
                      <span>최근 로그인</span>
                      <span className="fw-semibold">오늘</span>
                    </li>
                    <li className="list-group-item d-flex justify-content-between">
                      <span>2단계 인증</span>
                      <span className="fw-semibold">미설정</span>
                    </li>
                    <li className="list-group-item d-flex justify-content-between">
                      <span>연동된 기기</span>
                      <span className="fw-semibold">2대</span>
                    </li>
                  </ul>
                </div>
              </div>
              <div className="card border-0 shadow-sm">
                <div className="card-body">
                  <h5 className="card-title">알림 설정</h5>
                  <p className="text-muted">중요 알림을 수신할 방법을 선택하세요.</p>
                  <form onSubmit={submitSettingsUpdate}>
                    <div className="form-check">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="intake_reminder"
                        name="intake_reminder"
                        checked={settingsState.data?.intake_reminder ?? false}
                        onChange={handleSettingsChange}
                      />
                      <label className="form-check-label" htmlFor="intake_reminder">
                        복약 리마인드
                      </label>
                    </div>
                    <div className="form-check">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="missed_alert"
                        name="missed_alert"
                        checked={settingsState.data?.missed_alert ?? false}
                        onChange={handleSettingsChange}
                      />
                      <label className="form-check-label" htmlFor="missed_alert">
                        미복용 알림
                      </label>
                    </div>
                    <div className="form-check">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="ocr_done"
                        name="ocr_done"
                        checked={settingsState.data?.ocr_done ?? false}
                        onChange={handleSettingsChange}
                      />
                      <label className="form-check-label" htmlFor="ocr_done">
                        OCR 결과 알림
                      </label>
                    </div>
                    <div className="form-check">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="guide_ready"
                        name="guide_ready"
                        checked={settingsState.data?.guide_ready ?? false}
                        onChange={handleSettingsChange}
                      />
                      <label className="form-check-label" htmlFor="guide_ready">
                        가이드 준비 완료
                      </label>
                    </div>
                    <button className="btn btn-outline-primary btn-sm mt-3" type="submit" disabled={settingsState.submitting}>
                      {settingsState.submitting ? "저장 중..." : "알림 설정 저장"}
                    </button>
                    {settingsState.error && <div className="alert alert-danger mt-3">{settingsState.error}</div>}
                    {settingsState.success && <div className="alert alert-success mt-3">설정 저장 완료</div>}
                  </form>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="container py-5">
          <nav className="navbar navbar-expand-lg">
            <a className="navbar-brand fw-bold" href="#" style={{ fontSize: '1.5rem' }}>
              (주)케어브릿지
            </a>
            <div className="ms-auto d-flex align-items-center gap-3">
              {accessToken ? (
                <>
                  <div className="dropdown">
                    <button className="btn btn-outline-light btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                      대시보드
                    </button>
                    <ul className="dropdown-menu dropdown-menu-end">
                      <li><a className="dropdown-item" href="/auth-demo/app/dashboard">대시보드</a></li>
                      <li><a className="dropdown-item" href="/auth-demo/app/health-profile">건강 프로필</a></li>
                      <li><a className="dropdown-item" href="/auth-demo/app/documents">문서 관리</a></li>
                    </ul>
                  </div>
                  <div className="dropdown">
                    <button className="btn btn-outline-light btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                      보호자 관리
                    </button>
                    <ul className="dropdown-menu dropdown-menu-end">
                      <li><a className="dropdown-item" href="/auth-demo/app/caregiver">보호자 관리</a></li>
                      <li><a className="dropdown-item" href="/auth-demo/app/ai">AI 상담</a></li>
                    </ul>
                  </div>
                  <div className="dropdown">
                    <button className="btn btn-outline-light btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                      건강 프로필
                    </button>
                    <ul className="dropdown-menu dropdown-menu-end">
                      <li><a className="dropdown-item" href="/auth-demo/app/health-profile">건강 프로필</a></li>
                      <li><a className="dropdown-item" href="/auth-demo/app/schedule">스케줄</a></li>
                    </ul>
                  </div>
                  <a className="btn btn-outline-light btn-sm" href="/auth-demo/app/documents">문서 관리</a>
                  <a className="btn btn-outline-light btn-sm" href="/auth-demo/app/schedule">스케줄</a>
                  <a className="btn btn-outline-light btn-sm" href="/auth-demo/app/settings">개인정보</a>
                  <button className="btn btn-light btn-sm" onClick={handleLogout}>
                    로그아웃
                  </button>
                </>
              ) : (
                <>
                  <a className="btn btn-outline-light btn-sm" href="/auth-demo/login">
                    로그인
                  </a>
                </>
              )}
            </div>
          </nav>
          <div className="row align-items-center mt-4">
            <div className="col-lg-7">
              <h1 className="display-5 fw-bold">나와 내 가족을 지켜주는 AI기반 의료 워크플로우</h1>
              <p className="lead mt-3">한 눈에 볼 수 있는 나의 의료서비스</p>
            </div>
            <div className="col-lg-5 mt-4 mt-lg-0">
              <div className="card shadow-lg border-0">
                <div className="card-body">
                  <h5 className="card-title">오늘의 시스템 상태</h5>
                  <p className="text-muted">실시간 워크로드 모니터링</p>
                  <div className="progress mb-3" role="progressbar" aria-valuenow="72" aria-valuemin="0" aria-valuemax="100">
                    <div className="progress-bar" style={{ width: "72%" }}>
                      72%
                    </div>
                  </div>
                  <ul className="list-group list-group-flush">
                    <li className="list-group-item d-flex justify-content-between">
                      <span>응답 지연</span>
                      <span className="fw-semibold">120ms</span>
                    </li>
                    <li className="list-group-item d-flex justify-content-between">
                      <span>활성 케이스</span>
                      <span className="fw-semibold">38</span>
                    </li>
                    <li className="list-group-item d-flex justify-content-between">
                      <span>자동 분류</span>
                      <span className="fw-semibold">93%</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="container my-5">
        <section id="profile" className="mb-5">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <div className="d-flex flex-column flex-lg-row justify-content-between align-items-start align-items-lg-center gap-3">
                <div>
                  <h4 className="fw-bold mb-1">개인정보</h4>
                  <div className="text-muted">로그인 상태를 확인하고 계정 정보를 관리하세요.</div>
                </div>
                <div className="d-flex gap-2">
                  <a className="btn btn-outline-primary btn-sm" href="/auth-demo/app/profile">
                    정보 수정
                  </a>
                  <button className="btn btn-outline-secondary btn-sm">비밀번호 변경</button>
                </div>
              </div>
              <div className="row g-3 mt-3">
                <div className="col-md-4">
                  <div className="border rounded-3 p-3 h-100">
                    <div className="text-muted small">계정 상태</div>
                    <div className="fw-semibold">활성</div>
                  </div>
                </div>
                <div className="col-md-4">
                  <div className="border rounded-3 p-3 h-100">
                    <div className="text-muted small">역할</div>
                    <div className="fw-semibold">{loginRole}</div>
                  </div>
                </div>
                <div className="col-md-4">
                  <div className="border rounded-3 p-3 h-100">
                    <div className="text-muted small">로그인 방식</div>
                    <div className="fw-semibold">이메일</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="row g-4 mb-4">
          <div className="col-lg-6">
            <div className="card h-100 border-0 shadow-sm">
              <div className="card-body">
                <h5 className="card-title">API 연동 예제</h5>
                <p className="text-muted mb-3">/api/health 엔드포인트 상태를 확인합니다.</p>
                <div className="d-flex align-items-center gap-2">
                  <button className="btn btn-primary" onClick={checkHealth} disabled={healthStatus.loading}>
                    {healthStatus.loading ? "확인 중..." : "상태 확인"}
                  </button>
                  {healthStatus.data && (
                    <span className="badge text-bg-success">
                      {healthStatus.data.status} ({healthStatus.data.timestamp})
                    </span>
                  )}
                  {healthStatus.error && <span className="badge text-bg-danger">{healthStatus.error}</span>}
                </div>
              </div>
            </div>
          </div>
          <div className="col-lg-6">
            <div className="card h-100 border-0 shadow-sm">
              <div className="card-body">
                <h5 className="card-title">운영 지표</h5>
                <p className="text-muted">팀 별 응답률과 처리 시간을 한눈에 확인하세요.</p>
                <button className="btn btn-outline-primary btn-sm">리포트 다운로드</button>
              </div>
            </div>
          </div>
        </div>

        <div className="row g-4 mb-5">
          <div className="col-lg-6">
            <div className="card h-100 border-0 shadow-sm">
              <div className="card-body">
                <h5 className="card-title">초대 코드 관리</h5>
                <p className="text-muted">환자 계정에서 보호자 초대 코드를 생성합니다.</p>
                <div className="row g-2">
                  <div className="col-md-6">
                    <input
                      type="number"
                      min="1"
                      className="form-control"
                      value={inviteCodeForm.expires_in_minutes}
                      onChange={(event) =>
                        setInviteCodeForm({ expires_in_minutes: Number(event.target.value) || 1 })
                      }
                      placeholder="만료(분)"
                    />
                  </div>
                  <div className="col-md-6 d-grid">
                    <button className="btn btn-outline-primary" onClick={createInviteCode} disabled={inviteState.submitting}>
                      {inviteState.submitting ? "생성 중..." : "초대 코드 생성"}
                    </button>
                  </div>
                </div>
                <div className="d-flex gap-2 mt-3">
                  <button
                    className="btn btn-outline-secondary btn-sm"
                    onClick={deleteInviteCode}
                    disabled={inviteDeleteState.submitting}
                  >
                    초대 코드 폐기
                  </button>
                </div>
                {inviteState.data && (
                  <div className="alert alert-success mt-3">
                    코드: <strong>{inviteState.data.code}</strong>
                    <br />
                    만료: {formatDateTime(inviteState.data.expires_at)}
                  </div>
                )}
                {inviteState.error && <div className="alert alert-danger mt-3">{inviteState.error}</div>}
                {inviteDeleteState.error && <div className="alert alert-danger mt-3">{inviteDeleteState.error}</div>}
                {inviteDeleteState.success && <div className="alert alert-success mt-3">삭제 완료</div>}
              </div>
            </div>
          </div>
          <div className="col-lg-6">
            <div className="card h-100 border-0 shadow-sm">
              <div className="card-body">
                <h5 className="card-title">보호자 연동</h5>
                <p className="text-muted">보호자 계정에서 초대 코드를 입력해 연동하세요.</p>
                <form onSubmit={linkByInviteCode}>
                  <div className="d-flex gap-2">
                    <input
                      className="form-control"
                      value={linkForm.code}
                      onChange={(event) => setLinkForm({ code: event.target.value })}
                      placeholder="초대 코드 입력"
                      required
                    />
                    <button className="btn btn-primary" type="submit" disabled={linkAction.submitting}>
                      {linkAction.submitting ? "연동 중..." : "연동"}
                    </button>
                  </div>
                </form>
                {linkAction.error && <div className="alert alert-danger mt-3">{linkAction.error}</div>}
                {linkAction.success && <div className="alert alert-success mt-3">{linkAction.success}</div>}
              </div>
            </div>
          </div>
        </div>

        <div className="card border-0 shadow-sm mb-5">
          <div className="card-body">
            <div className="d-flex flex-column flex-lg-row justify-content-between gap-3">
              <div>
                <h5 className="card-title">연동 목록</h5>
                <p className="text-muted">환자-보호자 연동 상태를 확인하세요.</p>
              </div>
              <div className="d-flex gap-2">
                <button
                  className="btn btn-outline-primary btn-sm"
                  onClick={async () => {
                    setLinksState((prev) => ({ ...prev, loading: true, error: null }));
                    try {
                      const res = await authFetch(`${API_PREFIX}/users/links`);
                      if (!res.ok) {
                        const body = await safeJson(res);
                        throw new Error(formatApiError(body) || `status ${res.status}`);
                      }
                      const data = await res.json();
                      setLinksState({ loading: false, data, error: null });
                    } catch (error) {
                      setLinksState({ loading: false, data: null, error: error.message });
                    }
                  }}
                  disabled={linksState.loading}
                >
                  {linksState.loading ? "갱신 중..." : "연동 목록 갱신"}
                </button>
              </div>
            </div>
            {linksState.error && <div className="alert alert-danger mt-3">{linksState.error}</div>}
            {linksState.data && linksState.data.links?.length > 0 ? (
              <div className="table-responsive mt-3">
                <table className="table table-sm align-middle">
                  <thead>
                    <tr>
                      <th>환자</th>
                      <th>보호자</th>
                      <th>상태</th>
                      <th>연동일</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {linksState.data.links.map((link) => (
                      <tr key={link.link_id}>
                        <td>{link.patient_name || link.patient_user_id || link.patient_id}</td>
                        <td>{link.caregiver_name || link.caregiver_user_id}</td>
                        <td>{link.status}</td>
                        <td>{formatDateTime(link.linked_at)}</td>
                        <td>
                          <button
                            className="btn btn-outline-danger btn-sm"
                            onClick={() => unlinkPatient(link.link_id)}
                            disabled={linkAction.submitting}
                          >
                            연동 해제
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-muted mt-3">연동된 사용자가 없습니다.</div>
            )}
          </div>
        </div>

        <div className="row g-4 mb-5">
          <div className="col-lg-7">
            <div className="card h-100 border-0 shadow-sm">
              <div className="card-body">
                <div className="d-flex flex-column flex-lg-row justify-content-between gap-3">
                  <div>
                    <h5 className="card-title">알림 센터</h5>
                    <p className="text-muted">최근 알림과 읽음 상태를 관리하세요.</p>
                  </div>
                  <div className="d-flex gap-2">
                    <button
                      className="btn btn-outline-secondary btn-sm"
                      onClick={markAllNotificationsRead}
                      disabled={notificationsAction.submitting}
                    >
                      모두 읽음 처리
                    </button>
                  </div>
                </div>
                {notificationsState.error && <div className="alert alert-danger mt-3">{notificationsState.error}</div>}
                <div className="list-group mt-3">
                  {notificationsState.items.length === 0 && (
                    <div className="text-muted">알림이 없습니다.</div>
                  )}
                  {notificationsState.items.map((item) => (
                    <div
                      key={item.id}
                      className={`list-group-item d-flex justify-content-between align-items-start ${
                        item.read_at ? "" : "list-group-item-warning"
                      }`}
                    >
                      <div>
                        <div className="fw-semibold">{item.title || item.type}</div>
                        <div className="text-muted small">{item.body}</div>
                        <div className="text-muted small">{formatDateTime(item.created_at)}</div>
                      </div>
                      <div className="d-flex flex-column align-items-end gap-2">
                        <span className="badge text-bg-light">{item.read_at ? "읽음" : "미읽음"}</span>
                        {!item.read_at && (
                          <button
                            className="btn btn-outline-primary btn-sm"
                            onClick={() => markNotificationRead(item.id)}
                            disabled={notificationsAction.submitting}
                          >
                            읽음 처리
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {notificationsState.nextCursor && (
                  <div className="d-grid mt-3">
                    <button
                      className="btn btn-outline-primary"
                      onClick={loadMoreNotifications}
                      disabled={notificationsState.loading}
                    >
                      {notificationsState.loading ? "불러오는 중..." : "더 보기"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="col-lg-5">
            <div className="card h-100 border-0 shadow-sm">
              <div className="card-body">
                <h5 className="card-title">미읽음 알림</h5>
                <p className="text-muted">현재 읽지 않은 알림 개수를 확인합니다.</p>
                <div className="d-flex align-items-center gap-3">
                  <span className="display-6 fw-bold">{unreadCountState.count}</span>
                  <button
                    className="btn btn-outline-primary btn-sm"
                    onClick={async () => {
                      setUnreadCountState((prev) => ({ ...prev, loading: true, error: null }));
                      try {
                        const res = await authFetch(`${API_PREFIX}/notifications/unread-count`);
                        if (!res.ok) {
                          const body = await safeJson(res);
                          throw new Error(formatApiError(body) || `status ${res.status}`);
                        }
                        const body = await safeJson(res);
                        const data = body?.data || body;
                        setUnreadCountState({ loading: false, count: data?.count ?? 0, error: null });
                      } catch (error) {
                        setUnreadCountState({ loading: false, count: 0, error: error.message });
                      }
                    }}
                    disabled={unreadCountState.loading}
                  >
                    {unreadCountState.loading ? "갱신 중..." : "갱신"}
                  </button>
                </div>
                {unreadCountState.error && <div className="alert alert-danger mt-3">{unreadCountState.error}</div>}
                <hr />
                <h6 className="fw-semibold">알림 설정</h6>
                <form onSubmit={submitSettingsUpdate}>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="intake_reminder_dash"
                      name="intake_reminder"
                      checked={settingsState.data?.intake_reminder ?? false}
                      onChange={handleSettingsChange}
                    />
                    <label className="form-check-label" htmlFor="intake_reminder_dash">
                      복약 리마인드
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="missed_alert_dash"
                      name="missed_alert"
                      checked={settingsState.data?.missed_alert ?? false}
                      onChange={handleSettingsChange}
                    />
                    <label className="form-check-label" htmlFor="missed_alert_dash">
                      미복용 알림
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="ocr_done_dash"
                      name="ocr_done"
                      checked={settingsState.data?.ocr_done ?? false}
                      onChange={handleSettingsChange}
                    />
                    <label className="form-check-label" htmlFor="ocr_done_dash">
                      OCR 결과 알림
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="guide_ready_dash"
                      name="guide_ready"
                      checked={settingsState.data?.guide_ready ?? false}
                      onChange={handleSettingsChange}
                    />
                    <label className="form-check-label" htmlFor="guide_ready_dash">
                      가이드 준비 완료
                    </label>
                  </div>
                  <button className="btn btn-outline-primary btn-sm mt-3" type="submit" disabled={settingsState.submitting}>
                    {settingsState.submitting ? "저장 중..." : "설정 저장"}
                  </button>
                  {settingsState.error && <div className="alert alert-danger mt-3">{settingsState.error}</div>}
                  {settingsState.success && <div className="alert alert-success mt-3">저장 완료</div>}
                </form>
              </div>
            </div>
          </div>
        </div>

        <div className="card border-0 shadow-sm mb-5">
          <div className="card-body">
            <h5 className="card-title">수동 리마인드 발송</h5>
            <p className="text-muted">보호자가 환자에게 알림을 발송할 수 있습니다.</p>
            <form onSubmit={submitRemind}>
              <div className="row g-3">
                <div className="col-md-4">
                  <label className="form-label">환자 선택</label>
                  <select
                    className="form-select"
                    name="patient_id"
                    value={remindForm.patient_id}
                    onChange={handleRemindChange}
                    required
                  >
                    <option value="">환자 선택</option>
                    {linksState.data?.links?.map((link) => (
                      <option key={link.link_id} value={link.patient_id}>
                        {link.patient_name || link.patient_user_id || link.patient_id}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-4">
                  <label className="form-label">타입</label>
                  <input
                    className="form-control"
                    name="type"
                    value={remindForm.type}
                    onChange={handleRemindChange}
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label">제목</label>
                  <input
                    className="form-control"
                    name="title"
                    value={remindForm.title}
                    onChange={handleRemindChange}
                  />
                </div>
                <div className="col-md-8">
                  <label className="form-label">메시지</label>
                  <input
                    className="form-control"
                    name="message"
                    value={remindForm.message}
                    onChange={handleRemindChange}
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label">payload(JSON)</label>
                  <input
                    className="form-control"
                    name="payload"
                    value={remindForm.payload}
                    onChange={handleRemindChange}
                    placeholder='{"schedule_id":123}'
                  />
                </div>
              </div>
              <div className="d-flex gap-2 mt-3">
                <button className="btn btn-primary" type="submit" disabled={remindState.submitting}>
                  {remindState.submitting ? "전송 중..." : "리마인드 전송"}
                </button>
              </div>
              {remindState.error && <div className="alert alert-danger mt-3">{remindState.error}</div>}
              {remindState.success && <div className="alert alert-success mt-3">{remindState.success}</div>}
            </form>
          </div>
        </div>




      </main>
    </div>
  );
}

export default App;
