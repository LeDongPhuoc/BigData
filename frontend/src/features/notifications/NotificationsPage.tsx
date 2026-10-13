import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Bell } from "lucide-react";
import { api } from "../../lib/api";
import { invalidate } from "../../lib/query";
import type { Notification, Page } from "../../lib/types";
import { dateTime } from "../../lib/format";
import {
  Empty,
  ErrorState,
  Heading,
  Loading,
  Pagination,
} from "../../components/ui";

const descriptions: Record<string, string> = {
  connection_request: "Bạn nhận được lời mời kết nối",
  referral_created: "Bạn nhận được yêu cầu giới thiệu",
  referral_status: "Yêu cầu giới thiệu đã có trạng thái mới",
  referral_expired: "Yêu cầu giới thiệu đã hết hạn",
  "connection.requested": "Bạn nhận được lời mời kết nối",
  "connection.accepted": "Lời mời kết nối đã được chấp nhận",
  "referral.created": "Bạn nhận được yêu cầu giới thiệu",
  "referral.accepted": "Yêu cầu giới thiệu đã được chấp nhận",
  "referral.rejected": "Yêu cầu giới thiệu đã bị từ chối",
  "referral.cancelled": "Yêu cầu giới thiệu đã được hủy",
  "referral.submitted": "Người giới thiệu đã gửi giới thiệu",
  "referral.completed": "Yêu cầu giới thiệu đã hoàn tất",
};
export function NotificationsPage() {
  const [offset, setOffset] = useState(0);
  const list = useQuery({
    queryKey: ["notifications", offset],
    queryFn: ({ signal }) =>
      api<Page<Notification>>(`/notifications/me?offset=${offset}&limit=12`, {
        signal,
      }),
  });
  const read = useMutation({
    mutationFn: (item: Notification) =>
      api<Notification>(`/notifications/${item.id}/read`, {
        method: "POST",
        revision: item.revision,
      }),
    onSuccess: async () => {
      await invalidate("notifications");
    },
    onError: async () => {
      await invalidate("notifications");
    },
  });
  return (
    <>
      <Heading eyebrow="CẬP NHẬT TỪ MẠNG LƯỚI" title="Thông báo">
        Các hoạt động và thay đổi liên quan đến tài khoản của bạn.
      </Heading>
      {read.isError && <ErrorState error={read.error} />}
      {list.isPending ? (
        <Loading />
      ) : list.isError ? (
        <ErrorState
          error={list.error}
          retry={() => {
            void list.refetch();
          }}
        />
      ) : list.data.items.length ? (
        <>
          <ul className="notification-list">
            {list.data.items.map((item) => {
              const [collection, id] = item.resource_id.split("/");
              const href =
                collection === "referral_requests"
                  ? `/referrals/${encodeURIComponent(id)}`
                  : collection === "connections"
                    ? "/network"
                    : undefined;
              return (
                <li
                  key={item.id}
                  className={`panel notification-row ${item.read_at ? "" : "unread"}`}
                >
                  <Bell size={21} />
                  <div>
                    <strong>
                      {descriptions[item.kind] ||
                        "Hoạt động mới trong mạng lưới"}
                    </strong>
                    <small>{dateTime(item.created_at)}</small>
                    {href && (
                      <Link className="text-link" to={href}>
                        Xem hoạt động
                      </Link>
                    )}
                  </div>
                  {!item.read_at && (
                    <button
                      className="button secondary small"
                      disabled={read.isPending}
                      onClick={() => read.mutate(item)}
                    >
                      Đánh dấu đã đọc
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
          <Pagination
            offset={offset}
            more={list.data.has_more}
            onChange={setOffset}
          />
        </>
      ) : (
        <Empty title="Bạn đã xem hết cập nhật">
          <p>
            Thông báo mới sẽ xuất hiện khi mạng lưới có hoạt động liên quan đến
            bạn.
          </p>
        </Empty>
      )}
    </>
  );
}
