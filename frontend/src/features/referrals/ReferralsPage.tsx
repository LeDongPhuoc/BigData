import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowUpRight, Send } from "lucide-react";
import { api } from "../../lib/api";
import { useMe } from "../../lib/query";
import type { Page, Referral } from "../../lib/types";
import { dateTime, statusNames } from "../../lib/format";
import {
  Badge,
  Empty,
  ErrorState,
  Heading,
  Loading,
  Pagination,
} from "../../components/ui";

export function ReferralsPage() {
  const user = useMe().data!,
    [tab, setTab] = useState(
      user.roles.includes("referrer") && !user.roles.includes("candidate")
        ? "incoming"
        : "me",
    ),
    [offset, setOffset] = useState(0);
  const list = useQuery({
    queryKey: ["referrals", tab, offset],
    queryFn: ({ signal }) =>
      api<Page<Referral>>(
        `/referral-requests/${tab}?offset=${offset}&limit=12`,
        { signal },
      ),
  });
  return (
    <>
      <Heading eyebrow="THEO DÕI HÀNH TRÌNH" title="Yêu cầu giới thiệu">
        Theo dõi lời nhắn đã gửi và xử lý yêu cầu dành cho bạn.
      </Heading>
      <div
        className="tab-list"
        role="group"
        aria-label="Loại yêu cầu giới thiệu"
      >
        <button
          aria-pressed={tab === "me"}
          className={tab === "me" ? "active" : ""}
          onClick={() => {
            setTab("me");
            setOffset(0);
          }}
        >
          Yêu cầu của tôi
        </button>
        {user.roles.includes("referrer") && (
          <button
            aria-pressed={tab === "incoming"}
            className={tab === "incoming" ? "active" : ""}
            onClick={() => {
              setTab("incoming");
              setOffset(0);
            }}
          >
            Yêu cầu nhận được
          </button>
        )}
      </div>
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
          <div className="referral-grid">
            {list.data.items.map((item) => (
              <article className="panel referral-card" key={item.id}>
                <div className="referral-card-heading">
                  <Send size={20} />
                  <Badge
                    tone={
                      ["accepted", "submitted", "completed"].includes(
                        item.status,
                      )
                        ? "green"
                        : item.status === "pending"
                          ? "amber"
                          : ""
                    }
                  >
                    {statusNames[item.status] || item.status}
                  </Badge>
                </div>
                <h2>
                  <Link to={`/referrals/${item.id}`}>
                    Yêu cầu #{item.id.slice(0, 8)}
                  </Link>
                </h2>
                <p className="referral-preview">{item.message}</p>
                <div className="referral-card-footer">
                  <small>{dateTime(item.created_at)}</small>
                  <Link className="text-link" to={`/referrals/${item.id}`}>
                    Xem chi tiết <ArrowUpRight size={15} />
                  </Link>
                </div>
              </article>
            ))}
          </div>
          <Pagination
            offset={offset}
            more={list.data.has_more}
            onChange={setOffset}
          />
        </>
      ) : (
        <Empty
          title={
            tab === "incoming"
              ? "Chưa có yêu cầu gửi đến bạn"
              : "Bạn chưa gửi yêu cầu giới thiệu"
          }
        >
          <p>
            {tab === "incoming"
              ? "Yêu cầu hợp lệ sẽ xuất hiện tại đây khi có ứng viên gửi đến."
              : "Bắt đầu từ một vị trí phù hợp và chọn người giới thiệu qua mạng lưới."}
          </p>
          {tab === "me" && user.roles.includes("candidate") && (
            <Link to="/jobs" className="button primary">
              Khám phá việc làm
            </Link>
          )}
        </Empty>
      )}
    </>
  );
}
