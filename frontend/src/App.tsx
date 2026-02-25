import { FormEvent, useEffect, useState } from "react";

import { fetchSummary, signUp } from "./api";
import type { SignUpPayload, SummaryResponse } from "./types";

const DEFAULT_SIGN_UP: SignUpPayload = {
  email: "",
  password: "",
  name: "",
  gender: "MALE",
  birth_date: "1990-01-01",
  phone_number: "",
};

export function App() {
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [form, setForm] = useState<SignUpPayload>(DEFAULT_SIGN_UP);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadSummary = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchSummary();
      setSummary(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load summary");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSummary();
  }, []);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      await signUp(form);
      setMessage("회원가입 완료: MySQL에 저장되었습니다.");
      setForm(DEFAULT_SIGN_UP);
      await loadSummary();
    } catch (e) {
      setError(e instanceof Error ? e.message : "회원가입 실패");
    }
  };

  return (
    <div className="page">
      <header className="header">
        <h1>AI Healthcare Frontend</h1>
        <p>독립 React 앱에서 백엔드 API를 호출해 데이터 상태를 확인합니다.</p>
      </header>

      <section className="panel">
        <div className="panel-head">
          <h2>회원가입 테스트</h2>
        </div>
        <form className="form-grid" onSubmit={onSubmit}>
          <input
            placeholder="email"
            value={form.email}
            onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
            required
          />
          <input
            placeholder="password"
            type="password"
            value={form.password}
            onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
            required
          />
          <input
            placeholder="name"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            required
          />
          <select value={form.gender} onChange={(e) => setForm((prev) => ({ ...prev, gender: e.target.value as SignUpPayload["gender"] }))}>
            <option value="MALE">MALE</option>
            <option value="FEMALE">FEMALE</option>
          </select>
          <input
            type="date"
            value={form.birth_date}
            onChange={(e) => setForm((prev) => ({ ...prev, birth_date: e.target.value }))}
            required
          />
          <input
            placeholder="phone_number (예: 01012345678)"
            value={form.phone_number}
            onChange={(e) => setForm((prev) => ({ ...prev, phone_number: e.target.value }))}
            required
          />
          <button type="submit">회원가입</button>
        </form>
        {message ? <p className="ok">{message}</p> : null}
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>테이블 건수 요약</h2>
          <button onClick={() => void loadSummary()} disabled={loading}>
            {loading ? "로딩..." : "새로고침"}
          </button>
        </div>
        <div className="cards">
          {summary &&
            Object.entries(summary.table_counts).map(([name, count]) => (
              <article className="card" key={name}>
                <span>{name}</span>
                <strong>{count}</strong>
              </article>
            ))}
        </div>
      </section>

      <section className="panel">
        <h2>최근 사용자</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Email</th>
              <th>Name</th>
              <th>Phone</th>
            </tr>
          </thead>
          <tbody>
            {summary?.recent_users.map((user) => (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.email}</td>
                <td>{user.name}</td>
                <td>{user.phone}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
