import type { ReactNode } from "react";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  LoaderCircle,
  SearchX,
} from "lucide-react";
import { ApiError, errorMessage } from "../lib/api";

export function Loading({ label = "Đang tải dữ liệu…" }: { label?: string }) {
  return (
    <div className="state loading" role="status">
      <LoaderCircle className="spin" size={24} />
      <span>{label}</span>
    </div>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="state empty">
      <SearchX size={32} aria-hidden="true" />
      <h3>{title}</h3>
      {children && <div>{children}</div>}
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  return (
    <div className="error-box" role="alert">
      <AlertCircle size={20} aria-hidden="true" />
      <div>
        <p>{errorMessage(error)}</p>
        {error instanceof ApiError && error.requestId && (
          <small>Mã hỗ trợ: {error.requestId}</small>
        )}
        {retry && (
          <button className="button secondary small" onClick={retry}>
            Thử lại
          </button>
        )}
      </div>
    </div>
  );
}
export function Heading({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {children && <p className="subtitle">{children}</p>}
      </div>
      {action}
    </div>
  );
}
export function Field({
  label,
  id,
  error,
  children,
  hint,
}: {
  label: string;
  id: string;
  error?: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && <small id={`${id}-hint`}>{hint}</small>}
      {error && (
        <p className="field-error" role="alert" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}
export function PendingButton({
  pending,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { pending: boolean }) {
  return (
    <button
      {...props}
      disabled={pending || props.disabled}
      aria-busy={pending}
      className={props.className || "button primary"}
    >
      {pending && (
        <LoaderCircle size={16} className="spin" aria-hidden="true" />
      )}
      {children}
    </button>
  );
}
export function Pagination({
  offset,
  more,
  onChange,
  busy,
  size = 12,
}: {
  offset: number;
  more: boolean;
  onChange: (v: number) => void;
  busy?: boolean;
  size?: number;
}) {
  return (
    <nav className="pagination" aria-label="Phân trang">
      <button
        className="button secondary small"
        disabled={offset === 0 || busy}
        onClick={() => onChange(Math.max(0, offset - size))}
      >
        <ArrowLeft size={16} />
        Trang trước
      </button>
      <span>Trang {Math.floor(offset / size) + 1}</span>
      <button
        className="button secondary small"
        disabled={!more || busy || offset + size > 1000}
        onClick={() => onChange(offset + size)}
      >
        Trang sau
        <ArrowRight size={16} />
      </button>
    </nav>
  );
}
export function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
