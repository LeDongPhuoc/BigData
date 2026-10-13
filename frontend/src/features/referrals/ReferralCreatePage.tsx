import { useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { z } from "zod";
import { ArrowLeft, Send, ShieldCheck } from "lucide-react";
import { api } from "../../lib/api";
import { invalidate, privateQuery, useMe } from "../../lib/query";
import type { Page, Path, Referral } from "../../lib/types";
import {
  ErrorState,
  Field,
  Heading,
  Loading,
  PendingButton,
} from "../../components/ui";
import { useJob } from "../jobs/queries";
import { initials } from "../../lib/format";

const schema = z.object({
  message: z
    .string()
    .trim()
    .min(1, "Hãy viết lời nhắn cho người giới thiệu.")
    .max(2000, "Lời nhắn tối đa 2.000 ký tự."),
});
export function ReferralCreatePage() {
  const { jobId = "" } = useParams(),
    [search] = useSearchParams(),
    navigate = useNavigate();
  const referrer = search.get("referrer") || "",
    user = useMe().data!,
    job = useJob(jobId);
  const offset = Math.max(0, Math.min(1000, Number(search.get("offset")) || 0)),
    depth = Math.max(1, Math.min(3, Number(search.get("depth")) || 3));
  const paths = useQuery({
    ...privateQuery,
    queryKey: ["paths", "compose", jobId, referrer, offset, depth],
    queryFn: ({ signal }) =>
      api<Page<Path>>(
        `/graph/referral-paths?company_id=${encodeURIComponent(job.data!.company_id)}&job_id=${encodeURIComponent(jobId)}&max_depth=${depth}&limit=12&offset=${offset}`,
        { signal },
      ),
    enabled: !!job.data && !!referrer && user.roles.includes("candidate"),
  });
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { message: "" },
  });
  const intent = useRef({ payload: "", key: "" });
  const send = useMutation({
    mutationFn: (value: z.infer<typeof schema>) => {
      const body = {
          referrer_id: referrer,
          job_id: jobId,
          message: value.message,
        },
        payload = JSON.stringify(body);
      if (intent.current.payload !== payload)
        intent.current = { payload, key: crypto.randomUUID() };
      return api<Referral>("/referral-requests", {
        method: "POST",
        body,
        idempotency: intent.current.key,
      });
    },
    onSuccess: async (result) => {
      await invalidate("referrals", "notifications");
      navigate(`/referrals/${result.id}`, { replace: true });
    },
  });
  if (!user.roles.includes("candidate"))
    return (
      <div className="notice" role="alert">
        Tài khoản cần vai trò ứng viên để gửi yêu cầu giới thiệu.
      </div>
    );
  if (job.isPending || (paths.isPending && !!referrer))
    return <Loading label="Đang kiểm tra người giới thiệu…" />;
  if (job.isError || paths.isError)
    return (
      <ErrorState
        error={job.error || paths.error}
        retry={() => {
          void job.refetch();
          void paths.refetch();
        }}
      />
    );
  const path = paths.data?.items.find((item) => item.referrer.id === referrer);
  return (
    <>
      <Link to={`/jobs/${jobId}/paths`} className="back-link">
        <ArrowLeft size={16} />
        Chọn đường giới thiệu
      </Link>
      <Heading
        eyebrow="YÊU CẦU GIỚI THIỆU"
        title="Một lời nhắn, một cơ hội mới"
      >
        Giới thiệu bản thân và lý do bạn quan tâm đến vị trí này.
      </Heading>
      {!path ? (
        <div className="panel">
          <p className="notice">
            Người nhận hoặc đường giới thiệu không còn khả dụng. Vui lòng chọn
            lại từ các đường kết nối hiện tại.
          </p>
          <Link to={`/jobs/${jobId}/paths`} className="button primary">
            Chọn người giới thiệu
          </Link>
        </div>
      ) : (
        <div className="compose-layout">
          <section className="panel">
            <div className="recipient">
              <span className="avatar">
                {initials(path.referrer.display_name)}
              </span>
              <div>
                <small>GỬI ĐẾN</small>
                <h2>{path.referrer.display_name}</h2>
                <p>
                  {path.referrer.headline ||
                    "Người giới thiệu tại doanh nghiệp"}
                </p>
              </div>
            </div>
            <form
              onSubmit={form.handleSubmit((value) => send.mutate(value))}
              noValidate
            >
              <Field
                label="Lời nhắn của bạn"
                id="referral-message"
                error={form.formState.errors.message?.message}
                hint="Tối đa 2.000 ký tự. Không gửi mật khẩu hoặc thông tin nhạy cảm trong lời nhắn."
              >
                <textarea
                  id="referral-message"
                  rows={8}
                  placeholder="Chào bạn, mình quan tâm đến vị trí… Kinh nghiệm của mình phù hợp vì…"
                  {...form.register("message")}
                />
              </Field>
              <div className="message-count">
                {form.watch("message").length}/2.000
              </div>
              {send.isError && <ErrorState error={send.error} />}
              <PendingButton pending={send.isPending}>
                <Send size={17} />
                {send.isPending
                  ? "Đang gửi yêu cầu…"
                  : "Gửi yêu cầu giới thiệu"}
              </PendingButton>
            </form>
          </section>
          <aside className="panel compose-summary">
            <span className="eyebrow">CƠ HỘI BẠN QUAN TÂM</span>
            <h2>{job.data!.title}</h2>
            <p>{job.data!.location}</p>
            <div className="verified-line">
              <ShieldCheck size={18} />
              Nhân viên hiện tại đã được xác minh
            </div>
            <p className="muted">
              Đường tiếp cận qua {path.hops} kết nối. Người nhận quyết định chấp
              nhận hoặc từ chối; gửi yêu cầu không đảm bảo được giới thiệu.
            </p>
            <p className="notice">
              Bạn có thể theo dõi và hủy yêu cầu đang chờ hoặc đã chấp nhận
              trong mục Yêu cầu giới thiệu.
            </p>
          </aside>
        </div>
      )}
    </>
  );
}
