import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowUpRight, Network, Plus, UserRoundCheck } from "lucide-react";
import { api } from "../../lib/api";
import { invalidate, privateQuery, useMe } from "../../lib/query";
import type {
  Connection,
  Page,
  PublicProfile,
  UserSummary,
} from "../../lib/types";
import { initials } from "../../lib/format";
import {
  Empty,
  ErrorState,
  Field,
  Heading,
  Loading,
  Pagination,
  PendingButton,
} from "../../components/ui";
import { GraphView } from "./GraphView";

export function NetworkPage() {
  const user = useMe().data!,
    [search] = useSearchParams();
  const [offset, setOffset] = useState(0),
    [tab, setTab] = useState("connections");
  const [target, setTarget] = useState(search.get("invite") || ""),
    [previewId, setPreviewId] = useState("");
  const intent = useRef({ payload: "", key: "" });
  const direct = useQuery({
    ...privateQuery,
    queryKey: ["connections", "direct", offset],
    queryFn: ({ signal }) =>
      api<Page<UserSummary>>(`/graph/connections?limit=24&offset=${offset}`, {
        signal,
      }),
    enabled: tab === "connections",
  });
  const requests = useQuery({
    queryKey: ["connections", tab, offset],
    queryFn: ({ signal }) =>
      api<Page<Connection>>(
        `/connections/requests/${tab}?limit=24&offset=${offset}`,
        { signal },
      ),
    enabled: tab !== "connections",
  });
  const preview = useQuery({
    ...privateQuery,
    queryKey: ["publicProfile", previewId],
    queryFn: ({ signal }) =>
      api<PublicProfile>(`/users/${encodeURIComponent(previewId)}/profile`, {
        signal,
      }),
    enabled: !!previewId,
  });
  const invite = useMutation({
    mutationFn: () => {
      if (intent.current.payload !== previewId)
        intent.current = { payload: previewId, key: crypto.randomUUID() };
      return api<Connection>("/connections/requests", {
        method: "POST",
        idempotency: intent.current.key,
        body: { target_user_id: previewId },
      });
    },
    onSuccess: async () => {
      intent.current = { payload: "", key: "" };
      await invalidate("connections", "notifications");
    },
  });
  const action = useMutation({
    mutationFn: ({
      item,
      operation,
    }: {
      item: Connection;
      operation: "accept" | "reject" | "delete";
    }) =>
      api<Connection>(
        `/connections/${item.id}${operation === "delete" ? "" : "/" + operation}`,
        {
          method: operation === "delete" ? "DELETE" : "POST",
          revision: item.revision,
        },
      ),
    onSuccess: async () => {
      await invalidate("connections", "paths", "notifications");
    },
    onError: async () => {
      await invalidate("connections");
    },
  });
  const page = tab === "connections" ? direct : requests;
  return (
    <>
      <Heading eyebrow="MẠNG LƯỚI CỦA BẠN" title="Những người mở ra cơ hội">
        Kết nối trực tiếp đã được chấp nhận và được phép chia sẻ với bạn.
      </Heading>
      <div className="network-layout">
        <section>
          <div className="tab-list" role="group" aria-label="Loại kết nối">
            {[
              ["connections", "Kết nối"],
              ["incoming", "Lời mời đến"],
              ["outgoing", "Lời mời đã gửi"],
            ].map(([value, label]) => (
              <button
                key={value}
                className={tab === value ? "active" : ""}
                aria-pressed={tab === value}
                onClick={() => {
                  setTab(value);
                  setOffset(0);
                  action.reset();
                }}
              >
                {label}
              </button>
            ))}
          </div>
          {page.isPending ? (
            <Loading />
          ) : page.isError ? (
            <ErrorState
              error={page.error}
              retry={() => {
                void page.refetch();
              }}
            />
          ) : tab === "connections" && direct.data ? (
            <>
              {direct.data.items.length ? (
                <>
                  <GraphView
                    current={{
                      id: user.id,
                      display_name: user.display_name,
                      headline: user.profile.headline,
                    }}
                    people={direct.data.items}
                  />
                  <div className="section-heading compact">
                    <h2>Kết nối trong trang này</h2>
                    <span>{direct.data.items.length} người</span>
                  </div>
                  <div className="people-grid">
                    {direct.data.items.map((person) => (
                      <Link
                        to={`/people/${person.id}`}
                        className="person-card"
                        key={person.id}
                      >
                        <span className="avatar">
                          {initials(person.display_name)}
                        </span>
                        <div>
                          <strong>{person.display_name}</strong>
                          <small>
                            {person.headline || "Kết nối nghề nghiệp"}
                          </small>
                        </div>
                        <ArrowUpRight size={16} />
                      </Link>
                    ))}
                  </div>
                </>
              ) : (
                <Empty title="Mạng lưới đang chờ kết nối đầu tiên">
                  <p>
                    Gửi lời mời đến người bạn biết. Đường giới thiệu chỉ dùng
                    các kết nối đã được chấp nhận.
                  </p>
                </Empty>
              )}
              <Pagination
                offset={offset}
                more={direct.data.has_more}
                onChange={setOffset}
                size={24}
              />
            </>
          ) : requests.data ? (
            <>
              {requests.data.items.length ? (
                <ul className="request-list">
                  {requests.data.items.map((item) => (
                    <li className="panel connection-request" key={item.id}>
                      <div>
                        <UserRoundCheck size={21} />
                        <div>
                          <Link
                            to={`/people/${item.from_user_id === user.id ? item.to_user_id : item.from_user_id}`}
                          >
                            Hồ sơ{" "}
                            {item.from_user_id === user.id
                              ? item.to_user_id
                              : item.from_user_id}
                          </Link>
                          <small>
                            {tab === "incoming"
                              ? "Muốn kết nối với bạn"
                              : "Đang chờ chấp nhận"}
                          </small>
                        </div>
                      </div>
                      <div className="button-row">
                        {tab === "incoming" ? (
                          <>
                            <button
                              className="button primary small"
                              disabled={action.isPending}
                              onClick={() =>
                                action.mutate({ item, operation: "accept" })
                              }
                            >
                              Chấp nhận
                            </button>
                            <button
                              className="button secondary small"
                              disabled={action.isPending}
                              onClick={() => {
                                if (
                                  window.confirm("Từ chối lời mời kết nối này?")
                                )
                                  action.mutate({ item, operation: "reject" });
                              }}
                            >
                              Từ chối
                            </button>
                          </>
                        ) : (
                          <button
                            className="button secondary small"
                            disabled={action.isPending}
                            onClick={() => {
                              if (
                                window.confirm("Thu hồi lời mời kết nối này?")
                              )
                                action.mutate({ item, operation: "delete" });
                            }}
                          >
                            Thu hồi
                          </button>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty
                  title={
                    tab === "incoming"
                      ? "Chưa có lời mời mới"
                      : "Chưa có lời mời đang chờ"
                  }
                />
              )}
              <Pagination
                offset={offset}
                more={requests.data.has_more}
                onChange={setOffset}
                size={24}
              />
            </>
          ) : null}
          {action.isError && <ErrorState error={action.error} />}
          {action.isSuccess && (
            <p className="success-message" role="status">
              Đã cập nhật lời mời kết nối.
            </p>
          )}
        </section>
        <aside>
          <section className="panel invite-panel">
            <h2>
              <Plus size={19} />
              Thêm một kết nối
            </h2>
            <p className="muted">
              Nhập mã hồ sơ được người quen chia sẻ. Hệ thống chỉ hiển thị hồ sơ
              được phép xem.
            </p>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                const id = target.trim();
                if (id !== user.id) {
                  setPreviewId(id);
                  invite.reset();
                }
              }}
            >
              <Field
                label="Mã hồ sơ người nhận"
                id="invite-id"
                hint={`Mã của bạn: ${user.id}`}
              >
                <input
                  id="invite-id"
                  required
                  pattern="[A-Za-z0-9_-]{1,128}"
                  maxLength={128}
                  value={target}
                  onChange={(event) => setTarget(event.target.value)}
                  placeholder="Mã hồ sơ"
                />
              </Field>
              <button
                className="button secondary full"
                disabled={target.trim() === user.id}
              >
                Xem người nhận
              </button>
            </form>
            {previewId &&
              (preview.isPending ? (
                <Loading />
              ) : preview.isError ? (
                <ErrorState
                  error={preview.error}
                  retry={() => {
                    void preview.refetch();
                  }}
                />
              ) : preview.data ? (
                <div className="invite-preview">
                  <span className="avatar">
                    {initials(preview.data.display_name)}
                  </span>
                  <strong>{preview.data.display_name}</strong>
                  <p>{preview.data.profile.headline || "Hồ sơ nghề nghiệp"}</p>
                  {invite.isError && <ErrorState error={invite.error} />}
                  {invite.isSuccess ? (
                    <p className="success-message" role="status">
                      Đã gửi lời mời kết nối.
                    </p>
                  ) : (
                    <PendingButton
                      pending={invite.isPending}
                      className="button primary full"
                      onClick={() => invite.mutate()}
                    >
                      Gửi lời mời kết nối
                    </PendingButton>
                  )}
                </div>
              ) : null)}
          </section>
          <section className="network-tip">
            <Network size={24} />
            <h3>Từ người quen đến cơ hội mới</h3>
            <p>
              Một đường giới thiệu có thể đi qua tối đa ba kết nối. Hãy bắt đầu
              từ những người bạn thực sự biết.
            </p>
            <Link to="/jobs" className="text-link">
              Tìm việc có thể được giới thiệu <ArrowUpRight size={15} />
            </Link>
          </section>
        </aside>
      </div>
    </>
  );
}
