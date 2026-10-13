import {
  Link,
  NavLink,
  Navigate,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import {
  Bell,
  BriefcaseBusiness,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  Menu,
  Network,
  Send,
  ShieldCheck,
  Compass,
  UserRound,
  X,
} from "lucide-react";
import { useMe } from "../lib/query";
import { api } from "../lib/api";
import { session, useSession } from "../lib/session";
import { initials } from "../lib/format";
import { ErrorState, Loading } from "./ui";

const navigation = [
  { to: "/", label: "Tổng quan", icon: LayoutDashboard, end: true },
  { to: "/explore", label: "Khám phá việc làm", icon: Compass },
  { to: "/jobs", label: "Tìm việc làm", icon: BriefcaseBusiness },
  { to: "/network", label: "Mạng lưới", icon: Network },
  { to: "/referrals", label: "Yêu cầu giới thiệu", icon: Send },
  { to: "/profile", label: "Hồ sơ của tôi", icon: UserRound },
];
export function Shell() {
  const current = useSession(),
    location = useLocation(),
    navigate = useNavigate();
  const [menu, setMenu] = useState(false);
  const [mobile, setMobile] = useState(
    () => window.matchMedia("(max-width: 1000px)").matches,
  );
  const sidebar = useRef<HTMLElement>(null);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 1000px)");
    const resize = () => setMobile(media.matches);
    media.addEventListener("change", resize);
    return () => media.removeEventListener("change", resize);
  }, []);
  useEffect(() => {
    if (!mobile || !menu) return;
    const previous = document.activeElement as HTMLElement | null;
    const focusable = () =>
      Array.from(
        sidebar.current?.querySelectorAll<HTMLElement>(
          "a[href], button:not(:disabled)",
        ) || [],
      );
    focusable()[0]?.focus();
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMenu(false);
      }
      if (event.key !== "Tab") return;
      const items = focusable(),
        first = items[0],
        last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", keyboard);
    return () => {
      document.removeEventListener("keydown", keyboard);
      previous?.focus();
    };
  }, [menu, mobile]);
  const me = useMe();
  const logout = useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      session.set(null);
      navigate("/login", { replace: true });
    },
  });
  if (!current)
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname + location.search }}
        replace
      />
    );
  if (me.isPending)
    return (
      <main className="boot-state">
        <Loading label="Đang xác thực tài khoản…" />
      </main>
    );
  if (me.isError)
    return (
      <main className="boot-state">
        <ErrorState
          error={me.error}
          retry={() => {
            void me.refetch();
          }}
        />
        <button
          className="button secondary"
          onClick={() => {
            session.set(null);
            navigate("/login");
          }}
        >
          Về đăng nhập
        </button>
      </main>
    );
  const user = me.data;
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Đi đến nội dung
      </a>
      <aside
        ref={sidebar}
        className={`sidebar ${menu ? "open" : ""}`}
        aria-label="Điều hướng chính"
        role={mobile ? "dialog" : undefined}
        aria-modal={mobile && menu ? true : undefined}
        aria-hidden={mobile && !menu}
        inert={mobile && !menu}
      >
        <Link className="brand" to="/" onClick={() => setMenu(false)}>
          <span className="brand-mark">
            <Network size={24} />
          </span>
          <span>
            nối<span className="brand-dot">.</span>
          </span>
        </Link>
        <button
          className="icon-button mobile-close"
          aria-label="Đóng menu"
          onClick={() => setMenu(false)}
        >
          <X />
        </button>
        <p className="nav-label">KHÔNG GIAN CỦA BẠN</p>
        <nav>
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setMenu(false)}
              className={({ isActive }) =>
                `nav-item ${isActive ? "active" : ""}`
              }
            >
              <item.icon size={19} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <Link
          to="/profile/privacy"
          className="sidebar-tip"
          onClick={() => setMenu(false)}
        >
          <ShieldCheck size={23} />
          <strong>Kết nối theo cách của bạn</strong>
          <p>Chọn thông tin bạn muốn chia sẻ.</p>
          <span>
            Quản lý quyền riêng tư <ChevronRight size={15} />
          </span>
        </Link>
        <div className="sidebar-footer">
          <Link to="/profile" className="user-link">
            <span className="avatar">{initials(user.display_name)}</span>
            <span>
              <strong>{user.display_name}</strong>
              <small>Xem hồ sơ cá nhân</small>
            </span>
          </Link>
          <button
            className="logout-button"
            disabled={logout.isPending}
            onClick={() => logout.mutate()}
          >
            <LogOut size={17} />
            {logout.isPending ? "Đang đăng xuất…" : "Đăng xuất"}
          </button>
          {logout.isError && <ErrorState error={logout.error} />}
        </div>
      </aside>
      {menu && (
        <button
          className="menu-backdrop"
          tabIndex={-1}
          onClick={() => setMenu(false)}
          aria-label="Đóng menu điều hướng"
        />
      )}
      <div className="workspace" inert={mobile && menu}>
        <header className="topbar">
          <div className="topbar-start">
            <button
              className="icon-button mobile-menu"
              aria-label="Mở menu"
              aria-expanded={menu}
              onClick={() => setMenu(true)}
            >
              <Menu size={22} />
            </button>
            <span className="workspace-name">
              Mạng lưới nghề nghiệp <span>/</span>{" "}
              <strong>
                {navigation.find((item) =>
                  item.to === "/"
                    ? location.pathname === "/"
                    : location.pathname.startsWith(item.to),
                )?.label || "Chi tiết"}
              </strong>
            </span>
          </div>
          <div className="topbar-end">
            <span className="live-indicator">Không gian cá nhân</span>
            <Link
              to="/notifications"
              className="icon-button"
              aria-label="Thông báo"
            >
              <Bell size={21} />
            </Link>
            <Link
              to="/profile"
              className="avatar small-avatar"
              aria-label="Hồ sơ cá nhân"
            >
              {initials(user.display_name)}
            </Link>
          </div>
        </header>
        <main id="main" className="main-content">
          <Outlet />
        </main>
        <footer className="page-footer">
          <span>nối. — Cơ hội từ những kết nối</span>
          <Link to="/profile/privacy">Quyền riêng tư</Link>
        </footer>
      </div>
    </div>
  );
}
