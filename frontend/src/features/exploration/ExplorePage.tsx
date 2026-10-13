import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, NavLink, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  ArrowLeft,
  BarChart3,
  BriefcaseBusiness,
  Check,
  Database,
  MapPin,
  Network,
  Search,
  Sparkles,
} from "lucide-react";
import { api } from "../../lib/api";
import { Badge, Empty, ErrorState, Field, Loading } from "../../components/ui";
import { money, workModes } from "../../lib/format";
import { SkillGraph } from "./SkillGraph";
import { RawDataPage } from "./RawDataPage";
import type { Catalog, CatalogJob, Ranking, Similar } from "./types";
import type { components } from "../../lib/api.generated";
import "./exploration.css";

const tabs = [
  { to: "/explore", label: "Tổng quan", icon: Database, end: true },
  { to: "/explore/jobs", label: "Tìm việc", icon: Search, end: false },
  {
    to: "/explore/recommendations",
    label: "Gợi ý & kỹ năng",
    icon: Sparkles,
    end: false,
  },
  { to: "/explore/graph", label: "Khám phá graph", icon: Network, end: false },
  { to: "/explore/analytics", label: "Phân tích", icon: BarChart3, end: false },
  {
    to: "/explore/data",
    label: "Dữ liệu VietJobs",
    icon: Database,
    end: false,
  },
];
const origin = {
  seed: "Dữ liệu seed",
  public: "Có nguồn công khai",
  local: "Dữ liệu nội bộ",
};
const tally = (values: string[]) =>
  Object.entries(
    values.reduce<Record<string, number>>((a, v) => {
      a[v] = (a[v] || 0) + 1;
      return a;
    }, {}),
  ).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));

function SourceBadge({ job }: { job: CatalogJob }) {
  return (
    <Badge tone={job.origin === "public" ? "green" : undefined}>
      {origin[job.origin]}
    </Badge>
  );
}
function Card({ job }: { job: CatalogJob }) {
  return (
    <article className="panel explore-job">
      <div className="explore-job-top">
        <span className="explore-company-mark">
          <BriefcaseBusiness size={20} />
        </span>
        <div>
          <small>{job.company}</small>
          <h3>
            <Link to={`/explore/jobs/${job.id}`}>{job.title}</Link>
          </h3>
        </div>
      </div>
      <div className="tag-row">
        <SourceBadge job={job} />
        <span className="muted">
          <MapPin size={13} /> {job.location}
        </span>
      </div>
      <div className="explore-salary">
        {money(job.salary_min, job.salary_max)}
      </div>
      <div className="tag-row">
        {job.requirements.slice(0, 4).map((s) => (
          <span className="skill-pill" key={s.id}>
            {s.name}
          </span>
        ))}
        {!job.requirements.length && (
          <small>Chưa khai báo kỹ năng yêu cầu</small>
        )}
      </div>
      <div className="explore-card-bottom">
        <small>{workModes[job.work_mode] || job.work_mode}</small>
        <Link className="text-link" to={`/explore/jobs/${job.id}`}>
          Xem chi tiết <ArrowRight size={15} />
        </Link>
      </div>
    </article>
  );
}
function Bars({
  title,
  rows,
  note,
}: {
  title: string;
  rows: [string, number][];
  note: string;
}) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  return (
    <section className="panel explore-bars">
      <h2>{title}</h2>
      <p className="muted">{note}</p>
      {rows.length ? (
        rows.slice(0, 10).map(([label, count]) => (
          <div className="bar-row" key={label}>
            <div>
              <span>{label}</span>
              <strong>{count}</strong>
            </div>
            <div className="bar-track">
              <span style={{ width: `${(100 * count) / max}%` }} />
            </div>
          </div>
        ))
      ) : (
        <p>Chưa đủ dữ liệu để thống kê.</p>
      )}
    </section>
  );
}

export function ExplorePage() {
  const { tab = "overview", jobId } = useParams();
  const catalog = useQuery({
    queryKey: ["exploration", "catalog"],
    queryFn: ({ signal }) => api<Catalog>("/exploration/catalog", { signal }),
    enabled: tab !== "data",
  });
  return (
    <div className="exploration">
      <div className="explore-title">
        <div>
          <p className="eyebrow">KHÁM PHÁ NGHỀ NGHIỆP</p>
          <h1>Hiểu kỹ năng. Tìm cơ hội phù hợp.</h1>
          <p className="muted">
            Từ yêu cầu công việc đến những lựa chọn dành cho bạn.
          </p>
        </div>
        <span className="explore-stage">
          <Database size={16} /> Bản xem trước chức năng
        </span>
      </div>
      <nav className="explore-tabs" aria-label="Các chức năng khám phá">
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            <t.icon size={17} />
            {t.label}
          </NavLink>
        ))}
      </nav>
      <div className="explore-source">
        <Database size={18} />
        <div>
          <strong>
            {tab === "data"
              ? "Đang kiểm tra CSV VietJobs gốc."
              : "Đang dùng catalog hiện có, gồm dữ liệu seed."}
          </strong>
          <p>
            {tab === "data"
              ? "Đọc raw bằng Python để khảo sát. Chưa nhập VietJobs vào ArangoDB, chưa xử lý bằng Spark; dữ liệu seed được giữ riêng."
              : "VietJobs chưa được nhập; thống kê và gợi ý ở đây chưa phải kết quả xử lý Spark. Hồ sơ thử nghiệm không ghi đè hồ sơ của bạn."}
          </p>
        </div>
        <Link to="/jobs" className="text-link">
          Không gian cũ <ArrowRight size={15} />
        </Link>
      </div>
      {tab === "data" ? (
        <RawDataPage />
      ) : catalog.isPending ? (
        <Loading label="Đang đọc catalog việc làm…" />
      ) : catalog.isError ? (
        <ErrorState
          error={catalog.error}
          retry={() => {
            void catalog.refetch();
          }}
        />
      ) : (
        <>
          {catalog.data.truncated && (
            <p className="notice">
              Đang khám phá 1.000/{catalog.data.total} tin. Bộ lọc và thống kê
              chỉ áp dụng phần catalog đã tải; chưa phải toàn dataset.
            </p>
          )}
          {jobId ? (
            <Detail jobs={catalog.data.items} id={jobId} />
          ) : tab === "jobs" ? (
            <SearchJobs jobs={catalog.data.items} />
          ) : tab === "recommendations" ? (
            <Recommendations jobs={catalog.data.items} />
          ) : tab === "graph" ? (
            <GraphPage jobs={catalog.data.items} />
          ) : tab === "analytics" ? (
            <Analytics jobs={catalog.data.items} />
          ) : (
            <Overview catalog={catalog.data} />
          )}
        </>
      )}
    </div>
  );
}

function Overview({ catalog }: { catalog: Catalog }) {
  const jobs = catalog.items,
    skills = new Set(jobs.flatMap((j) => j.requirements.map((s) => s.id)));
  return (
    <>
      <section className="explore-hero">
        <div>
          <span className="banner-label">MỖI KỸ NĂNG MỞ THÊM MỘT HƯỚNG ĐI</span>
          <h2>
            Khám phá công việc
            <br />
            qua những gì bạn có thể làm.
          </h2>
          <p>
            Nhập kỹ năng để thử gợi ý, hiểu yêu cầu còn thiếu và tìm những vị
            trí liên quan.
          </p>
          <Link className="button light" to="/explore/recommendations">
            Thử gợi ý theo kỹ năng <ArrowRight size={17} />
          </Link>
        </div>
        <div className="explore-hero-map" aria-hidden="true">
          <span className="hero-map-job">Công việc</span>
          <span className="hero-map-skill">Kỹ năng</span>
          <span className="hero-map-location">Địa điểm</span>
          <Network size={80} />
        </div>
      </section>
      <div className="explore-metrics">
        {[
          ["Tin trong catalog đã tải", jobs.length],
          ["Kỹ năng được đề cập", skills.size],
          ["Địa điểm", new Set(jobs.map((j) => j.location)).size],
          [
            "Tin seed trong catalog",
            jobs.filter((j) => j.origin === "seed").length,
          ],
        ].map(([label, value]) => (
          <div className="panel" key={label}>
            <small>{label}</small>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <div className="section-heading">
        <div>
          <h2>Bắt đầu từ một công việc</h2>
          <p className="muted">
            Mở chi tiết để xem yêu cầu và các vị trí có kỹ năng chung.
          </p>
        </div>
        <Link className="text-link" to="/explore/jobs">
          Xem catalog <ArrowRight size={16} />
        </Link>
      </div>
      <div className="job-grid">
        {jobs.slice(0, 3).map((j) => (
          <Card key={j.id} job={j} />
        ))}
      </div>
      {!jobs.length && (
        <Empty title="Catalog chưa có tin đang mở">
          Các chức năng cũ vẫn có tại không gian cá nhân.
        </Empty>
      )}
      <div className="explore-next panel">
        <div>
          <h2>Sẵn sàng cho bước dữ liệu VietJobs</h2>
          <p>
            Giao diện này cho phép kiểm tra luồng sử dụng trước. Ngành nghề,
            loại hợp đồng và dữ liệu chuẩn hóa sẽ được bổ sung khi nối pipeline.
          </p>
        </div>
        <Badge>Chưa nhập VietJobs</Badge>
      </div>
    </>
  );
}

function SearchJobs({ jobs }: { jobs: CatalogJob[] }) {
  const [search, setSearch] = useSearchParams();
  const query = search.get("q") || "";
  const [draft, setDraft] = useState(query);
  useEffect(() => setDraft(query), [query]);
  const skills = [
    ...new Map(
      jobs.flatMap((j) => j.requirements).map((s) => [s.id, s]),
    ).values(),
  ];
  const filter = (key: string, value: string) => {
    const next = new URLSearchParams(search);
    value ? next.set(key, value) : next.delete(key);
    next.delete("page");
    setSearch(next);
  };
  const q = (search.get("q") || "").toLocaleLowerCase();
  const filtered = jobs.filter(
    (j) =>
      (!q ||
        [
          j.title,
          j.description,
          j.company,
          ...j.requirements.map((s) => s.name),
        ].some((t) => t.toLocaleLowerCase().includes(q))) &&
      (!search.get("location") || j.location === search.get("location")) &&
      (!search.get("mode") || j.work_mode === search.get("mode")) &&
      (!search.get("skill") ||
        j.requirements.some((s) => s.id === search.get("skill"))),
  );
  const page = Math.min(
    Math.max(0, Math.floor(Number(search.get("page"))) || 0),
    Math.max(0, Math.ceil(filtered.length / 9) - 1),
  );
  const reset = () => {
    setDraft("");
    setSearch({});
  };
  return (
    <>
      <form
        className="search-bar"
        onSubmit={(e) => {
          e.preventDefault();
          filter("q", draft.trim());
        }}
      >
        <Search size={21} />
        <label className="sr-only" htmlFor="explore-search">
          Từ khóa tìm kiếm
        </label>
        <input
          id="explore-search"
          type="search"
          value={draft}
          maxLength={160}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Tên công việc, kỹ năng, doanh nghiệp…"
        />
        <button className="button primary">Tìm kiếm</button>
      </form>
      <div className="jobs-layout">
        <aside className="panel filter-panel">
          <h2>Thu hẹp lựa chọn</h2>
          <Field id="explore-location" label="Địa điểm">
            <select
              id="explore-location"
              value={search.get("location") || ""}
              onChange={(e) => filter("location", e.target.value)}
            >
              <option value="">Tất cả địa điểm</option>
              {[...new Set(jobs.map((j) => j.location))].map((l) => (
                <option key={l}>{l}</option>
              ))}
            </select>
          </Field>
          <Field id="explore-skill" label="Kỹ năng">
            <select
              id="explore-skill"
              value={search.get("skill") || ""}
              onChange={(e) => filter("skill", e.target.value)}
            >
              <option value="">Tất cả kỹ năng</option>
              {skills.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
          <Field id="explore-mode" label="Hình thức làm việc">
            <select
              id="explore-mode"
              value={search.get("mode") || ""}
              onChange={(e) => filter("mode", e.target.value)}
            >
              <option value="">Tất cả hình thức</option>
              {Object.entries(workModes).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </Field>
          <button className="button secondary full" onClick={reset}>
            Xóa bộ lọc
          </button>
          <p className="filter-note">
            Lọc trên catalog đã tải từ API. Ngành nghề sẽ có khi kết nối
            VietJobs.
          </p>
        </aside>
        <section>
          <div className="results-heading">
            <h2>{filtered.length} công việc</h2>
            <span>Catalog hiện có</span>
          </div>
          {filtered.length ? (
            <>
              <div className="job-grid search-results">
                {filtered.slice(page * 9, page * 9 + 9).map((j) => (
                  <Card key={j.id} job={j} />
                ))}
              </div>
              <div className="button-row explore-pagination">
                <button
                  className="button secondary"
                  disabled={!page}
                  onClick={() => {
                    const n = new URLSearchParams(search);
                    n.set("page", String(page - 1));
                    setSearch(n);
                  }}
                >
                  Trang trước
                </button>
                <span>
                  Trang {page + 1}/{Math.ceil(filtered.length / 9)}
                </span>
                <button
                  className="button secondary"
                  disabled={(page + 1) * 9 >= filtered.length}
                  onClick={() => {
                    const n = new URLSearchParams(search);
                    n.set("page", String(page + 1));
                    setSearch(n);
                  }}
                >
                  Trang sau
                </button>
              </div>
            </>
          ) : (
            <Empty title="Không có kết quả cho bộ lọc này">
              <button className="button secondary" onClick={reset}>
                Xóa điều kiện
              </button>
            </Empty>
          )}
        </section>
      </div>
    </>
  );
}

function Detail({ jobs, id }: { jobs: CatalogJob[]; id: string }) {
  const job = jobs.find((j) => j.id === id);
  const neighbors = useQuery({
    queryKey: ["exploration", "similar", id],
    queryFn: ({ signal }) =>
      api<Similar>(`/exploration/jobs/${encodeURIComponent(id)}/similar`, {
        signal,
      }),
    enabled: !!job,
  });
  if (!job)
    return (
      <Empty title="Tin không có trong catalog hiện tại">
        <Link to="/explore/jobs" className="text-link">
          Về tìm kiếm
        </Link>
      </Empty>
    );
  return (
    <>
      <Link className="back-link" to="/explore/jobs">
        <ArrowLeft size={16} />
        Về tìm việc
      </Link>
      <div className="explore-detail-heading">
        <SourceBadge job={job} />
        <h2>{job.title}</h2>
        <p>
          {job.company} · {job.location} · {workModes[job.work_mode]}
        </p>
      </div>
      <div className="detail-columns">
        <section className="panel job-description">
          <h2>Nội dung công việc</h2>
          <p className="preserve-lines">{job.description}</p>
          <h2>Kỹ năng được khai báo</h2>
          <div className="tag-row">
            {job.requirements.map((s) => (
              <span className="skill-pill" key={s.id}>
                {s.name}
              </span>
            ))}
          </div>
          {!job.requirements.length && (
            <p>
              Chưa có dữ liệu kỹ năng; không thể kết luận tin không cần kỹ năng.
            </p>
          )}
          <h2>Nguồn dữ liệu</h2>
          <p>
            {job.origin === "seed"
              ? "Tin giả lập trong bộ seed, dùng kiểm tra chức năng."
              : job.source
                ? `Nguồn: ${job.source.publisher}`
                : "Tin nội bộ chưa có thông tin nguồn công khai."}
          </p>
          {job.source && (
            <a
              className="text-link"
              href={job.source.url}
              target="_blank"
              rel="noreferrer"
            >
              Xem nguồn công khai ↗
            </a>
          )}
        </section>
        <aside className="panel explore-detail-aside">
          <h2>Thông tin đối chiếu</h2>
          <strong>{money(job.salary_min, job.salary_max)}</strong>
          <p>
            {job.experience == null
              ? "Kinh nghiệm chưa được xác định"
              : `Yêu cầu: ${job.experience} năm kinh nghiệm`}
          </p>
          <Link className="button primary full" to="/explore/recommendations">
            Đối chiếu kỹ năng của tôi
          </Link>
          <Link
            className="button secondary full"
            to={`/explore/graph?job=${job.id}`}
          >
            Xem quan hệ kỹ năng
          </Link>
        </aside>
      </div>
      <div className="section-heading">
        <div>
          <h2>Công việc có kỹ năng tương tự</h2>
          <p className="muted">
            Jaccard trên kỹ năng trong catalog hiện có; chưa phải similarity
            batch Spark.
          </p>
        </div>
      </div>
      {neighbors.isPending ? (
        <Loading />
      ) : neighbors.isError ? (
        <ErrorState
          error={neighbors.error}
          retry={() => {
            void neighbors.refetch();
          }}
        />
      ) : neighbors.data.items.length ? (
        <div className="job-grid">
          {neighbors.data.items.map((r) => (
            <div key={r.job.id}>
              <div className="explore-similar-label">
                {Math.round(r.score * 100)}% kỹ năng tương tự ·{" "}
                {r.shared.map((s) => s.name).join(", ")}
              </div>
              <Card job={r.job} />
            </div>
          ))}
        </div>
      ) : (
        <Empty title="Chưa tìm thấy việc có kỹ năng chung">
          Thử một việc khác trong catalog.
        </Empty>
      )}
    </>
  );
}

function Recommendations({ jobs }: { jobs: CatalogJob[] }) {
  const policy = useQuery({
    queryKey: ["exploration", "policy"],
    queryFn: ({ signal }) =>
      api<components["schemas"]["ExplorationPolicy"]>("/exploration/policy", {
        signal,
      }),
  });
  const skills = [
    ...new Map(
      jobs.flatMap((j) => j.requirements).map((s) => [s.id, s]),
    ).values(),
  ];
  const [selected, setSelected] = useState<string[]>([]),
    [experience, setExperience] = useState(""),
    [location, setLocation] = useState(""),
    [mode, setMode] = useState(""),
    [limit, setLimit] = useState(10);
  const ranking = useMutation({
    mutationFn: (body: {
      skill_ids: string[];
      experience: number | null;
      location: string;
      work_mode: string | null;
      limit: number;
    }) =>
      api<Ranking>("/exploration/recommendations", { method: "POST", body }),
  });
  return (
    <div className="explore-recommend-layout">
      <form
        className="panel explore-profile"
        onSubmit={(e) => {
          e.preventDefault();
          ranking.mutate({
            skill_ids: selected,
            experience: experience === "" ? null : Number(experience),
            location,
            work_mode: mode || null,
            limit,
          });
        }}
      >
        <span className="eyebrow">HỒ SƠ THỬ NGHIỆM</span>
        <h2>Bạn mang theo kỹ năng gì?</h2>
        <p className="muted">
          Chọn ít nhất một tiêu chí. Thông tin chỉ dùng cho lần tính này.
        </p>
        <fieldset>
          <legend>Kỹ năng đã khai báo</legend>
          <div className="explore-skill-options">
            {skills.map((s) => (
              <label
                key={s.id}
                className={selected.includes(s.id) ? "selected" : ""}
              >
                <input
                  type="checkbox"
                  disabled={ranking.isPending}
                  checked={selected.includes(s.id)}
                  onChange={(e) => {
                    ranking.reset();
                    setSelected(
                      e.target.checked
                        ? [...selected, s.id]
                        : selected.filter((k) => k !== s.id),
                    );
                  }}
                />
                {s.name}
              </label>
            ))}
          </div>
        </fieldset>
        <Field id="preview-exp" label="Số năm kinh nghiệm">
          <input
            id="preview-exp"
            disabled={ranking.isPending}
            type="number"
            min="0"
            max="100"
            step="any"
            value={experience}
            placeholder="Chưa khai báo"
            onChange={(e) => {
              ranking.reset();
              setExperience(e.target.value);
            }}
          />
        </Field>
        <Field id="preview-location" label="Địa điểm ưu tiên">
          <select
            id="preview-location"
            disabled={ranking.isPending}
            value={location}
            onChange={(e) => {
              ranking.reset();
              setLocation(e.target.value);
            }}
          >
            <option value="">Không ưu tiên</option>
            {[...new Set(jobs.map((j) => j.location))].map((l) => (
              <option key={l}>{l}</option>
            ))}
          </select>
        </Field>
        <Field id="preview-mode" label="Hình thức ưu tiên">
          <select
            id="preview-mode"
            disabled={ranking.isPending}
            value={mode}
            onChange={(e) => {
              ranking.reset();
              setMode(e.target.value);
            }}
          >
            <option value="">Không ưu tiên</option>
            {Object.entries(workModes)
              .filter(([k]) => k !== "unspecified")
              .map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
          </select>
        </Field>
        <Field id="preview-limit" label="Số gợi ý tối đa (Top-K)">
          <select
            id="preview-limit"
            disabled={ranking.isPending || !policy.data}
            value={limit}
            onChange={(e) => {
              ranking.reset();
              setLimit(Number(e.target.value));
            }}
          >
            {[5, 10, 20, 50]
              .filter((value) => value <= (policy.data?.maximum_limit ?? 50))
              .map((value) => (
                <option key={value} value={value}>
                  {value} công việc
                </option>
              ))}
          </select>
        </Field>
        {policy.isError && (
          <ErrorState
            error={policy.error}
            retry={() => {
              void policy.refetch();
            }}
          />
        )}
        <button
          className="button primary full"
          disabled={
            ranking.isPending ||
            !policy.data ||
            (!selected.length && experience === "" && !location && !mode)
          }
        >
          <Sparkles size={17} />
          {ranking.isPending ? "Đang đối chiếu…" : "Xem gợi ý phù hợp"}
        </button>
        <p className="filter-note">
          {policy.data
            ? `Kỹ năng ${policy.data.weights.skills * 100}% · kinh nghiệm ${policy.data.weights.experience * 100}% · địa điểm ${policy.data.weights.location * 100}% · hình thức ${policy.data.weights.work_mode * 100}%.`
            : "Đang tải thông số đối chiếu…"}{" "}
          Tiêu chí chưa chọn được bỏ khỏi tổng trọng số. Điểm thử nghiệm chưa
          được hiệu chỉnh bằng đánh giá trên VietJobs.
        </p>
      </form>
      <section>
        <div className="results-heading">
          <h2>Gợi ý dành cho hồ sơ thử nghiệm</h2>
        </div>
        {ranking.isPending ? (
          <Loading />
        ) : ranking.isError ? (
          <ErrorState error={ranking.error} />
        ) : ranking.data ? (
          <>
            {ranking.data.truncated && (
              <p className="notice">Xếp hạng trên tối đa 1.000 tin đã tải.</p>
            )}
            <p className="muted explore-score-note">
              Điểm xếp hạng = điểm trên thông tin đã biết × coverage. Không phải
              xác suất được tuyển. Kỹ năng chỉ đối chiếu tên, chưa đánh giá mức
              thành thạo.
            </p>
            {ranking.data.items.map((r) => (
              <article className="panel explore-rank" key={r.job.id}>
                <div className="explore-rank-header">
                  <div>
                    <SourceBadge job={r.job} />
                    <h3>
                      <Link to={`/explore/jobs/${r.job.id}`}>
                        {r.job.title}
                      </Link>
                    </h3>
                    <p className="muted">
                      {r.job.company} · {r.job.location}
                    </p>
                  </div>
                  <div className="explore-score">
                    <strong>{r.score}</strong>
                    <small>điểm xếp hạng</small>
                  </div>
                </div>
                <div className="explore-score-meta">
                  <span>Điểm đã biết: {r.observed ?? "—"}/100</span>
                  <span>Coverage: {r.coverage}% trọng số</span>
                </div>
                <div className="explore-components">
                  {r.components.map((c) => (
                    <div key={c.key}>
                      <span>{c.label}</span>
                      <strong>
                        {c.value == null
                          ? "Chưa đủ dữ liệu"
                          : `${Math.round(c.value * 100)}%`}
                      </strong>
                    </div>
                  ))}
                </div>
                <div className="explore-gap">
                  <div>
                    <h4>
                      <Check size={15} /> Kỹ năng khớp
                    </h4>
                    <div className="tag-row">
                      {r.matched.length ? (
                        r.matched.map((s) => (
                          <span className="skill-pill matched" key={s.id}>
                            {s.name}
                          </span>
                        ))
                      ) : (
                        <small>Chưa có kỹ năng khớp đã khai báo.</small>
                      )}
                    </div>
                  </div>
                  <div>
                    <h4>Kỹ năng chưa khai báo</h4>
                    <div className="tag-row">
                      {r.gap.length ? (
                        r.gap.map((s) => (
                          <span className="skill-pill gap" key={s.id}>
                            {s.name}
                          </span>
                        ))
                      ) : (
                        <small>
                          {r.job.requirements.length
                            ? "Đã khai báo các kỹ năng của tin."
                            : "Tin chưa có thông tin kỹ năng."}
                        </small>
                      )}
                    </div>
                  </div>
                </div>
              </article>
            ))}
            {!ranking.data.items.length && (
              <Empty title="Catalog chưa có việc để gợi ý">
                Quay lại sau khi có dữ liệu.
              </Empty>
            )}
          </>
        ) : (
          <div className="panel explore-before">
            <Sparkles size={38} />
            <h2>Một hồ sơ, nhiều hướng đi</h2>
            <p>
              Chọn kỹ năng và ưu tiên bên trái để xem xếp hạng, lý do phù hợp và
              những kỹ năng chưa khai báo.
            </p>
            <Link className="text-link" to="/profile">
              Xem hồ sơ đã lưu <ArrowRight size={16} />
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}

function GraphPage({ jobs }: { jobs: CatalogJob[] }) {
  const [search, setSearch] = useSearchParams();
  const root = jobs.find((j) => j.id === search.get("job")) || jobs[0];
  return (
    <section className="panel explore-graph-panel">
      <div className="section-heading">
        <div>
          <h2>Những công việc kết nối qua kỹ năng</h2>
          <p className="muted">
            Chọn một việc để xem kỹ năng và các vị trí có liên quan.
          </p>
        </div>
      </div>
      {root ? (
        <>
          <Field id="graph-root" label="Công việc trung tâm">
            <select
              id="graph-root"
              value={root.id}
              onChange={(e) => setSearch({ job: e.target.value })}
            >
              {jobs.map((j) => (
                <option value={j.id} key={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
          </Field>
          <SkillGraph root={root} jobs={jobs} />
          <Link className="text-link" to={`/explore/jobs/${root.id}`}>
            Xem chi tiết công việc trung tâm →
          </Link>
        </>
      ) : (
        <Empty title="Chưa có dữ liệu graph">
          Cần có việc làm trong catalog.
        </Empty>
      )}
    </section>
  );
}

function Analytics({ jobs }: { jobs: CatalogJob[] }) {
  const [location, setLocation] = useState("");
  const scope = jobs.filter((j) => !location || j.location === location);
  const valid = scope.filter(
    (j) =>
      j.salary_min != null &&
      j.salary_max != null &&
      j.salary_min > 0 &&
      j.salary_max >= j.salary_min,
  );
  const average = valid.length
    ? valid.reduce((sum, j) => sum + (j.salary_min! + j.salary_max!) / 2, 0) /
      valid.length
    : null;
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Đọc dữ liệu trước khi ra quyết định</h2>
          <p className="muted">
            Tổng hợp trực tiếp từ catalog đã tải; chưa dùng bảng analytics
            Spark.
          </p>
        </div>
        <Field id="analytics-location" label="Phạm vi địa điểm">
          <select
            id="analytics-location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          >
            <option value="">Tất cả địa điểm</option>
            {[...new Set(jobs.map((j) => j.location))].map((l) => (
              <option key={l}>{l}</option>
            ))}
          </select>
        </Field>
      </div>
      <div className="explore-metrics">
        <div className="panel">
          <small>Tin trong phạm vi</small>
          <strong>{scope.length}</strong>
        </div>
        <div className="panel">
          <small>Tin có khoảng lương hợp lệ</small>
          <strong>
            {valid.length}/{scope.length}
          </strong>
        </div>
        <div className="panel">
          <small>Trung bình trung điểm khoảng lương</small>
          <strong className="metric-salary">
            {average == null
              ? "—"
              : `${(average / 1000000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} triệu`}
          </strong>
        </div>
        <div className="panel">
          <small>Tin thiếu kỹ năng yêu cầu</small>
          <strong>{scope.filter((j) => !j.requirements.length).length}</strong>
        </div>
      </div>
      <p className="notice">
        Lương được tính trên {valid.length} tin có hai cận dương hợp lệ; loại{" "}
        {scope.length - valid.length} tin thiếu/không đủ khoảng lương. Tin seed
        có mức lương giả lập. Không đại diện mức lương thị trường.
      </p>
      <div className="explore-analytics-grid">
        <Bars
          title="Kỹ năng được đề cập"
          rows={tally(
            scope.flatMap((j) => [
              ...new Set(j.requirements.map((s) => s.name)),
            ]),
          )}
          note="Số tin đề cập từng kỹ năng; một tin có thể có nhiều kỹ năng."
        />
        <Bars
          title="Phân bố địa điểm"
          rows={tally(scope.map((j) => j.location))}
          note="Địa điểm nguyên văn của catalog hiện có, chưa chuẩn hóa VietJobs."
        />
        <Bars
          title="Hình thức làm việc"
          rows={tally(scope.map((j) => workModes[j.work_mode] || j.work_mode))}
          note="Hình thức làm việc của tin; chưa phải loại hợp đồng VietJobs."
        />
        <Bars
          title="Yêu cầu kinh nghiệm"
          rows={tally(
            scope.map((j) =>
              j.experience == null ? "Chưa xác định" : `${j.experience} năm`,
            ),
          )}
          note="Số năm yêu cầu đã khai báo; không suy ra cấp độ nghề nghiệp."
        />
      </div>
    </>
  );
}
