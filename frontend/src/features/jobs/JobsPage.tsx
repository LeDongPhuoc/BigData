import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search, SlidersHorizontal } from "lucide-react";
import { api, params } from "../../lib/api";
import type { Job, Page } from "../../lib/types";
import { levels, workModes } from "../../lib/format";
import {
  Empty,
  ErrorState,
  Field,
  Heading,
  Loading,
  Pagination,
} from "../../components/ui";
import { JobCard } from "./JobCard";
import { useCompanies } from "./queries";
import { useMe } from "../../lib/query";
import { RecommendedJobs } from "./RecommendedJobs";

export function JobsPage() {
  const [search, setSearch] = useSearchParams(),
    companies = useCompanies();
  const candidate = useMe().data!.roles.includes("candidate"),
    recommended = candidate && search.get("view") === "recommended";
  const offset = Math.max(0, Math.min(996, Number(search.get("offset")) || 0));
  const filters = {
    q: search.get("q") || "",
    location: search.get("location") || "",
    work_mode: search.get("work_mode") || "",
    level: search.get("level") || "",
    company_id: search.get("company_id") || "",
  };
  const [draft, setDraft] = useState(filters.q);
  const editingDraft = useRef(false);
  useEffect(() => {
    if (!editingDraft.current) setDraft(filters.q);
  }, [filters.q]);
  const resetSearch = () => {
    editingDraft.current = false;
    setDraft("");
    setSearch(recommended ? { view: "recommended" } : {});
  };
  const jobs = useQuery({
    queryKey: ["jobs", "search", filters, offset],
    queryFn: ({ signal }) =>
      api<Page<Job>>("/jobs" + params({ ...filters, offset, limit: 12 }), {
        signal,
      }),
    enabled: !recommended,
  });
  const update = (name: string, value: string) => {
    // Router navigation can still be rendering when the next control is used.
    // Start from the current URL so a cleared filter cannot reappear from a stale render.
    const next = new URLSearchParams(window.location.search);
    value ? next.set(name, value) : next.delete(name);
    next.delete("offset");
    setSearch(next);
  };
  return (
    <>
      <Heading eyebrow="KHÁM PHÁ CƠ HỘI" title="Công việc tiếp theo của bạn">
        Tìm một vị trí phù hợp. Khám phá người có thể mở cánh cửa cho bạn.
      </Heading>
      {candidate && (
        <nav className="job-view-options" aria-label="Chọn danh sách việc làm">
          <Link
            className={`button ${recommended ? "secondary" : "primary"}`}
            to="/jobs"
            aria-current={recommended ? undefined : "page"}
          >
            Tất cả việc làm
          </Link>
          <Link
            className={`button ${recommended ? "primary" : "secondary"}`}
            to="/jobs?view=recommended"
            aria-current={recommended ? "page" : undefined}
          >
            Gợi ý theo hồ sơ
          </Link>
        </nav>
      )}
      <form
        className="search-bar"
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          const keyword = String(data.get("q") || "").trim();
          editingDraft.current = false;
          setDraft(keyword);
          update("q", keyword);
        }}
      >
        <Search size={21} aria-hidden="true" />
        <label className="sr-only" htmlFor="job-search">
          Từ khóa tìm việc
        </label>
        <input
          id="job-search"
          name="q"
          type="search"
          maxLength={160}
          placeholder="Tên công việc, kỹ năng hoặc doanh nghiệp…"
          value={draft}
          onChange={(event) => {
            editingDraft.current = true;
            setDraft(event.target.value);
          }}
        />
        <button className="button primary" type="submit">
          Tìm kiếm
        </button>
      </form>
      <div className="jobs-layout">
        <aside className="panel filter-panel">
          <h2>
            <SlidersHorizontal size={18} />
            Bộ lọc
          </h2>
          <Field label="Địa điểm" id="filter-location">
            <input
              id="filter-location"
              maxLength={120}
              value={filters.location}
              placeholder="Ví dụ: HCMC"
              onChange={(event) => update("location", event.target.value)}
            />
          </Field>
          <Field label="Hình thức làm việc" id="filter-mode">
            <select
              id="filter-mode"
              value={filters.work_mode}
              onChange={(event) => update("work_mode", event.target.value)}
            >
              <option value="">Tất cả hình thức</option>
              {Object.entries(workModes).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Cấp độ" id="filter-level">
            <select
              id="filter-level"
              value={filters.level}
              onChange={(event) => update("level", event.target.value)}
            >
              <option value="">Tất cả cấp độ</option>
              {Object.entries(levels).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Doanh nghiệp" id="filter-company">
            <select
              id="filter-company"
              value={filters.company_id}
              onChange={(event) => update("company_id", event.target.value)}
              disabled={companies.isPending || companies.isError}
            >
              <option value="">Tất cả doanh nghiệp</option>
              {companies.data?.items.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </Field>
          {companies.isError && (
            <ErrorState
              error={companies.error}
              retry={() => {
                void companies.refetch();
              }}
            />
          )}
          {companies.data?.truncated && (
            <p className="notice">
              Danh sách đang hiển thị tối đa 1.100 doanh nghiệp. Bạn có thể tìm
              bằng tên trong ô từ khóa.
            </p>
          )}
          <button
            className="button secondary full"
            type="button"
            disabled={!Object.values(filters).some(Boolean)}
            onClick={resetSearch}
          >
            Xóa bộ lọc
          </button>
          <p className="filter-note">
            Chỉ hiển thị tin đang mở tại doanh nghiệp hoạt động.
          </p>
        </aside>
        <section aria-label="Kết quả việc làm">
          <div className="results-heading">
            <h2>
              {filters.q
                ? `Kết quả cho “${filters.q}”`
                : recommended
                  ? "Gợi ý theo hồ sơ của bạn"
                  : "Vị trí đang tuyển"}
            </h2>
            <span>
              {recommended ? "Điểm phù hợp cao trước" : "Mới nhất trước"}
            </span>
          </div>
          {recommended ? (
            <RecommendedJobs
              companies={companies.data?.items}
              filters={filters}
              offset={offset}
              onPage={(value) => {
                const next = new URLSearchParams(window.location.search);
                next.set("offset", String(value));
                setSearch(next);
              }}
            />
          ) : jobs.isPending ? (
            <Loading label="Đang tìm việc làm…" />
          ) : jobs.isError ? (
            <ErrorState
              error={jobs.error}
              retry={() => {
                void jobs.refetch();
              }}
            />
          ) : jobs.data.items.length ? (
            <>
              <div className="job-grid search-results">
                {jobs.data.items.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    company={companies.data?.items.find(
                      (company) => company.id === job.company_id,
                    )}
                  />
                ))}
              </div>
              <Pagination
                offset={offset}
                more={jobs.data.has_more}
                busy={jobs.isFetching}
                onChange={(value) => {
                  const next = new URLSearchParams(window.location.search);
                  next.set("offset", String(value));
                  setSearch(next);
                }}
              />
            </>
          ) : (
            <Empty title="Chưa tìm thấy công việc phù hợp">
              <p>Thử từ khóa khác hoặc bớt điều kiện lọc.</p>
              <button className="button secondary" onClick={resetSearch}>
                Xóa điều kiện tìm kiếm
              </button>
            </Empty>
          )}
        </section>
      </div>
    </>
  );
}
