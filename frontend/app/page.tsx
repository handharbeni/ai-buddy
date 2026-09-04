"use client";

import { useState, useEffect, useRef, useCallback } from "react";

// ─── API config ────────────────────────────────────────────────────────────
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  data?: Record<string, unknown>[];
  tools_used?: string[];
  intent?: string;
  latency_ms?: number;
  llm_status?: string;
  row_count?: number;
  suggested_format?: string;
  metadata?: Record<string, unknown>;
  timestamp: number;
};

type Conversation = {
  id: string;
  title: string;
  messages: Message[];
  created_at: number;
  updated_at: number;
  message_count?: number;
};

type Format = { id: string; ext: string; mime: string; label?: string };

type User = {
  username: string;
  user_id: string;
  role: "ADMIN" | "SUPERVISOR" | "ANALYST" | "STAFF";
  display_name: string;
  scope: Record<string, unknown>;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};

type Branding = {
  app_name: string;
  app_short_name: string;
  tagline: string;
  institution: string;
  domain: string;
  version: string;
};

type View = "chat" | "users" | "settings" | "rag";

type RagDocument = {
  document_id: string;
  title: string;
  document_type: string;
  document_number: string;
  effective_date?: string;
  classification?: string;
  version?: string;
  chunks?: number;
};

const RAG_DOC_TYPES = ["PERDA", "PERGUB", "SOP", "SURAT_EDARAN", "INSTRUKSI", "NOTA_DINAS", "LAINNYA"];

const STORAGE_KEY = "bapenda_state_v2";

type AppState = {
  conversations: Record<string, Conversation>;
  activeConversationId: string | null;
};

function loadState(): AppState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { conversations: {}, activeConversationId: null };
}

function saveState(state: AppState) {
  try {
    // Only persist lightweight metadata; messages will be re-fetched from server
    const lightweight: AppState = {
      activeConversationId: state.activeConversationId,
      conversations: Object.fromEntries(
        Object.entries(state.conversations).map(([id, c]) => [
          id,
          { ...c, messages: [] }, // drop messages; server has them
        ])
      ),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lightweight));
  } catch {}
}

// ─── Component ────────────────────────────────────────────────────────────

export default function Home() {
  // Branding
  const [branding, setBranding] = useState<Branding>({
    app_name: "Local AI Platform",
    app_short_name: "LocalAI",
    tagline: "Internal AI for Data Intelligence",
    institution: "",
    domain: "data",
    version: "1.0.0",
  });

  // Auth
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  // Login form
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");

  // App state
  const [view, setView] = useState<View>("chat");
  const [state, setState] = useState<AppState>(loadState);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [devUsers, setDevUsers] = useState<any[]>([]);
  const [formats, setFormats] = useState<Format[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [systemStatus, setSystemStatus] = useState<{ backend: boolean; frontend: boolean; ollama: boolean } | null>(null);

  // User management
  const [users, setUsers] = useState<User[]>([]);
  const [userModal, setUserModal] = useState<null | { mode: "create" | "edit"; user: User | null }>(null);
  const [pwResetFor, setPwResetFor] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [renameModal, setRenameModal] = useState<null | { id: string; currentTitle: string }>(null);
  const [convTitle, setConvTitle] = useState<string>("");
  const [newTitleInput, setNewTitleInput] = useState<string>("");

  // RAG state
  const [ragDocs, setRagDocs] = useState<RagDocument[]>([]);
  const [ragLoading, setRagLoading] = useState(false);
  const [ragUploading, setRagUploading] = useState(false);
  const [ragUploadProgress, setRagUploadProgress] = useState("");
  const [ragDeleteId, setRagDeleteId] = useState<string | null>(null);
  const [ragUploadModal, setRagUploadModal] = useState(false);
  const [ragDragOver, setRagDragOver] = useState(false);
  const [ragSelectedFile, setRagSelectedFile] = useState<File | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── Derived ──────────────────────────────────────────────────────────
  const isAdmin = user?.role === "ADMIN";
  const activeConversation = state.activeConversationId
    ? state.conversations[state.activeConversationId]
    : null;
  const activeMsgs = activeConversation?.messages || [];

  // ── API helpers ──────────────────────────────────────────────────────
  const authHeaders = useCallback((): HeadersInit => {
    const t = token || localStorage.getItem("bapenda_token") || "";
    return { "Content-Type": "application/json", Authorization: `Bearer ${t}` };
  }, [token]);

  // ── Boot ─────────────────────────────────────────────────────────────
  useEffect(() => {
    const saved = localStorage.getItem("bapenda_token");
    if (saved) {
      setToken(saved);
      fetchUserInfo(saved);
    }
    // Load branding
    fetch(`${API}/api/v1/config`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) setBranding(d);
      })
      .catch(() => {});
    fetch(`${API}/api/v1/auth/users`)
      .then((r) => r.json())
      .then((d) => setDevUsers(d.users || []))
      .catch(() => {});
    fetch(`${API}/api/v1/download/formats`)
      .then((r) => r.json())
      .then((d) => setFormats(d.formats || []))
      .catch(() => {});
    checkSystemStatus();
    const interval = setInterval(checkSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll
  useEffect(() => {
    if (!loading) messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state, loading]);

  // Persist lightweight state
  useEffect(() => {
    saveState(state);
  }, [state]);

  // When token changes, load conversations + users
  useEffect(() => {
    if (token) {
      loadConversationsFromServer();
      if (isAdmin) loadUsers();
    }
  }, [token, isAdmin]);

  // ── Functions ────────────────────────────────────────────────────────
  const checkSystemStatus = async () => {
    const s = { backend: false, frontend: true, ollama: false };
    try { const r = await fetch(`${API}/health`); s.backend = r.ok; } catch {}
    try { const r = await fetch(`http://localhost:11434/api/tags`); s.ollama = r.ok; } catch {}
    setSystemStatus(s);
  };

  const fetchUserInfo = async (tok: string) => {
    try {
      const res = await fetch(`${API}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${tok}` } });
      if (res.ok) {
        const u = await res.json();
        setUser({ ...u, display_name: u.display_name || u.user_id });
      }
    } catch {}
  };

  const login = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Login failed (${res.status})`);
      }
      const data = await res.json();
      localStorage.setItem("bapenda_token", data.access_token);
      setToken(data.access_token);
      await fetchUserInfo(data.access_token);
    } catch (e: any) {
      setError(e.message || "Network error");
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("bapenda_token");
    setToken(null);
    setUser(null);
    setState({ conversations: {}, activeConversationId: null });
    setView("chat");
  };

  // ── Conversation ops (server-side) ──────────────────────────────────
  const loadConversationsFromServer = async () => {
    try {
      const res = await fetch(`${API}/api/v1/conversations`, { headers: authHeaders() });
      if (!res.ok) return;
      const convs = await res.json();
      setState((prev) => {
        const next: AppState = { conversations: {}, activeConversationId: prev.activeConversationId };
        for (const c of convs) {
          const existing = prev.conversations[c.id];
          next.conversations[c.id] = {
            id: c.id,
            title: c.title,
            created_at: c.created_at,
            updated_at: c.updated_at,
            message_count: c.message_count,
            messages: existing?.messages || [], // lazy-load later
          };
        }
        return next;
      });
    } catch {}
  };

  const loadConversationMessages = async (convId: string) => {
    try {
      const res = await fetch(`${API}/api/v1/conversations/${convId}`, { headers: authHeaders() });
      if (!res.ok) return;
      const data = await res.json();
      setState((prev) => {
        const conv = prev.conversations[convId];
        if (!conv) return prev;
        return {
          ...prev,
          conversations: {
            ...prev.conversations,
            [convId]: {
              ...conv,
              messages: data.messages.map((m: any) => ({
                id: m.id,
                role: m.role,
                content: m.content,
                metadata: m.metadata,
                timestamp: m.created_at,
              })),
            },
          },
        };
      });
    } catch {}
  };

  const startNewConversation = async () => {
    try {
      const res = await fetch(`${API}/api/v1/conversations`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ title: "" }),
      });
      if (!res.ok) throw new Error("Failed to create");
      const conv = await res.json();
      setState((prev) => ({
        conversations: {
          ...prev.conversations,
          [conv.id]: {
            id: conv.id,
            title: conv.title,
            messages: [],
            created_at: conv.created_at,
            updated_at: conv.updated_at,
            message_count: 0,
          },
        },
        activeConversationId: conv.id,
      }));
      setView("chat");
    } catch (e: any) {
      setError(e.message);
    }
  };

  const selectConversation = async (id: string) => {
    setState((prev) => ({ ...prev, activeConversationId: id }));
    const conv = state.conversations[id];
    if (conv && (!conv.messages || conv.messages.length === 0)) {
      await loadConversationMessages(id);
    }
  };

  const deleteConversation = async (id: string) => {
    if (!confirm("Delete this conversation?")) return;
    try {
      await fetch(`${API}/api/v1/conversations/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      setState((prev) => {
        const next = { ...prev, conversations: { ...prev.conversations } };
        delete next.conversations[id];
        if (prev.activeConversationId === id) {
          const remaining = Object.keys(next.conversations);
          next.activeConversationId = remaining[0] || null;
        }
        return next;
      });
    } catch (e: any) {
      setError(e.message);
    }
  };

  // Open rename modal
  const openRenameModal = (id: string, currentTitle: string) => {
    setRenameModal({ id, currentTitle });
    setNewTitleInput(currentTitle);
  };

  const closeRenameModal = () => setRenameModal(null);

  const handleRenameSubmit = async (newTitle: string) => {
    if (!renameModal) return;
    const convId = renameModal.id;
    if (!newTitle || newTitle.trim() === renameModal.currentTitle) {
      closeRenameModal();
      return;
    }
    try {
      await fetch(`${API}/api/v1/conversations/${convId}`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({ title: newTitle }),
      });
      setState((prev) => ({
        ...prev,
        conversations: {
          ...prev.conversations,
          [convId]: { ...prev.conversations[convId], title: newTitle },
        },
      }));
      closeRenameModal();
    } catch (e: any) {
      setError(e.message);
      closeRenameModal();
    }
  };


  // Modified: renameConversation now opens the modal
  const renameConversation = async (id: string) => {
    const conv = state.conversations[id];
    if (!conv) return;
    openRenameModal(id, conv.title);
  };

  // ── Message save (server-side) ──────────────────────────────────────
  const saveMessage = async (convId: string, msg: Message) => {
    try {
      await fetch(`${API}/api/v1/conversations/${convId}/messages`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          metadata: {
            data: msg.data,
            tools_used: msg.tools_used,
            intent: msg.intent,
            latency_ms: msg.latency_ms,
            llm_status: msg.llm_status,
            row_count: msg.row_count,
            suggested_format: msg.suggested_format,
          },
        }),
      });
    } catch {}
  };

  // ── Send query ──────────────────────────────────────────────────────
  const sendQuery = async () => {
    if (!query.trim() || loading) return;
    setError("");

    let convId = state.activeConversationId;
    // If no active conv, create one
    if (!convId) {
      try {
        const res = await fetch(`${API}/api/v1/conversations`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ title: query.slice(0, 50) }),
        });
        const conv = await res.json();
        convId = conv.id;
        setState((prev) => ({
          conversations: {
            ...prev.conversations,
            [convId!]: {
              id: convId!,
              title: conv.title,
              messages: [],
              created_at: conv.created_at,
              updated_at: conv.updated_at,
            },
          },
          activeConversationId: convId,
        }));
      } catch (e: any) {
        setError("Failed to create conversation");
        return;
      }
    }

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query.trim(),
      timestamp: Date.now(),
    };

    // Optimistic update
    setState((prev) => {
      const conv = prev.conversations[convId!];
      if (!conv) return prev;
      return {
        ...prev,
        conversations: {
          ...prev.conversations,
          [convId!]: { ...conv, messages: [...conv.messages, userMsg] },
        },
      };
    });
    saveMessage(convId, userMsg);
    const sentQuery = query;
    setQuery("");
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/v1/query`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ question: sentQuery, conversation_id: convId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.detail || `Query failed (${res.status})`);
      }
      const data = await res.json();
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer || "(no response)",
        data: data.data,
        tools_used: data.tools_used,
        intent: data.intent,
        latency_ms: data.metadata?.latency_ms,
        llm_status: data.metadata?.llm_status,
        row_count: data.metadata?.row_count,
        suggested_format: data.suggested_format || "docx",
        timestamp: Date.now(),
      };
      setState((prev) => {
        const conv = prev.conversations[convId!];
        if (!conv) return prev;
        return {
          ...prev,
          conversations: {
            ...prev.conversations,
            [convId!]: { ...conv, messages: [...conv.messages, assistantMsg] },
          },
        };
      });
      saveMessage(convId, assistantMsg);
    } catch (e: any) {
      const errMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `**Error:** ${e.message}`,
        timestamp: Date.now(),
      };
      setState((prev) => {
        const conv = prev.conversations[convId!];
        if (!conv) return prev;
        return {
          ...prev,
          conversations: {
            ...prev.conversations,
            [convId!]: { ...conv, messages: [...conv.messages, errMsg] },
          },
        };
      });
      saveMessage(convId, errMsg);
    } finally {
      setLoading(false);
    }
  };

  // ── Download ────────────────────────────────────────────────────────
  const downloadData = async (format: string, data: any[], filename: string) => {
    try {
      const res = await fetch(`${API}/api/v1/download`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ format, data, filename }),
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${filename}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError("Download error: " + err.message);
    }
  };

  const formatCell = (val: any): string => {
    if (val === null || val === undefined) return "—";
    if (typeof val === "number") {
      if (Number.isInteger(val)) return val.toLocaleString("id-ID");
      return val.toLocaleString("id-ID", { maximumFractionDigits: 2 });
    }
    if (typeof val === "object") return JSON.stringify(val);
    return String(val);
  };

  // ─── USERS CRUD ────────────────────────────────────────────────────
  const loadUsers = async () => {
    try {
      const res = await fetch(`${API}/api/v1/users`, { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch {}
  };

  const saveUser = async (mode: "create" | "edit", payload: any) => {
    const url = mode === "create"
      ? `${API}/api/v1/users`
      : `${API}/api/v1/users/${payload.username}`;
    const method = mode === "create" ? "POST" : "PATCH";
    try {
      const res = await fetch(url, {
        method,
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Save failed");
      }
      setUserModal(null);
      await loadUsers();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const resetPassword = async (username: string, newPassword: string) => {
    try {
      const res = await fetch(`${API}/api/v1/users/${username}/reset-password`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ new_password: newPassword }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Reset failed");
      }
      setPwResetFor(null);
      alert(`Password reset for ${username}`);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const doDeleteUser = async (username: string) => {
    try {
      const res = await fetch(`${API}/api/v1/users/${username}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Delete failed");
      }
      setDeleteConfirm(null);
      await loadUsers();
    } catch (e: any) {
      setError(e.message);
    }
  };

  // ─── RAG CRUD ─────────────────────────────────────────────────────────
  const loadRagDocuments = async () => {
    setRagLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/rag/documents`, { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        setRagDocs(data.documents || []);
      }
    } catch { /* RAG service unavailable */ }
    finally { setRagLoading(false); }
  };

  const uploadRagDocument = async (file: File, metadata: Record<string, string>) => {
    setRagUploading(true);
    setRagUploadProgress("Reading file…");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("metadata", JSON.stringify(metadata));
      setRagUploadProgress("Uploading & indexing…");
      const res = await fetch(`${API}/api/v1/rag/ingest`, {
        method: "POST",
        headers: { Authorization: authHeaders()["Authorization"] },
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Upload failed");
      }
      setRagUploadProgress("Done!");
      setTimeout(() => {
        setRagUploadModal(false);
        setRagUploading(false);
        setRagUploadProgress("");
        setRagSelectedFile(null);
        loadRagDocuments();
      }, 600);
    } catch (e: any) {
      setError(e.message);
      setRagUploading(false);
      setRagUploadProgress("");
    }
  };

  const deleteRagDocument = async (documentId: string) => {
    try {
      const res = await fetch(`${API}/api/v1/rag/documents/${documentId}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Delete failed");
      }
      setRagDeleteId(null);
      loadRagDocuments();
    } catch (e: any) {
      setError(e.message);
    }
  };

  // ─── LOGIN ──────────────────────────────────────────────────────
  if (!token) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "var(--bg-canvas)" }}>
        <div style={{ width: 380, padding: 32 }}>
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <div style={{ width: 48, height: 48, borderRadius: 12, background: "var(--accent)", display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 16, fontWeight: 600, fontSize: 20, color: "white" }}>{branding.app_short_name[0] || "L"}</div>
            <h1 style={{ fontSize: 22, fontWeight: 510, letterSpacing: "-0.5px" }}>{branding.app_name}</h1>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", marginTop: 4 }}>{branding.tagline}</p>
            {branding.institution && <p style={{ fontSize: 11, color: "var(--text-quaternary)", marginTop: 8 }}>{branding.institution}</p>}
          </div>

          <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border-primary)", borderRadius: 12, padding: 24, boxShadow: "var(--shadow-dialog)" }}>
            <h2 style={{ fontSize: 16, fontWeight: 510, marginBottom: 16 }}>Sign in</h2>
            <label style={{ display: "block", fontSize: 12, fontWeight: 510, color: "var(--text-secondary)", marginBottom: 6, letterSpacing: "-0.13px" }}>Username</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus style={{ width: "100%", marginBottom: 14 }} />
            <label style={{ display: "block", fontSize: 12, fontWeight: 510, color: "var(--text-secondary)", marginBottom: 6, letterSpacing: "-0.13px" }}>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === "Enter" && login()} style={{ width: "100%", marginBottom: 16 }} />
            <button onClick={login} disabled={loading} style={{ width: "100%", padding: "10px 16px", background: "var(--accent)", color: "white", borderRadius: 6, fontSize: 14, fontWeight: 510 }} onMouseEnter={(e) => (e.currentTarget.style.background = "var(--accent-hover)")} onMouseLeave={(e) => (e.currentTarget.style.background = "var(--accent)")}>
              {loading ? "Signing in..." : "Sign in"}
            </button>
            {error && <div style={{ marginTop: 14, padding: "8px 12px", background: "var(--danger-bg)", color: "var(--danger)", borderRadius: 6, fontSize: 13 }}>{error}</div>}
          </div>

          {devUsers.length > 0 && (
            <div style={{ marginTop: 16, padding: 14, background: "var(--bg-panel)", border: "1px solid var(--border-primary)", borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 510, color: "var(--text-quaternary)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 10 }}>Dev users (click to fill)</div>
              {devUsers.map((u) => (
                <div key={u.username} onClick={() => { setUsername(u.username); setPassword(u.username + "123"); }} style={{ padding: "6px 8px", cursor: "pointer", borderRadius: 4, fontSize: 13, display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-secondary)" }} onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")} onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                  <span><code style={{ color: "var(--text-primary)" }}>{u.username}</code> / {u.username}123</span>
                  <span style={{ fontSize: 11, color: "var(--text-tertiary)", padding: "2px 6px", background: "var(--bg-elevated)", borderRadius: 3 }}>{u.role}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ─── AUTHENTICATED LAYOUT ────────────────────────────────────────
  const conversationList = Object.values(state.conversations).sort(
    (a, b) => b.updated_at - a.updated_at
  );

  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--bg-canvas)", color: "var(--text-primary)" }}>
      {/* ── Sidebar ── */}
      <aside style={{ width: sidebarOpen ? 260 : 60, background: "var(--bg-panel)", borderRight: "1px solid var(--border-primary)", display: "flex", flexDirection: "column", transition: "width 0.15s" }}>
        <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: 8 }}>
          <button onClick={() => setSidebarOpen(!sidebarOpen)} style={{ width: 28, height: 28, borderRadius: 5, background: "transparent", border: "none", color: "var(--text-tertiary)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }} title={sidebarOpen ? "Collapse" : "Expand"}>
            <span style={{ fontSize: 14 }}>≡</span>
          </button>
          {sidebarOpen && <span style={{ fontSize: 13, fontWeight: 600 }}>{branding.app_short_name}</span>}
        </div>

        {/* Nav */}
        <nav style={{ padding: "8px 8px", display: "flex", flexDirection: "column", gap: 2 }}>
          <NavItem icon="💬" label="Chat" active={view === "chat"} open={sidebarOpen} onClick={() => setView("chat")} />
          {isAdmin && <NavItem icon="👥" label="Users" active={view === "users"} open={sidebarOpen} onClick={() => { setView("users"); loadUsers(); }} />}
          {isAdmin && <NavItem icon="📚" label="Knowledge" active={view === "rag"} open={sidebarOpen} onClick={() => { setView("rag"); loadRagDocuments(); }} />}
          <NavItem icon="⚙" label="Settings" active={view === "settings"} open={sidebarOpen} onClick={() => setView("settings")} />
        </nav>

        {/* Conversation list (only in chat view) */}
        {view === "chat" && sidebarOpen && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <div style={{ padding: "10px 14px 6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 11, fontWeight: 510, color: "var(--text-quaternary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Conversations</span>
              <button onClick={startNewConversation} title="New conversation" style={{ width: 22, height: 22, borderRadius: 4, background: "var(--accent)", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 400, flexShrink: 0, lineHeight: 1, border: "none", cursor: "pointer" }}>+</button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "0 6px" }}>
              {conversationList.length === 0 ? (
                <div style={{ padding: "12px", textAlign: "center", color: "var(--text-quaternary)", fontSize: 12 }}>
                  No conversations yet.<br />Click + to start.
                </div>
              ) : (
                conversationList.map((conv) => {
                  const isActive = conv.id === state.activeConversationId;
                  return (
                    <div
                      key={conv.id}
                      onClick={() => selectConversation(conv.id)}
                      style={{ padding: "8px 10px", cursor: "pointer", borderRadius: 5, background: isActive ? "var(--bg-hover)" : "transparent", display: "flex", alignItems: "center", gap: 6, marginBottom: 2, fontSize: 13 }}
                      onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = "var(--bg-subtle)"; }}
                      onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
                    >
                      <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {conv.title.startsWith("Conversation") ? `💬 ${conv.title}` : conv.title}
                      </span>
                      <span style={{ fontSize: 10, color: "var(--text-quaternary)", flexShrink: 0 }}>{conv.message_count || conv.messages?.length || 0}</span>
                      <button onClick={(e) => { e.stopPropagation(); renameConversation(conv.id); }} style={{ background: "transparent", border: "none", color: "var(--text-quaternary)", cursor: "pointer", padding: 0, fontSize: 11 }} title="Rename">✎</button>
                      <button onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }} style={{ background: "transparent", border: "none", color: "var(--text-quaternary)", cursor: "pointer", padding: 0, fontSize: 11 }} title="Delete">×</button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* User footer */}
        <div style={{ borderTop: "1px solid var(--border-subtle)", padding: "10px 12px", display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--accent)", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 600, flexShrink: 0 }}>
            {(user?.display_name || user?.user_id || "U").charAt(0).toUpperCase()}
          </div>
          {sidebarOpen && (
            <>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 510, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user?.display_name || user?.user_id}</div>
                <div style={{ fontSize: 10, color: "var(--text-quaternary)" }}>{user?.role}</div>
              </div>
              <button onClick={logout} title="Sign out" style={{ background: "transparent", border: "none", color: "var(--text-tertiary)", cursor: "pointer", fontSize: 14 }}>⎋</button>
            </>
          )}
        </div>
      </aside>

      {/* ── Main ── */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Header */}
        <div style={{ height: 48, padding: "0 20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--bg-panel)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h1 style={{ fontSize: 14, fontWeight: 510, color: "var(--text-primary)" }}>
                {view === "chat" && (activeConversation?.title || "New conversation")}
                {view === "users" && "User Management"}
                {view === "rag" && "Knowledge Base"}
                {view === "settings" && "Settings"}
              </h1>
            {view === "chat" && activeMsgs.length > 0 && <span style={{ fontSize: 11, color: "var(--text-quaternary)", padding: "2px 8px", background: "var(--bg-elevated)", borderRadius: 3 }}>{activeMsgs.length} messages</span>}
          </div>
          <div style={{ display: "flex", gap: 12, alignItems: "center", fontSize: 11, color: "var(--text-tertiary)" }}>
            {systemStatus && (
              <>
                <StatusDot label="API" ok={systemStatus.backend} />
                <StatusDot label="Ollama" ok={systemStatus.ollama} />
              </>
            )}
            <span style={{ fontSize: 10, color: "var(--text-quaternary)" }}>v{branding.version}</span>
          </div>
        </div>

        {/* View content */}
        {view === "chat" && (
          <ChatView
            activeConversation={activeConversation}
            activeMsgs={activeMsgs}
            loading={loading}
            query={query}
            setQuery={setQuery}
            sendQuery={sendQuery}
            formats={formats}
            downloadData={downloadData}
            formatCell={formatCell}
            inputRef={inputRef}
            messagesEndRef={messagesEndRef}
            branding={branding}
          />
        )}
        {view === "users" && isAdmin && (
          <UsersView
            users={users}
            currentUsername={user?.user_id || ""}
            onAdd={() => setUserModal({ mode: "create", user: null })}
            onEdit={(u) => setUserModal({ mode: "edit", user: u })}
            onResetPassword={(un) => setPwResetFor(un)}
            onDelete={(un) => setDeleteConfirm(un)}
          />
        )}
        {view === "settings" && (
          <SettingsView
            branding={branding}
            user={user}
            systemStatus={systemStatus}
            onLogout={logout}
            onClearConversations={() => {
              if (confirm("Clear all conversations locally? (server data is preserved)")) {
                setState({ conversations: {}, activeConversationId: null });
              }
            }}
          />
        )}
        {view === "rag" && isAdmin && (
          <RagView
            documents={ragDocs}
            loading={ragLoading}
            dragOver={ragDragOver}
            onDragOver={(e) => { e.preventDefault(); setRagDragOver(true); }}
            onDragLeave={() => setRagDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setRagDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) { setRagSelectedFile(f); setRagUploadModal(true); }
            }}
            onPickFile={(f) => { setRagSelectedFile(f); setRagUploadModal(true); }}
            onRefresh={loadRagDocuments}
            onDelete={(id) => setRagDeleteId(id)}
          />
        )}
      </main>

      {/* ── Modals ── */}
      {userModal && (
        <UserFormModal
          mode={userModal.mode}
          user={userModal.user}
          onClose={() => setUserModal(null)}
          onSave={saveUser}
        />
      )}
      {pwResetFor && (
        <PasswordResetModal
          username={pwResetFor}
          onClose={() => setPwResetFor(null)}
          onReset={(pw) => resetPassword(pwResetFor, pw)}
        />
      )}
      {deleteConfirm && (
        <ConfirmModal
          title="Delete user?"
          message={`This will permanently delete user "${deleteConfirm}". They will no longer be able to log in. This cannot be undone.`}
          confirmLabel="Delete"
          danger
          onCancel={() => setDeleteConfirm(null)}
          onConfirm={() => doDeleteUser(deleteConfirm)}
        />
      )}
      {renameModal && (
        <Modal onClose={closeRenameModal}>
          <h3 style={{ fontSize: 16, fontWeight: 510, marginBottom: 12 }}>
            Rename conversation
          </h3>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
            Current title: <strong>{renameModal.currentTitle}</strong>
          </p>
          <FormField label="New title">
            <input
              type="text"
              value={newTitleInput}
              onChange={(e) => setNewTitleInput(e.target.value)}
              autoFocus
              style={{
                width: "100%",
                padding: "8px 10px",
                background: "var(--bg-canvas)",
                border: "1px solid var(--border-primary)",
                borderRadius: 5,
                color: "var(--text-primary)",
                fontSize: 13,
              }}
            />
          </FormField>
          <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
            <button onClick={closeRenameModal} style={{ padding: "8px 14px", background: "transparent", border: "1px solid var(--border-primary)", borderRadius: 5, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>Cancel</button>
            <button onClick={() => handleRenameSubmit(newTitleInput)} style={{ padding: "8px 14px", background: "var(--accent)", border: "none", borderRadius: 5, fontSize: 13, color: "white", cursor: "pointer", fontWeight: 510 }}>Save</button>
          </div>
        </Modal>
      )}
      {ragUploadModal && ragSelectedFile && (
        <RagUploadModal
          file={ragSelectedFile}
          uploading={ragUploading}
          progress={ragUploadProgress}
          onClose={() => { if (!ragUploading) { setRagUploadModal(false); setRagSelectedFile(null); } }}
          onSubmit={(meta) => uploadRagDocument(ragSelectedFile, meta)}
        />
      )}
      {ragDeleteId && (
        <ConfirmModal
          title="Delete document?"
          message={`This will permanently delete document "${ragDeleteId}" and all its indexed chunks. This cannot be undone.`}
          confirmLabel="Delete"
          danger
          onCancel={() => setRagDeleteId(null)}
          onConfirm={() => deleteRagDocument(ragDeleteId)}
        />
      )}

      {/* Global error toast */}
      {error && (
        <div style={{ position: "fixed", top: 16, right: 16, padding: "10px 14px", background: "var(--danger-bg)", color: "var(--danger)", borderRadius: 6, fontSize: 13, boxShadow: "var(--shadow-dialog)", zIndex: 100, maxWidth: 360, display: "flex", gap: 10, alignItems: "center" }}>
          <span style={{ flex: 1 }}>{error}</span>
          <button onClick={() => setError("")} style={{ background: "transparent", border: "none", color: "var(--danger)", cursor: "pointer", fontSize: 16 }}>×</button>
        </div>
      )}
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────

function NavItem({ icon, label, active, open, onClick }: { icon: string; label: string; active: boolean; open: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: open ? "8px 10px" : "8px 0",
        background: active ? "var(--bg-hover)" : "transparent",
        color: active ? "var(--text-primary)" : "var(--text-secondary)",
        border: "none",
        borderRadius: 5,
        cursor: "pointer",
        fontSize: 13,
        textAlign: "left",
        display: "flex",
        alignItems: "center",
        gap: 8,
        justifyContent: open ? "flex-start" : "center",
        fontWeight: active ? 510 : 400,
      }}
      onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "var(--bg-subtle)"; }}
      onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
    >
      <span style={{ fontSize: 14 }}>{icon}</span>
      {open && <span>{label}</span>}
    </button>
  );
}

function StatusDot({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: ok ? "var(--success)" : "var(--danger)" }} />
      {label}
    </span>
  );
}

// ─── Chat View ────────────────────────────────────────────────────────────

function ChatView({ activeConversation, activeMsgs, loading, query, setQuery, sendQuery, formats, downloadData, formatCell, inputRef, messagesEndRef, branding }: any) {
  return (
    <>
      <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px" }}>
        {activeMsgs.length === 0 ? (
          <div style={{ maxWidth: 600, margin: "60px auto", textAlign: "center" }}>
            <div style={{ fontSize: 28, marginBottom: 12 }}>👋</div>
            <h2 style={{ fontSize: 18, fontWeight: 510, marginBottom: 6 }}>Hi, I'm your {branding.app_name} assistant</h2>
            <p style={{ color: "var(--text-tertiary)", fontSize: 13, lineHeight: 1.6, marginBottom: 24 }}>
              Ask questions about your data in natural language. I'll query the right databases and synthesize an answer with sources.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, textAlign: "left" }}>
              {[
                "What's the tax revenue this month?",
                "Show me top 5 taxpayers with arrears",
                "Hotel tax growth year-over-year",
                "Latest regulations on restaurant tax",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => { setQuery(q); }}
                  style={{ padding: "10px 12px", background: "var(--bg-panel)", border: "1px solid var(--border-primary)", borderRadius: 8, fontSize: 12, color: "var(--text-secondary)", cursor: "pointer", textAlign: "left" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "var(--bg-panel)")}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ maxWidth: 800, margin: "0 auto" }}>
            {activeMsgs.map((msg: Message) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                formats={formats}
                onDownload={downloadData}
                formatCell={formatCell}
              />
            ))}
            {loading && (
              <div style={{ display: "flex", gap: 10, padding: "12px 14px", marginTop: 8 }}>
                <div style={{ width: 26, height: 26, borderRadius: "50%", background: "var(--accent)", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 600, flexShrink: 0 }}>AI</div>
                <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "10px 14px", background: "var(--bg-panel)", border: "1px solid var(--border-subtle)", borderRadius: 10, color: "var(--text-tertiary)", fontSize: 13 }}>
                  <span>Thinking</span>
                  <span className="typing-dots">...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div style={{ padding: "12px 20px 20px", borderTop: "1px solid var(--border-subtle)", background: "var(--bg-panel)" }}>
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <div style={{ display: "flex", gap: 8, background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 10, padding: "10px 12px" }}>
            <textarea
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendQuery();
                }
              }}
              placeholder="Ask anything about your data..."
              rows={1}
              style={{ flex: 1, resize: "none", border: "none", background: "transparent", color: "var(--text-primary)", fontSize: 14, fontFamily: "inherit", outline: "none" }}
            />
            <button
              onClick={sendQuery}
              disabled={!query.trim() || loading}
              style={{ padding: "6px 14px", background: query.trim() && !loading ? "var(--accent)" : "var(--bg-elevated)", color: query.trim() && !loading ? "white" : "var(--text-quaternary)", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 510, cursor: query.trim() && !loading ? "pointer" : "not-allowed" }}
            >
              Send
            </button>
          </div>
          <div style={{ marginTop: 6, fontSize: 10, color: "var(--text-quaternary)", textAlign: "center" }}>
            Press Enter to send, Shift+Enter for new line
          </div>
        </div>
      </div>
    </>
  );
}

function MessageBubble({ msg, formats, onDownload, formatCell }: any) {
  const [showData, setShowData] = useState(false);
  const isUser = msg.role === "user";
  const data = msg.data;
  const cols: string[] = data && data.length > 0 ? Object.keys(data[0]) : [];
  const filename = (activeConv: any) => `data_${Date.now()}`;

  return (
    <div style={{ display: "flex", gap: 10, padding: "10px 0", flexDirection: isUser ? "row-reverse" : "row" }}>
      <div style={{ width: 26, height: 26, borderRadius: "50%", background: isUser ? "var(--bg-elevated)" : "var(--accent)", color: isUser ? "var(--text-secondary)" : "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 600, flexShrink: 0 }}>
        {isUser ? (msg.metadata?.user || "U").charAt(0).toUpperCase() : "AI"}
      </div>
      <div style={{ maxWidth: "78%", padding: "10px 14px", background: isUser ? "var(--accent)" : "var(--bg-panel)", color: isUser ? "white" : "var(--text-primary)", borderRadius: 10, border: isUser ? "none" : "1px solid var(--border-subtle)", fontSize: 13, lineHeight: 1.55, whiteSpace: "pre-wrap" }}>
        <div>{msg.content}</div>

        {/* Metadata pills */}
        {!isUser && (msg.intent || msg.tools_used?.length || msg.latency_ms) && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
            {msg.intent && <Pill>{msg.intent}</Pill>}
            {msg.tools_used?.map((t: string) => <Pill key={t}>{t}</Pill>)}
            {msg.latency_ms && <Pill>{(msg.latency_ms / 1000).toFixed(1)}s</Pill>}
            {msg.row_count != null && <Pill>{msg.row_count} rows</Pill>}
          </div>
        )}

        {/* Data preview + download */}
        {data && data.length > 0 && (
          <div style={{ marginTop: 10, background: "var(--bg-canvas)", border: "1px solid var(--border-subtle)", borderRadius: 6, padding: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 11, fontWeight: 510, color: "var(--text-secondary)" }}>{data.length} rows × {cols.length} columns</span>
              <button onClick={() => setShowData(!showData)} style={{ background: "transparent", border: "none", color: "var(--text-tertiary)", fontSize: 11, cursor: "pointer" }}>{showData ? "Hide" : "Show"} data</button>
            </div>
            {showData && (
              <div style={{ overflowX: "auto", maxHeight: 360, overflowY: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                  <thead>
                    <tr>
                      {cols.map((c) => <th key={c} style={{ textAlign: "left", padding: "4px 6px", background: "var(--bg-elevated)", color: "var(--text-secondary)", fontWeight: 510, position: "sticky", top: 0, borderBottom: "1px solid var(--border-subtle)" }}>{c}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {data.slice(0, 100).map((row: any, i: number) => (
                      <tr key={i} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        {cols.map((c) => <td key={c} style={{ padding: "4px 6px", color: "var(--text-primary)" }}>{formatCell(row[c])}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {data.length > 100 && <div style={{ textAlign: "center", padding: 6, color: "var(--text-quaternary)", fontSize: 11 }}>+ {data.length - 100} more rows</div>}
              </div>
            )}
            <div style={{ display: "flex", gap: 6, marginTop: 8, paddingTop: 8, borderTop: "1px solid var(--border-subtle)" }}>
              {formats.slice(0, 5).map((f: Format) => (
                <button key={f.id} onClick={() => onDownload(f.id, data, `export_${Date.now()}`)} style={{ padding: "3px 8px", background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)", borderRadius: 4, fontSize: 11, color: "var(--text-secondary)", cursor: "pointer" }} title={`Download as ${f.id.toUpperCase()}`}>↓ {f.id.toUpperCase()}</button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return <span style={{ display: "inline-block", padding: "2px 7px", background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)", borderRadius: 10, fontSize: 10, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{children}</span>;
}

// ─── Users View ───────────────────────────────────────────────────────────

function UsersView({ users, currentUsername, onAdd, onEdit, onResetPassword, onDelete }: any) {
  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "24px 32px" }}>
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 510, marginBottom: 4 }}>Users</h2>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Manage user accounts, roles, and access.</p>
          </div>
          <button onClick={onAdd} style={{ padding: "8px 16px", background: "var(--accent)", color: "white", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 510, cursor: "pointer" }}>+ Add user</button>
        </div>

        {users.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-quaternary)", background: "var(--bg-panel)", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
            No users found.
          </div>
        ) : (
          <div style={{ background: "var(--bg-panel)", borderRadius: 8, border: "1px solid var(--border-subtle)", overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--bg-elevated)" }}>
                  <Th>User</Th>
                  <Th>Role</Th>
                  <Th>Status</Th>
                  <Th>Created</Th>
                  <Th align="right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {users.map((u: User) => {
                  const isCurrentUser = u.username === currentUsername;
                  return (
                    <tr key={u.username} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                      <Td>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <div style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--accent)", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 600 }}>{u.display_name.charAt(0).toUpperCase()}</div>
                          <div>
                            <div style={{ fontWeight: 510, fontSize: 13 }}>{u.display_name} {isCurrentUser && <span style={{ fontSize: 10, color: "var(--text-quaternary)", marginLeft: 6 }}>(you)</span>}</div>
                            <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>@{u.username}</div>
                          </div>
                        </div>
                      </Td>
                      <Td><RoleBadge role={u.role} /></Td>
                      <Td>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, color: u.is_active ? "var(--success)" : "var(--text-quaternary)" }}>
                          <span style={{ width: 6, height: 6, borderRadius: "50%", background: u.is_active ? "var(--success)" : "var(--text-quaternary)" }} />
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </Td>
                      <Td><span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</span></Td>
                      <Td align="right">
                        <ActionButton onClick={() => onEdit(u)} title="Edit user">✎</ActionButton>
                        <ActionButton onClick={() => onResetPassword(u.username)} title="Reset password">🔑</ActionButton>
                        {!isCurrentUser && <ActionButton onClick={() => onDelete(u.username)} title="Delete user" danger>🗑</ActionButton>}
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function Th({ children, align }: { children: React.ReactNode; align?: "right" }) {
  return <th style={{ textAlign: align || "left", padding: "10px 14px", fontSize: 11, fontWeight: 510, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>{children}</th>;
}
function Td({ children, align }: { children: React.ReactNode; align?: "right" }) {
  return <td style={{ padding: "10px 14px", textAlign: align || "left", verticalAlign: "middle" }}>{children}</td>;
}
function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, { bg: string; fg: string }> = {
    ADMIN: { bg: "rgba(99, 102, 241, 0.12)", fg: "var(--accent)" },
    SUPERVISOR: { bg: "rgba(245, 158, 11, 0.12)", fg: "#F59E0B" },
    ANALYST: { bg: "rgba(16, 185, 129, 0.12)", fg: "#10B981" },
    STAFF: { bg: "rgba(107, 114, 128, 0.12)", fg: "var(--text-tertiary)" },
  };
  const c = colors[role] || colors.STAFF;
  return <span style={{ display: "inline-block", padding: "2px 8px", background: c.bg, color: c.fg, borderRadius: 3, fontSize: 11, fontWeight: 510 }}>{role}</span>;
}
function ActionButton({ children, onClick, title, danger }: { children: React.ReactNode; onClick: () => void; title: string; danger?: boolean }) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        padding: "4px 8px",
        background: "transparent",
        border: "1px solid var(--border-subtle)",
        borderRadius: 4,
        fontSize: 12,
        color: danger ? "var(--danger)" : "var(--text-secondary)",
        cursor: "pointer",
        marginLeft: 4,
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = danger ? "var(--danger-bg)" : "var(--bg-hover)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
    >
      {children}
    </button>
  );
}

// ─── Settings View ────────────────────────────────────────────────────────

function SettingsView({ branding, user, systemStatus, onLogout, onClearConversations }: any) {
  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "24px 32px" }}>
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
        <h2 style={{ fontSize: 18, fontWeight: 510, marginBottom: 4 }}>Settings</h2>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 24 }}>Application configuration and account information.</p>

        <Section title="About">
          <Row label="Application" value={branding.app_name} />
          <Row label="Tagline" value={branding.tagline} />
          <Row label="Institution" value={branding.institution || "—"} />
          <Row label="Domain" value={branding.domain} />
          <Row label="Version" value={branding.version} />
        </Section>

        <Section title="System status">
          {systemStatus ? (
            <>
              <Row label="Backend API" value={systemStatus.backend ? "Online" : "Offline"} ok={systemStatus.backend} />
              <Row label="Ollama LLM" value={systemStatus.ollama ? "Online" : "Offline"} ok={systemStatus.ollama} />
              <Row label="Frontend" value="Online" ok={true} />
            </>
          ) : <Row label="Status" value="Checking..." />}
        </Section>

        <Section title="Account">
          <Row label="Username" value={user?.user_id || "—"} />
          <Row label="Display name" value={user?.display_name || "—"} />
          <Row label="Role" value={user?.role || "—"} />
        </Section>

        <Section title="Data">
          <button onClick={onClearConversations} style={{ padding: "8px 14px", background: "transparent", border: "1px solid var(--border-primary)", borderRadius: 6, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>Clear local conversation cache</button>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 8 }}>Server-side conversation history is preserved. Only clears local browser cache.</p>
        </Section>

        <Section title="Session">
          <button onClick={onLogout} style={{ padding: "8px 14px", background: "var(--danger-bg)", border: "1px solid var(--danger)", borderRadius: 6, fontSize: 13, color: "var(--danger)", cursor: "pointer" }}>Sign out</button>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 24, background: "var(--bg-panel)", border: "1px solid var(--border-subtle)", borderRadius: 8, padding: 16 }}>
      <h3 style={{ fontSize: 13, fontWeight: 510, color: "var(--text-secondary)", marginBottom: 12 }}>{title}</h3>
      {children}
    </div>
  );
}
function Row({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid var(--border-subtle)", fontSize: 13 }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ fontFamily: "monospace", fontSize: 12, color: ok === true ? "var(--success)" : ok === false ? "var(--danger)" : "var(--text-primary)" }}>{value}</span>
    </div>
  );
}

// ─── Modals ───────────────────────────────────────────────────────────────

function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200 }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--bg-panel)", borderRadius: 10, padding: 24, minWidth: 400, maxWidth: 560, boxShadow: "var(--shadow-dialog)" }}>
        {children}
      </div>
    </div>
  );
}

function UserFormModal({ mode, user, onClose, onSave }: { mode: "create" | "edit"; user: User | null; onClose: () => void; onSave: (mode: "create" | "edit", payload: any) => void }) {
  const [username, setUsername] = useState(user?.username || "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<User["role"]>(user?.role || "STAFF");
  const [displayName, setDisplayName] = useState(user?.display_name || "");
  const [isActive, setIsActive] = useState(user?.is_active ?? true);

  const submit = () => {
    if (mode === "create") {
      if (!username || !password) return alert("Username and password required");
      onSave(mode, { username, password, role, display_name: displayName, scope: { regions: ["ALL"], tax_types: ["ALL"], departments: ["ALL"], own_taxpayers: false } });
    } else {
      onSave(mode, { username, role, display_name: displayName, is_active: isActive, scope: user?.scope });
    }
  };

  return (
    <Modal onClose={onClose}>
      <h3 style={{ fontSize: 16, fontWeight: 510, marginBottom: 16 }}>{mode === "create" ? "Add user" : `Edit ${user?.display_name}`}</h3>
      <FormField label="Username">
        <input value={username} onChange={(e) => setUsername(e.target.value)} disabled={mode === "edit"} style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }} />
      </FormField>
      {mode === "create" && (
        <FormField label="Password">
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }} />
        </FormField>
      )}
      <FormField label="Display name">
        <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }} />
      </FormField>
      <FormField label="Role">
        <select value={role} onChange={(e) => setRole(e.target.value as any)} disabled={mode === "edit" && user?.username === "admin"} style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }}>
          <option value="STAFF">STAFF</option>
          <option value="ANALYST">ANALYST</option>
          <option value="SUPERVISOR">SUPERVISOR</option>
          <option value="ADMIN">ADMIN</option>
        </select>
      </FormField>
      {mode === "edit" && (
        <FormField label="Status">
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} disabled={user?.username === "admin"} />
            Active
          </label>
        </FormField>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
        <button onClick={onClose} style={{ padding: "8px 14px", background: "transparent", border: "1px solid var(--border-primary)", borderRadius: 5, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>Cancel</button>
        <button onClick={submit} style={{ padding: "8px 14px", background: "var(--accent)", border: "none", borderRadius: 5, fontSize: 13, color: "white", cursor: "pointer", fontWeight: 510 }}>{mode === "create" ? "Create" : "Save"}</button>
      </div>
    </Modal>
  );
}

function PasswordResetModal({ username, onClose, onReset }: { username: string; onClose: () => void; onReset: (pw: string) => void }) {
  const [pw, setPw] = useState("");
  return (
    <Modal onClose={onClose}>
      <h3 style={{ fontSize: 16, fontWeight: 510, marginBottom: 12 }}>Reset password</h3>
      <p style={{ fontSize: 13, color: "var(--text-tertiary)", marginBottom: 16 }}>Set a new password for <strong>{username}</strong></p>
      <FormField label="New password">
        <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoFocus style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }} />
      </FormField>
      <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
        <button onClick={onClose} style={{ padding: "8px 14px", background: "transparent", border: "1px solid var(--border-primary)", borderRadius: 5, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>Cancel</button>
        <button onClick={() => pw && onReset(pw)} disabled={!pw} style={{ padding: "8px 14px", background: pw ? "var(--accent)" : "var(--bg-elevated)", border: "none", borderRadius: 5, fontSize: 13, color: "white", cursor: pw ? "pointer" : "not-allowed", fontWeight: 510 }}>Reset</button>
      </div>
    </Modal>
  );
}

function ConfirmModal({ title, message, confirmLabel, danger, onCancel, onConfirm }: { title: string; message: string; confirmLabel: string; danger?: boolean; onCancel: () => void; onConfirm: () => void }) {
  return (
    <Modal onClose={onCancel}>
      <h3 style={{ fontSize: 16, fontWeight: 510, marginBottom: 8 }}>{title}</h3>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 20 }}>{message}</p>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button onClick={onCancel} style={{ padding: "8px 14px", background: "transparent", border: "1px solid var(--border-primary)", borderRadius: 5, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>Cancel</button>
        <button onClick={onConfirm} style={{ padding: "8px 14px", background: danger ? "var(--danger)" : "var(--accent)", border: "none", borderRadius: 5, fontSize: 13, color: "white", cursor: "pointer", fontWeight: 510 }}>{confirmLabel}</button>
      </div>
    </Modal>
  );
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "block", fontSize: 11, fontWeight: 510, color: "var(--text-secondary)", marginBottom: 4 }}>{label}</label>
      {children}
    </div>
  );
}

// ─── RAG View ─────────────────────────────────────────────────────────────

function RagView({ documents, loading, dragOver, onDragOver, onDragLeave, onDrop, onPickFile, onRefresh, onDelete }: any) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "24px 32px" }}>
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 510, marginBottom: 4 }}>Knowledge Base</h2>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Upload regulation documents for semantic search.</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={onRefresh} style={{ padding: "8px 14px", background: "transparent", border: "1px solid var(--border-primary)", borderRadius: 6, fontSize: 13, color: "var(--text-primary)", cursor: "pointer" }}>↻ Refresh</button>
            <button onClick={() => fileInputRef.current?.click()} style={{ padding: "8px 16px", background: "var(--accent)", color: "white", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 510, cursor: "pointer" }}>+ Upload document</button>
            <input ref={fileInputRef} type="file" accept=".pdf,.docx,.md,.txt" style={{ display: "none" }} onChange={(e) => { const f = e.target.files?.[0]; if (f) onPickFile(f); e.currentTarget.value = ""; }} />
          </div>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? "var(--accent)" : "var(--border-primary)"}`,
            background: dragOver ? "var(--bg-hover)" : "var(--bg-panel)",
            borderRadius: 8,
            padding: 32,
            textAlign: "center",
            cursor: "pointer",
            marginBottom: 20,
            transition: "all 0.15s",
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 8 }}>📄</div>
          <div style={{ fontSize: 14, fontWeight: 510, marginBottom: 4 }}>Drop files here, or click to browse</div>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Supports PDF, DOCX, MD, TXT</div>
        </div>

        {/* Documents table */}
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-tertiary)" }}>Loading…</div>
        ) : documents.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-quaternary)", background: "var(--bg-panel)", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
            No documents indexed yet. Upload your first document above.
          </div>
        ) : (
          <div style={{ background: "var(--bg-panel)", borderRadius: 8, border: "1px solid var(--border-subtle)", overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--bg-elevated)" }}>
                  <Th>Title</Th>
                  <Th>Type</Th>
                  <Th>Number</Th>
                  <Th align="right">Chunks</Th>
                  <Th>Version</Th>
                  <Th align="right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {documents.map((d: RagDocument) => (
                  <tr key={d.document_id} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <Td>
                      <div style={{ fontWeight: 510, fontSize: 13 }}>{d.title || "—"}</div>
                      <div style={{ fontSize: 10, color: "var(--text-quaternary)", fontFamily: "monospace" }}>{d.document_id}</div>
                    </Td>
                    <Td><span style={{ display: "inline-block", padding: "2px 8px", background: "var(--bg-elevated)", color: "var(--text-secondary)", borderRadius: 3, fontSize: 11, fontWeight: 510 }}>{d.document_type || "—"}</span></Td>
                    <Td><span style={{ fontSize: 12, color: "var(--text-secondary)", fontFamily: "monospace" }}>{d.document_number || "—"}</span></Td>
                    <Td align="right"><span style={{ fontSize: 12 }}>{d.chunks ?? "—"}</span></Td>
                    <Td><span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{d.version || "—"}</span></Td>
                    <Td align="right">
                      <ActionButton onClick={() => onDelete(d.document_id)} title="Delete document" danger>🗑</ActionButton>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function RagUploadModal({ file, uploading, progress, onClose, onSubmit }: { file: File; uploading: boolean; progress: string; onClose: () => void; onSubmit: (meta: Record<string, string>) => void }) {
  const [title, setTitle] = useState(file.name.replace(/\.[^.]+$/, ""));
  const [docType, setDocType] = useState("PERDA");
  const [docNumber, setDocNumber] = useState("");
  const [authority, setAuthority] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().slice(0, 10));
  const [version, setVersion] = useState("v1.0");

  const submit = () => {
    if (!title || !docNumber) return alert("Title and document number required");
    onSubmit({
      title,
      document_type: docType,
      document_number: docNumber,
      issuing_authority: authority || "Unknown",
      effective_date: effectiveDate,
      version,
    });
  };

  return (
    <Modal onClose={onClose}>
      <h3 style={{ fontSize: 16, fontWeight: 510, marginBottom: 4 }}>Index document</h3>
      <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 16 }}>
        <strong>{file.name}</strong> · {(file.size / 1024).toFixed(1)} KB
      </p>
      <FormField label="Title">
        <input value={title} onChange={(e) => setTitle(e.target.value)} disabled={uploading} style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }} />
      </FormField>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <FormField label="Document type">
          <select value={docType} onChange={(e) => setDocType(e.target.value)} disabled={uploading} style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }}>
            {RAG_DOC_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </FormField>
        <FormField label="Document number">
          <input value={docNumber} onChange={(e) => setDocNumber(e.target.value)} disabled={uploading} placeholder="e.g. 12/2024" style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }} />
        </FormField>
      </div>
      <FormField label="Issuing authority">
        <input value={authority} onChange={(e) => setAuthority(e.target.value)} disabled={uploading} placeholder="e.g. DPRD Kota Bandung" style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }} />
      </FormField>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <FormField label="Effective date">
          <input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} disabled={uploading} style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }} />
        </FormField>
        <FormField label="Version">
          <input value={version} onChange={(e) => setVersion(e.target.value)} disabled={uploading} style={{ width: "100%", padding: "8px 10px", background: "var(--bg-canvas)", border: "1px solid var(--border-primary)", borderRadius: 5, color: "var(--text-primary)", fontSize: 13 }} />
        </FormField>
      </div>
      {uploading && (
        <div style={{ marginTop: 8, padding: "10px 12px", background: "var(--bg-elevated)", borderRadius: 5, fontSize: 12, color: "var(--text-secondary)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 12, height: 12, borderRadius: "50%", border: "2px solid var(--accent)", borderTopColor: "transparent", animation: "spin 0.8s linear infinite" }} />
            {progress}
          </div>
        </div>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
        <button onClick={onClose} disabled={uploading} style={{ padding: "8px 14px", background: "transparent", border: "1px solid var(--border-primary)", borderRadius: 5, fontSize: 13, color: "var(--text-primary)", cursor: uploading ? "not-allowed" : "pointer", opacity: uploading ? 0.5 : 1 }}>Cancel</button>
        <button onClick={submit} disabled={uploading} style={{ padding: "8px 14px", background: "var(--accent)", border: "none", borderRadius: 5, fontSize: 13, color: "white", cursor: uploading ? "not-allowed" : "pointer", fontWeight: 510, opacity: uploading ? 0.7 : 1 }}>{uploading ? "Uploading…" : "Index"}</button>
      </div>
    </Modal>
  );
}
