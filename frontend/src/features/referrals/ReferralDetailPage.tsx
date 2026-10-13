import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check, Clock3 } from "lucide-react";
import { api, ApiError } from "../../lib/api";
import { invalidate, useMe } from "../../lib/query";
import type { Referral } from "../../lib/types";
import { dateTime, statusNames } from "../../lib/format";
import {
  Badge,
  ErrorState,
  Field,
  Heading,
  Loading,
  PendingButton,
} from "../../components/ui";

export function ReferralDetailPage() {
  const { referralId = "" } = useParams(),
    user = useMe().data!;
  const [reason, setReason] = useState(""),
    [evidence, setEvidence] = useState(""),
    [outcome, setOutcome] = useState("");
  const detail = useQuery({
    queryKey: ["referrals", "detail", referralId],
    queryFn: ({ signal }) =>
      api<Referral>(`/referral-requests/${encodeURIComponent(referralId)}`, {
        signal,
      }),
    staleTime: 0,
  });
  const action = useMutation({
    mutationFn: (operation: string) =>
      api<Referral>(
        `/referral-requests/${encodeURIComponent(referralId)}/${operation}`,
        {
          method: "POST",
          revision: detail.data!.revision,
          body: {
            reason: reason.trim() || null,
            ...(operation === "submit"
              ? { evidence_ref: evidence.trim() }
              : {}),
            ...(operation === "complete" ? { outcome: outcome.trim() } : {}),
          },
        },
      ),
    onSuccess: async () => {
      setReason("");
      setEvidence("");
      setOutcome("");
      await invalidate("referrals", "notifications");
    },
  });
  if (detail.isPending) return <Loading />;
  if (detail.isError)
    return (
      <ErrorState
        error={detail.error}
        retry={() => {
          void detail.refetch();
        }}
      />
    );
  const item = detail.data;
  const own = item.candidate_id === user.id && user.roles.includes("candidate"),
    recipient = item.referrer_id === user.id && user.roles.includes("referrer");
  const cancellable = own && ["pending", "accepted"].includes(item.status),
    acceptable = recipient && item.status === "pending",
    submittable = recipient && item.status === "accepted",
    completable = recipient && item.status === "submitted";
  const stale = action.error instanceof ApiError && action.error.status === 412;
  return (
    <>
      <Link to="/referrals" className="back-link">
        <ArrowLeft size={16} />
        Tất cả yêu cầu
      </Link>
      <Heading
        eyebrow={`YÊU CẦU #${item.id.slice(0, 8)}`}
        title="Theo dõi lời giới thiệu"
        action={
          <Badge
            tone={
              ["accepted", "submitted", "completed"].includes(item.status)
                ? "green"
                : "amber"
            }
          >
            {statusNames[item.status] || item.status}
          </Badge>
        }
      >
        Tạo lúc {dateTime(item.created_at)}
      </Heading>
      <div className="detail-columns">
        <section className="panel">
          <h2>Nội dung yêu cầu</h2>
          <p className="preserve-lines referral-message">{item.message}</p>
          <div className="request-info">
            <div>
              <span>Công việc</span>
              <Link to={`/jobs/${item.job_id}`}>Xem vị trí tuyển dụng</Link>
            </div>
            <div>
              <span>Ứng viên</span>
              <Link to={`/people/${item.candidate_id}`}>
                {item.candidate_id === user.id
                  ? "Hồ sơ của bạn"
                  : "Xem hồ sơ ứng viên"}
              </Link>
            </div>
            <div>
              <span>Người giới thiệu</span>
              <Link to={`/people/${item.referrer_id}`}>
                {item.referrer_id === user.id
                  ? "Hồ sơ của bạn"
                  : "Xem hồ sơ người giới thiệu"}
              </Link>
            </div>
            <div>
              <span>Hết hạn</span>
              <strong>{dateTime(item.expires_at)}</strong>
            </div>
            {item.evidence_ref && (
              <div>
                <span>Mã bằng chứng giới thiệu</span>
                <code>{item.evidence_ref}</code>
              </div>
            )}
          </div>
          {(cancellable || acceptable || submittable || completable) && (
            <form
              className="referral-action-form"
              onSubmit={(event) => {
                event.preventDefault();
                if (submittable) action.mutate("submit");
                else if (completable) action.mutate("complete");
              }}
            >
              <h2>Thao tác với yêu cầu</h2>
              <Field
                label="Lý do hoặc ghi chú (không bắt buộc)"
                id="action-reason"
              >
                <textarea
                  id="action-reason"
                  rows={3}
                  maxLength={500}
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                />
              </Field>
              {submittable && (
                <Field
                  label="Mã bằng chứng giới thiệu"
                  id="evidence-ref"
                  hint="Mã tham chiếu nội bộ, không phải tệp tải lên. Dùng chữ, số và _ . / : -"
                >
                  <input
                    id="evidence-ref"
                    required
                    pattern="[A-Za-z0-9][A-Za-z0-9_./:\-]*"
                    maxLength={500}
                    value={evidence}
                    onChange={(event) => setEvidence(event.target.value)}
                  />
                </Field>
              )}
              {completable && (
                <Field label="Kết quả giới thiệu" id="outcome">
                  <textarea
                    id="outcome"
                    required
                    maxLength={500}
                    value={outcome}
                    onChange={(event) => setOutcome(event.target.value)}
                  />
                </Field>
              )}
              <div className="button-row">
                {acceptable && (
                  <>
                    <PendingButton
                      type="button"
                      pending={action.isPending}
                      disabled={stale}
                      onClick={() => action.mutate("accept")}
                    >
                      Chấp nhận yêu cầu
                    </PendingButton>
                    <button
                      type="button"
                      className="button secondary"
                      disabled={action.isPending || stale}
                      onClick={() => {
                        if (window.confirm("Từ chối yêu cầu giới thiệu này?"))
                          action.mutate("reject");
                      }}
                    >
                      Từ chối
                    </button>
                  </>
                )}
                {cancellable && (
                  <button
                    type="button"
                    className="button danger"
                    disabled={action.isPending || stale}
                    onClick={() => {
                      if (
                        window.confirm(
                          "Hủy yêu cầu giới thiệu này? Hành động này sẽ được lưu trong lịch sử.",
                        )
                      )
                        action.mutate("cancel");
                    }}
                  >
                    Hủy yêu cầu
                  </button>
                )}
                {(submittable || completable) && (
                  <PendingButton
                    pending={action.isPending}
                    disabled={
                      stale ||
                      (submittable ? !evidence.trim() : !outcome.trim())
                    }
                  >
                    {submittable
                      ? "Xác nhận đã giới thiệu"
                      : "Hoàn tất giới thiệu"}
                  </PendingButton>
                )}
              </div>
            </form>
          )}
          {action.isError && <ErrorState error={action.error} />}
          {stale && (
            <button
              className="button secondary"
              onClick={() => {
                void detail.refetch().then((result) => {
                  if (!result.isError) action.reset();
                });
              }}
            >
              Tải trạng thái mới nhất
            </button>
          )}
          {action.isSuccess && (
            <p className="success-message" role="status">
              <Check size={17} />
              Đã cập nhật trạng thái yêu cầu.
            </p>
          )}
        </section>
        <aside className="panel timeline-panel">
          <h2>
            <Clock3 size={18} />
            Lịch sử yêu cầu
          </h2>
          <ol className="timeline">
            {item.history.map((entry, index) => (
              <li key={`${entry.at}-${index}`}>
                <span className="timeline-dot" />
                <strong>{statusNames[entry.status] || entry.status}</strong>
                <small>{dateTime(entry.at)}</small>
                {entry.reason && <p>{entry.reason}</p>}
              </li>
            ))}
          </ol>
          <p className="notice">
            Hồ sơ và công việc được kiểm tra quyền khi mở. Yêu cầu giới thiệu
            không cấp thêm quyền xem thông tin riêng tư.
          </p>
        </aside>
      </div>
    </>
  );
}
