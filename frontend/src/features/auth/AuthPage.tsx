import { useMutation } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import {
  ArrowUpRight,
  Network,
  ShieldCheck,
  Route,
  Eye,
  EyeOff,
} from "lucide-react";
import { useState } from "react";
import { api } from "../../lib/api";
import { session, useSession } from "../../lib/session";
import type { Tokens } from "../../lib/types";
import { ErrorState, Field, PendingButton } from "../../components/ui";

export function AuthPage({ register = false }: { register?: boolean }) {
  const current = useSession();
  const navigate = useNavigate(),
    location = useLocation();
  const [visible, setVisible] = useState(false);
  const schema = z.object({
    email: z.string().trim().email("Nhập địa chỉ email hợp lệ.").max(254),
    password: z
      .string()
      .min(12, "Mật khẩu cần ít nhất 12 ký tự.")
      .max(128, "Tối đa 128 ký tự."),
    display_name: register
      ? z
          .string()
          .trim()
          .min(1, "Nhập tên hiển thị.")
          .max(120, "Tối đa 120 ký tự.")
      : z.string(),
  });
  type Form = z.infer<typeof schema>;
  const form = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "", display_name: "" },
  });
  const mutation = useMutation({
    mutationFn: (values: Form) =>
      api<Tokens>(register ? "/auth/register" : "/auth/login", {
        method: "POST",
        public: true,
        body: register
          ? values
          : { email: values.email, password: values.password },
      }),
    onSuccess: (tokens) => {
      session.set(tokens);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(
        from &&
          from.startsWith("/") &&
          !from.startsWith("//") &&
          !from.startsWith("/login")
          ? from
          : "/",
        { replace: true },
      );
    },
  });
  if (current) return <Navigate to="/" replace />;
  return (
    <main className="auth-page">
      <section className="auth-story">
        <Link to="/login" className="brand">
          <span className="brand-mark">
            <Network size={24} />
          </span>
          <span>
            nối<span className="brand-dot">.</span>
          </span>
        </Link>
        <div className="auth-story-copy">
          <span className="eyebrow">CƠ HỘI BẮT ĐẦU TỪ KẾT NỐI</span>
          <h1>
            Một mối nối.
            <br />
            Một bước tiến mới.
          </h1>
          <p>
            Tìm công việc phù hợp và những người có thể giúp bạn mở cánh cửa
            tiếp theo.
          </p>
          <div className="auth-network" aria-hidden="true">
            <span className="orbit-line one" />
            <span className="orbit-line two" />
            <span className="orbit-person a">Bạn</span>
            <span className="orbit-person b">Kết nối</span>
            <span className="orbit-person c">
              <ArrowUpRight size={28} />
            </span>
            <span className="orbit-person d">Cơ hội</span>
          </div>
        </div>
        <div className="auth-points">
          <span>
            <Route size={18} />
            Đường giới thiệu rõ ràng
          </span>
          <span>
            <ShieldCheck size={18} />
            Quyền riêng tư do bạn chọn
          </span>
        </div>
      </section>
      <section className="auth-form-wrap">
        <div className="auth-form">
          <span className="eyebrow">JOB REFERRAL NETWORK</span>
          <h2>
            {register ? "Bắt đầu mạng lưới của bạn" : "Chào mừng bạn trở lại"}
          </h2>
          <p className="subtitle">
            {register
              ? "Tạo hồ sơ, kết nối và khám phá cơ hội mới."
              : "Đăng nhập để tiếp tục hành trình nghề nghiệp."}
          </p>
          <form
            onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
            noValidate
          >
            {register && (
              <Field
                label="Tên hiển thị"
                id="display_name"
                error={form.formState.errors.display_name?.message}
              >
                <input
                  id="display_name"
                  autoComplete="name"
                  aria-invalid={!!form.formState.errors.display_name}
                  {...form.register("display_name")}
                />
              </Field>
            )}
            <Field
              label="Email"
              id="email"
              error={form.formState.errors.email?.message}
            >
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="ban@example.com"
                aria-invalid={!!form.formState.errors.email}
                {...form.register("email")}
              />
            </Field>
            <Field
              label="Mật khẩu"
              id="password"
              error={form.formState.errors.password?.message}
              hint={
                register
                  ? "Từ 12 đến 128 ký tự. Khoảng trắng trong mật khẩu được giữ nguyên."
                  : undefined
              }
            >
              <div className="password-wrap">
                <input
                  id="password"
                  type={visible ? "text" : "password"}
                  autoComplete={register ? "new-password" : "current-password"}
                  aria-invalid={!!form.formState.errors.password}
                  {...form.register("password")}
                />
                <button
                  type="button"
                  className="icon-button"
                  aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  aria-pressed={visible}
                  onClick={() => setVisible(!visible)}
                >
                  {visible ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </Field>
            {mutation.isError && <ErrorState error={mutation.error} />}
            <PendingButton
              pending={mutation.isPending}
              className="button primary full"
            >
              {mutation.isPending
                ? "Đang xử lý…"
                : register
                  ? "Tạo tài khoản"
                  : "Đăng nhập"}
              <ArrowUpRight size={18} />
            </PendingButton>
          </form>
          <p className="auth-switch">
            {register ? "Đã có tài khoản?" : "Bạn mới đến đây?"}{" "}
            <Link to={register ? "/login" : "/register"}>
              {register ? "Đăng nhập" : "Tạo tài khoản"}
            </Link>
          </p>
          <p className="auth-note">
            <ShieldCheck size={16} />
            Bạn kiểm soát thông tin được chia sẻ trong mạng lưới.
          </p>
        </div>
      </section>
    </main>
  );
}
