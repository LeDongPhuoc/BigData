import { session } from "./session";
import type { Tokens } from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public requestId = "",
    public fields: { field: string; message: string }[] = [],
  ) {
    super(code);
  }
}
export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "Có lỗi xảy ra. Vui lòng thử lại.";
  const codes: Record<string, string> = {
    offline: "Không kết nối được máy chủ. Kiểm tra kết nối và thử lại.",
    session_changed: "Phiên đăng nhập đã thay đổi. Vui lòng thử lại.",
    duplicate_email: "Email đã được đăng ký. Hãy đăng nhập bằng tài khoản này.",
    refresh_reuse: "Phiên đăng nhập đã hết hiệu lực. Vui lòng đăng nhập lại.",
    idempotency_conflict: "Nội dung đã thay đổi. Vui lòng tạo yêu cầu mới.",
    raw_dataset_unavailable:
      "Chưa đọc được CSV VietJobs. Kiểm tra file nguồn và cấu hình đường dẫn raw trên máy chủ.",
  };
  return (
    codes[error.code] ||
    (
      {
        401: "Thông tin đăng nhập không đúng hoặc phiên đã hết hạn.",
        403: "Tài khoản chưa có quyền thực hiện thao tác này.",
        404: "Thông tin không khả dụng hoặc chưa được chia sẻ với bạn.",
        409: "Yêu cầu đã tồn tại hoặc trạng thái hiện tại không cho phép thao tác này.",
        412: "Dữ liệu đã được cập nhật ở nơi khác. Hãy tải bản mới trước khi lưu lại.",
        422: "Thông tin chưa hợp lệ. Kiểm tra các trường đã nhập.",
        428: "Thiếu phiên bản dữ liệu. Hãy tải lại trang.",
        429: "Bạn đã đạt giới hạn yêu cầu. Vui lòng thử lại sau.",
        500: "Máy chủ gặp lỗi. Vui lòng thử lại sau.",
        503: "Dịch vụ đang tạm gián đoạn. Vui lòng thử lại.",
      } as Record<number, string>
    )[error.status] ||
    "Không thể thực hiện yêu cầu. Vui lòng thử lại."
  );
}
type Options = {
  method?: string;
  body?: unknown;
  revision?: string;
  idempotency?: string;
  signal?: AbortSignal;
  public?: boolean;
  timeoutMs?: number;
};
const base = import.meta.env.VITE_API_BASE || "/api/v1";
let refreshing: Promise<void> | null = null;
let authAttempt = 0;

async function send<T>(
  path: string,
  options: Options,
  access?: string,
): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  options.signal?.addEventListener("abort", abort, { once: true });
  if (options.signal?.aborted) abort();
  const timeout = window.setTimeout(abort, options.timeoutMs ?? 25000);
  try {
    const response = await fetch(base + path, {
      method: options.method || "GET",
      signal: controller.signal,
      credentials: "omit",
      headers: {
        "X-Request-ID": crypto.randomUUID(),
        ...(options.body !== undefined
          ? { "Content-Type": "application/json" }
          : {}),
        ...(access ? { Authorization: `Bearer ${access}` } : {}),
        ...(options.revision ? { "If-Match": `"${options.revision}"` } : {}),
        ...(options.idempotency
          ? { "Idempotency-Key": options.idempotency }
          : {}),
      },
      body:
        options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new ApiError(
        response.status,
        data?.error?.code || "http_error",
        data?.error?.request_id || response.headers.get("X-Request-ID") || "",
        data?.error?.details || [],
      );
    }
    return response.status === 204
      ? (undefined as T)
      : ((await response.json()) as T);
  } catch (error) {
    if (error instanceof ApiError || options.signal?.aborted) throw error;
    throw new ApiError(0, "offline");
  } finally {
    clearTimeout(timeout);
    options.signal?.removeEventListener("abort", abort);
  }
}
async function refresh() {
  if (refreshing) return refreshing;
  const before = session.get(),
    version = session.generation();
  if (!before) throw new ApiError(401, "unauthenticated");
  refreshing = (async () => {
    try {
      const tokens = await send<Tokens>("/auth/refresh", {
        method: "POST",
        public: true,
        body: { refresh_token: before.refresh_token },
      });
      if (version !== session.generation())
        throw new ApiError(401, "session_changed");
      session.set(tokens, false);
    } catch (error) {
      // A refresh response can be lost after rotation; never reuse the old token.
      if (version === session.generation()) session.set(null);
      throw error;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}
export async function api<T>(path: string, options: Options = {}): Promise<T> {
  if (options.public) {
    const authenticating = path === "/auth/login" || path === "/auth/register";
    const attempt = authenticating ? ++authAttempt : authAttempt;
    const version = session.generation();
    const result = await send<T>(path, options);
    if (
      authenticating &&
      (attempt !== authAttempt || version !== session.generation())
    )
      throw new ApiError(401, "session_changed");
    return result;
  }
  const version = session.generation();
  if (!session.get()) throw new ApiError(401, "unauthenticated");
  if (session.get()!.expires_at < Date.now() + 5000) await refresh();
  if (version !== session.generation())
    throw new ApiError(401, "session_changed");
  const access = session.get()!.access_token;
  const deliver = async (token: string) => {
    const result = await send<T>(path, options, token);
    // A late mutation response must never populate the next account's cache.
    if (version !== session.generation())
      throw new ApiError(401, "session_changed");
    return result;
  };
  try {
    return await deliver(access);
  } catch (error) {
    if (
      !(error instanceof ApiError) ||
      error.status !== 401 ||
      options.signal?.aborted
    )
      throw error;
    if (version !== session.generation()) throw error;
    if (session.get()?.access_token === access) await refresh();
    if (version !== session.generation())
      throw new ApiError(401, "session_changed");
    try {
      return await deliver(session.get()!.access_token);
    } catch (last) {
      if (
        last instanceof ApiError &&
        last.status === 401 &&
        version === session.generation()
      )
        session.set(null);
      throw last;
    }
  }
}
export function params(values: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== "" && value !== undefined) query.set(key, String(value));
  });
  return "?" + query.toString();
}
