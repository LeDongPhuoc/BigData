import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Route, ShieldCheck } from "lucide-react";
import { api } from "../../lib/api";
import { privateQuery, useMe } from "../../lib/query";
import type { Page, Path } from "../../lib/types";
import {
  Badge,
  Empty,
  ErrorState,
  Heading,
  Loading,
  Pagination,
} from "../../components/ui";
import { useJob } from "../jobs/queries";
import { GraphView } from "./GraphView";

export function PathsPage() {
  const { jobId = "" } = useParams(),
    user = useMe().data!,
    job = useJob(jobId);
  const [depth, setDepth] = useState(3),
    [offset, setOffset] = useState(0),
    [selected, setSelected] = useState("");
  const paths = useQuery({
    ...privateQuery,
    queryKey: ["paths", jobId, job.data?.company_id, depth, offset],
    queryFn: ({ signal }) =>
      api<Page<Path>>(
        `/graph/referral-paths?company_id=${encodeURIComponent(job.data!.company_id)}&job_id=${encodeURIComponent(jobId)}&max_depth=${depth}&limit=12&offset=${offset}`,
        { signal },
      ),
    enabled: !!job.data,
  });
  if (job.isPending) return <Loading />;
  if (job.isError)
    return (
      <ErrorState
        error={job.error}
        retry={() => {
          void job.refetch();
        }}
      />
    );
  const active =
    paths.data?.items.find((path) => path.path_key === selected) ||
    paths.data?.items[0];
  return (
    <>
      <Link to={`/jobs/${jobId}`} className="back-link">
        <ArrowLeft size={16} />
        Trở lại công việc
      </Link>
      <Heading
        eyebrow="ĐƯỜNG GIỚI THIỆU"
        title="Một đường đến người có thể giúp bạn"
      >
        {job.data.title} · Các đường kết nối đã được kiểm tra quyền chia sẻ.
      </Heading>
      <div className="path-toolbar">
        <span>
          <Route size={18} />
          Tối đa
        </span>
        <label className="sr-only" htmlFor="path-depth">
          Số kết nối tối đa
        </label>
        <select
          id="path-depth"
          value={depth}
          onChange={(event) => {
            setDepth(Number(event.target.value));
            setOffset(0);
            setSelected("");
          }}
        >
          {[1, 2, 3].map((value) => (
            <option key={value} value={value}>
              {value} kết nối
            </option>
          ))}
        </select>
        <span className="muted">Ưu tiên điểm đường giới thiệu cao nhất</span>
      </div>
      {paths.isPending ? (
        <Loading label="Đang tìm đường giới thiệu…" />
      ) : paths.isError ? (
        <ErrorState
          error={paths.error}
          retry={() => {
            void paths.refetch();
          }}
        />
      ) : !paths.data.items.length || !active ? (
        <Empty title="Chưa tìm thấy đường giới thiệu">
          <p>
            Thử phạm vi ba kết nối hoặc mở rộng mạng lưới. Người ẩn hồ sơ, bị
            chặn hoặc chưa có việc làm được xác minh sẽ không xuất hiện.
          </p>
          <Link to="/network" className="button primary">
            Xem mạng lưới của bạn
          </Link>
        </Empty>
      ) : (
        <div className="paths-layout">
          <section>
            <GraphView
              current={{
                id: user.id,
                display_name: user.display_name,
                headline: user.profile.headline,
              }}
              path={active}
            />
            <div className="panel path-explanation">
              <div className="section-heading compact">
                <h2>Vì sao đường này được đề xuất?</h2>
                <Badge tone="green">{active.hops} kết nối</Badge>
              </div>
              <ol className="path-breadcrumb">
                {active.vertices.map((person, index) => (
                  <li key={person.id}>
                    <Link
                      to={
                        person.id === user.id
                          ? "/profile"
                          : `/people/${person.id}`
                      }
                    >
                      {person.id === user.id ? "Bạn" : person.display_name}
                    </Link>
                    {index < active.vertices.length - 1 && (
                      <ArrowRight size={15} />
                    )}
                  </li>
                ))}
              </ol>
              <div className="path-metrics">
                <div>
                  <strong>
                    {Math.round(active.path_score * 100)}
                    <small>/100</small>
                  </strong>
                  <span>Điểm đường giới thiệu</span>
                </div>
                <div>
                  <strong>
                    {Math.round(active.trust * 100)}
                    <small>/100</small>
                  </strong>
                  <span>Độ tin cậy khai báo trung bình</span>
                </div>
              </div>
              <p className="muted">
                Điểm xếp hạng kết hợp độ tin cậy khai báo (60%) và độ ngắn của
                đường kết nối (40%). Đây không phải xác suất giới thiệu thành
                công.
              </p>
              <p className="verified-line">
                <ShieldCheck size={17} />
                Người nhận đang làm việc tại doanh nghiệp, đã được xác minh.
              </p>
              {user.roles.includes("candidate") && (
                <Link
                  className="button primary"
                  to={`/jobs/${jobId}/referral?referrer=${encodeURIComponent(active.referrer.id)}&offset=${offset}&depth=${depth}`}
                >
                  Gửi yêu cầu giới thiệu <ArrowRight size={16} />
                </Link>
              )}
            </div>
          </section>
          <aside className="panel path-options">
            <h2>Các đường kết nối</h2>
            <p className="muted">Chọn một đường để xem chi tiết.</p>
            {paths.data.items.map((path, index) => (
              <button
                key={path.path_key}
                className={`path-option ${path.path_key === active.path_key ? "selected" : ""}`}
                aria-pressed={path.path_key === active.path_key}
                onClick={() => setSelected(path.path_key)}
              >
                <span className="path-rank">{offset + index + 1}</span>
                <span>
                  <strong>{path.referrer.display_name}</strong>
                  <small>
                    {path.hops === 1
                      ? "Kết nối trực tiếp"
                      : `${path.hops} kết nối · Qua ${path.vertices[1]?.display_name}`}
                  </small>
                </span>
                <span className="path-option-score">
                  {Math.round(path.path_score * 100)}
                </span>
              </button>
            ))}
            <Pagination
              offset={offset}
              more={paths.data.has_more}
              onChange={(value) => {
                setOffset(value);
                setSelected("");
              }}
            />
          </aside>
        </div>
      )}
    </>
  );
}
