import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigationType, useSearchParams } from "react-router-dom";
import { ArrowLeft, Database, Search } from "lucide-react";
import { api } from "../../lib/api";
import { Badge, Empty, ErrorState, Field, Loading } from "../../components/ui";
import type { components } from "../../lib/api.generated";

type Assessment = components["schemas"]["RawAssessment"];
type RawJob = components["schemas"]["RawJob"];
type RawPage = components["schemas"]["RawJobsPage"];
type Detail = components["schemas"]["RawJobDetail"];
type CountRow = components["schemas"]["CountRow"];
const pretty = (value: string) => value.replaceAll("_", " ");
const count = (value: number) => value.toLocaleString("vi-VN");
type ChangeParams = (change: (next: URLSearchParams) => void) => void;

function useRawNavigation() {
  const [urlParams, setUrlParams] = useSearchParams();
  const navigationType = useNavigationType();
  const [params, setLocalParams] = useState(urlParams);
  const current = useRef(urlParams);
  const pending = useRef<string | null>(null);
  useEffect(() => {
    // Ignore intermediate router transitions after another filter changed.
    if (
      pending.current !== null &&
      pending.current !== urlParams.toString() &&
      navigationType !== "POP"
    )
      return;
    pending.current = null;
    current.current = urlParams;
    setLocalParams(urlParams);
  }, [urlParams, navigationType]);
  const changeParams: ChangeParams = (change) => {
    const next = new URLSearchParams(current.current);
    change(next);
    current.current = next;
    pending.current = next.toString();
    setLocalParams(next);
    setUrlParams(next);
  };
  return { params, changeParams };
}
const flagNames: Record<string, string> = {
  salary_zero_placeholder: "Lương 0/0: chưa có mức lương định lượng",
  salary_text_numeric_conflict: "Lương dạng chữ và cột số khác nhau",
  salary_incomplete_bounds: "Khoảng lương thiếu một cận dương",
  salary_inverted_bounds: "Cận lương tối đa nhỏ hơn tối thiểu",
  salary_invalid_number: "Cột số lương không hợp lệ",
  salary_foreign_currency_text: "Lương dạng chữ có ngoại tệ",
  language_unknown_token: "Ngôn ngữ có token chưa xác định",
  experience_unparsed: "Kinh nghiệm chưa chuyển được sang năm",
};

function Distribution({
  title,
  rows,
  note,
}: {
  title: string;
  rows: CountRow[];
  note: string;
}) {
  const max = Math.max(1, ...rows.map((row) => row.count));
  return (
    <section className="panel explore-bars">
      <h3>{title}</h3>
      <p className="muted">{note}</p>
      {rows.slice(0, 10).map((row) => (
        <div className="bar-row" key={row.label}>
          <div>
            <span>{pretty(row.label)}</span>
            <strong>{count(row.count)}</strong>
          </div>
          <div className="bar-track">
            <span style={{ width: `${(100 * row.count) / max}%` }} />
          </div>
        </div>
      ))}
    </section>
  );
}

export function RawDataPage() {
  const { params, changeParams } = useRawNavigation();
  const profile = useQuery({
    queryKey: ["exploration", "raw-profile"],
    staleTime: 300000,
    queryFn: ({ signal }) =>
      api<Assessment>("/exploration/raw/profile", { signal, timeoutMs: 90000 }),
  });
  const row = params.get("row");
  if (profile.isPending)
    return (
      <Loading label="Đang khảo sát CSV đầy đủ; lần đầu có thể mất khoảng một phút…" />
    );
  if (profile.isError)
    return (
      <ErrorState
        error={profile.error}
        retry={() => {
          void profile.refetch();
        }}
      />
    );
  const data = profile.data.raw;
  if (row)
    return (
      <RawDetail
        id={row}
        back={() => {
          changeParams((next) => next.delete("row"));
        }}
      />
    );
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Khảo sát dữ liệu gốc VietJobs</h2>
          <p className="muted">
            Số liệu toàn file CSV. Đọc raw để kiểm tra trước khi thiết kế
            pipeline.
          </p>
        </div>
        <Badge>Raw · chưa qua Spark</Badge>
      </div>
      <div className="explore-metrics">
        {[
          ["Bản ghi raw", data.rows],
          ["Cột dữ liệu", data.column_count],
          ["Nhóm nghề", data.categories.length],
          ["Dòng trùng hoàn toàn", data.exact_duplicate_rows],
        ].map(([label, value]) => (
          <div className="panel" key={label}>
            <small>{label}</small>
            <strong>{count(Number(value))}</strong>
          </div>
        ))}
      </div>
      <div className="panel raw-context">
        <Database size={22} />
        <div>
          <h3>Database và CSV là hai nguồn riêng</h3>
          <p>
            ArangoDB hiện có {count(profile.data.database_counts.jobs)} tin,{" "}
            {count(profile.data.database_counts.skills)} kỹ năng,{" "}
            {count(profile.data.database_counts.companies)} công ty và{" "}
            {count(profile.data.database_counts.users)} tài khoản. CSV không
            cung cấp công ty, URL tin, ngày đăng hoặc quan hệ giới thiệu; các
            bản ghi bên dưới chưa nối mạng lưới này.
          </p>
          <p className="muted">
            Nguồn: {data.file_name} ·{" "}
            {(data.source_bytes / 1024 / 1024).toFixed(1)} MiB · SHA-256:{" "}
            <code>{data.source_sha256}</code>
          </p>
        </div>
      </div>
      <div className="explore-analytics-grid">
        <Distribution
          title="Phân bố nhóm nghề"
          rows={data.categories}
          note={`Toàn bộ ${count(data.rows)} dòng raw, có cả dòng trùng. Hiển thị 10 nhóm nhiều nhất.`}
        />
        <Distribution
          title="Loại hợp đồng theo CSV"
          rows={data.contracts}
          note="Giữ nguyên nhãn nguồn. Toàn thời gian khác với hình thức onsite/remote/hybrid."
        />
      </div>
      <section className="panel raw-quality">
        <h3>Điểm cần xử lý trước khi khai thác</h3>
        <ul>
          {data.quality_flags.map((flag) => (
            <li key={flag.label}>
              <strong>{count(flag.count)}</strong> dòng ·{" "}
              {flagNames[flag.label] || pretty(flag.label)}
            </li>
          ))}
        </ul>
        <p>
          Lương số được nguồn công bố theo triệu VND/tháng. Giữ nguyên chữ và số
          để đối chiếu, chưa tự sửa mâu thuẫn.{" "}
          <a
            className="text-link"
            href={data.salary.source}
            target="_blank"
            rel="noopener noreferrer"
          >
            Tài liệu nguồn ↗
          </a>
        </p>
        <p>
          Trung vị trung điểm khoảng lương đủ điều kiện:{" "}
          <strong>{data.salary.median_midpoint_million ?? "—"} triệu</strong>{" "}
          trên {count(data.salary.eligible_raw_rows)} dòng raw; loại{" "}
          {count(data.salary.excluded_raw_rows)} dòng thiếu cận, 0/0 hoặc có cờ
          lương. Có cả dòng trùng, chưa phải thống kê thị trường sau làm sạch.
        </p>
        <p>
          {count(data.comma_location_rows)} dòng có dấu phẩy trong địa điểm; sau
          bỏ token lặp, {count(data.multi_location_rows)} dòng có nhiều địa
          điểm. Địa điểm vẫn theo nguyên văn nguồn, chưa ánh xạ đơn vị hành
          chính.
        </p>
        <div className="raw-table-wrap">
          <table className="raw-table">
            <caption>Độ thiếu dữ liệu theo từng cột raw</caption>
            <thead>
              <tr>
                <th scope="col">Cột</th>
                <th scope="col">Thiếu/rỗng</th>
                <th scope="col">Tỷ lệ</th>
                <th scope="col">Dài nhất</th>
              </tr>
            </thead>
            <tbody>
              {data.fields.map((field) => (
                <tr key={field.name}>
                  <th scope="row">
                    <code>{field.name}</code>
                  </th>
                  <td>{count(field.missing)}</td>
                  <td>{((100 * field.missing) / data.rows).toFixed(2)}%</td>
                  <td>{field.max_length} ký tự</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted">
          Các cột kỹ năng, bằng cấp, phúc lợi chứa list dạng chuỗi và được parse
          an toàn; ngôn ngữ là chuỗi tách dấu phẩy, UNK là chưa xác định. Thiếu
          hoặc list rỗng không chứng minh tin không cần kỹ năng.
        </p>
      </section>
      <RawBrowser
        profile={profile.data}
        params={params}
        changeParams={changeParams}
      />
      <div className="explore-next panel">
        <div>
          <h3>Bước tiếp theo: chuẩn hóa và nối dữ liệu</h3>
          <p>
            Khảo sát raw giúp chọn quy tắc xử lý. Gợi ý và graph hiện có tiếp
            tục dùng catalog ArangoDB; dữ liệu VietJobs sẽ được nối sau bước
            Spark, kiểm tra chất lượng và thiết kế graph.
          </p>
        </div>
        <Link className="text-link" to="/explore/recommendations">
          Thử gợi ý catalog hiện có →
        </Link>
      </div>
    </>
  );
}

function RawBrowser({
  profile,
  params,
  changeParams,
}: {
  profile: Assessment;
  params: URLSearchParams;
  changeParams: ChangeParams;
}) {
  const keyword = params.get("q") || "";
  const [draft, setDraft] = useState(keyword);
  useEffect(() => setDraft(keyword), [keyword]);
  const uniqueOnly = params.get("unique_only") !== "false";
  const filter = (key: string, value: string) => {
    changeParams((next) => {
      value ? next.set(key, value) : next.delete(key);
      next.delete("offset");
    });
  };
  const query = new URLSearchParams();
  for (const key of [
    "q",
    "category",
    "location",
    "country",
    "contract",
    "experience_max",
    "unique_only",
    "offset",
  ])
    if (params.has(key)) query.set(key, params.get(key)!);
  query.set("limit", "12");
  const rows = useQuery({
    queryKey: ["exploration", "raw-jobs", query.toString()],
    queryFn: ({ signal }) =>
      api<RawPage>(`/exploration/raw/jobs?${query}`, { signal }),
  });
  const options: [string, string, CountRow[]][] = [
    ["category", "Nhóm nghề raw", profile.raw.categories],
    ["location", "Địa điểm raw", profile.raw.locations],
    ["country", "Quốc gia raw", profile.raw.countries],
    ["contract", "Loại hợp đồng raw", profile.raw.contracts],
  ];
  return (
    <section className="raw-browser">
      <div className="section-heading">
        <div>
          <h2>Xem bản ghi CSV thực tế</h2>
          <p className="muted">
            Tìm và phân trang trên toàn file; không giới hạn 1.000 tin như
            catalog seed.
          </p>
        </div>
      </div>
      <form
        className="search-bar"
        onSubmit={(event) => {
          event.preventDefault();
          filter("q", draft.trim());
        }}
      >
        <Search size={20} />
        <label htmlFor="raw-q" className="sr-only">
          Từ khóa raw
        </label>
        <input
          id="raw-q"
          value={draft}
          maxLength={160}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Tên công việc, nhóm nghề, kỹ năng…"
        />
        <button className="button primary">Tìm trong CSV</button>
      </form>
      <div className="panel raw-filters">
        {options.map(([key, label, values]) => (
          <Field key={key} id={`raw-${key}`} label={label}>
            <select
              id={`raw-${key}`}
              value={params.get(key) || ""}
              onChange={(event) => filter(key, event.target.value)}
            >
              <option value="">Tất cả</option>
              {values.map((value) => (
                <option key={value.label} value={value.label}>
                  {pretty(value.label)}
                </option>
              ))}
            </select>
          </Field>
        ))}
        <Field id="raw-experience" label="Kinh nghiệm tối đa đáp ứng">
          <select
            id="raw-experience"
            value={params.get("experience_max") || ""}
            onChange={(event) => filter("experience_max", event.target.value)}
          >
            <option value="">Không lọc</option>
            <option value="0">Không yêu cầu</option>
            <option value="0.25">3 tháng</option>
            <option value="0.5">6 tháng</option>
            <option value="1">1 năm</option>
            <option value="2">2 năm</option>
            <option value="5">5 năm</option>
          </select>
        </Field>
        <label className="raw-unique">
          <input
            type="checkbox"
            checked={uniqueOnly}
            onChange={(event) => {
              filter("unique_only", String(event.target.checked));
            }}
          />
          Ẩn dòng trùng hoàn toàn
        </label>
        <button
          className="button secondary"
          onClick={() => {
            setDraft("");
            changeParams((next) => {
              for (const key of [...next.keys()]) next.delete(key);
            });
          }}
        >
          Xóa bộ lọc raw
        </button>
      </div>
      <p className="filter-note">
        Từ khóa tìm trong tên, nhóm nghề, kỹ năng chuyên môn và kỹ năng mềm;
        chưa tìm full-text trong mô tả. Địa điểm so khớp token tách dấu phẩy;
        tháng kinh nghiệm được đổi sang năm /12.
      </p>
      {rows.isPending ? (
        <Loading />
      ) : rows.isError ? (
        <ErrorState
          error={rows.error}
          retry={() => {
            void rows.refetch();
          }}
        />
      ) : (
        <>
          <div className="results-heading">
            <h3>{count(rows.data.total)} bản ghi phù hợp</h3>
            <span>
              Trang {Math.floor(rows.data.offset / rows.data.limit) + 1}
            </span>
          </div>
          {rows.data.items.length ? (
            <div className="job-grid raw-results">
              {rows.data.items.map((job) => (
                <RawCard
                  key={job.id}
                  job={job}
                  open={() => {
                    changeParams((next) => next.set("row", job.id));
                  }}
                />
              ))}
            </div>
          ) : (
            <Empty title="Không có bản ghi trong trang/bộ lọc này">
              Thử xóa bộ lọc hoặc quay về trang trước.
            </Empty>
          )}
          <div className="button-row explore-pagination">
            <button
              className="button secondary"
              disabled={rows.data.offset === 0}
              onClick={() => {
                changeParams((next) =>
                  next.set(
                    "offset",
                    String(Math.max(0, rows.data.offset - rows.data.limit)),
                  ),
                );
              }}
            >
              Trang raw trước
            </button>
            <span>{count(rows.data.total)} kết quả</span>
            <button
              className="button secondary"
              disabled={!rows.data.has_more}
              onClick={() => {
                changeParams((next) =>
                  next.set(
                    "offset",
                    String(rows.data.offset + rows.data.limit),
                  ),
                );
              }}
            >
              Trang raw sau
            </button>
          </div>
        </>
      )}
    </section>
  );
}

function RawCard({ job, open }: { job: RawJob; open: () => void }) {
  return (
    <article className="panel explore-job raw-job">
      <small>VietJobs CSV · bản ghi #{job.row_number}</small>
      <h3>
        <button className="raw-title-link" onClick={open}>
          {job.title}
        </button>
      </h3>
      <div className="tag-row">
        <Badge>Raw VietJobs</Badge>
        <span>{job.country}</span>
      </div>
      <p>{job.location}</p>
      <strong className="explore-salary">
        {job.salary_raw || "Chưa có thông tin lương"}
      </strong>
      <p>
        {job.contract_type} · {job.experience_raw}
      </p>
      <small>{pretty(job.category)}</small>
      <div className="tag-row">
        {job.technical_skills.slice(0, 3).map((skill) => (
          <span className="skill-pill" key={skill}>
            {skill}
          </span>
        ))}
      </div>
      {!!job.flags.length && (
        <small className="raw-warning">
          Có {job.flags.length} điểm cần kiểm tra
        </small>
      )}
      {job.duplicate_of != null && (
        <Badge>Trùng bản ghi #{job.duplicate_of}</Badge>
      )}
      <button className="button secondary" onClick={open}>
        Đọc bản ghi gốc
      </button>
    </article>
  );
}

function RawDetail({ id, back }: { id: string; back: () => void }) {
  const detail = useQuery({
    queryKey: ["exploration", "raw-detail", id],
    queryFn: ({ signal }) =>
      api<Detail>(`/exploration/raw/jobs/${encodeURIComponent(id)}`, {
        signal,
      }),
  });
  return (
    <>
      <button className="button secondary" onClick={back}>
        <ArrowLeft size={16} />
        Về khảo sát CSV
      </button>
      {detail.isPending ? (
        <Loading />
      ) : detail.isError ? (
        <ErrorState
          error={detail.error}
          retry={() => {
            void detail.refetch();
          }}
        />
      ) : (
        <>
          <div className="explore-detail-heading">
            <Badge>Raw VietJobs · #{detail.data.job.row_number}</Badge>
            <h2>{detail.data.job.title}</h2>
            <p>
              {detail.data.job.location} · {detail.data.job.country} ·{" "}
              {detail.data.job.contract_type}
            </p>
          </div>
          <p className="notice">
            Bản ghi lịch sử từ CSV, chưa xác minh tin còn tuyển. Nguồn không có
            công ty/URL/ngày đăng; không có đường giới thiệu cho bản ghi này.
          </p>
          <div className="detail-columns">
            <section className="panel job-description">
              <h3>Mô tả theo nguồn</h3>
              <p className="preserve-lines">{detail.data.raw.description}</p>
              <h3>Yêu cầu theo nguồn</h3>
              <p className="preserve-lines">
                {detail.data.raw.requirements_text}
              </p>
            </section>
            <aside className="panel explore-detail-aside">
              <h3>Lương và kinh nghiệm</h3>
              <strong>{detail.data.job.salary_raw}</strong>
              <p>
                Cột số gốc: {detail.data.job.salary_min_million} –{" "}
                {detail.data.job.salary_max_million} triệu VND/tháng
              </p>
              <p>
                Kinh nghiệm gốc: {detail.data.job.experience_raw}; giá trị đổi
                sang năm:{" "}
                {detail.data.job.experience_years?.toLocaleString("vi-VN", {
                  maximumFractionDigits: 4,
                }) ?? "Chưa xác định"}
              </p>
              {detail.data.job.flags.map((flag) => (
                <p className="raw-warning" key={flag}>
                  {flagNames[flag] || pretty(flag)}
                </p>
              ))}
            </aside>
          </div>
          <div className="explore-analytics-grid">
            {[
              ["Kỹ năng chuyên môn", detail.data.job.technical_skills],
              ["Kỹ năng mềm", detail.data.job.soft_skills],
              ["Ngôn ngữ", detail.data.job.languages],
            ].map(([label, values]) => (
              <section className="panel explore-bars" key={String(label)}>
                <h3>{String(label)}</h3>
                <div className="tag-row">
                  {(values as string[]).map((value) => (
                    <span className="skill-pill" key={value}>
                      {value}
                    </span>
                  ))}
                </div>
                {!(values as string[]).length && (
                  <p>Chưa có dữ liệu xác định trong trường nguồn.</p>
                )}
              </section>
            ))}
          </div>
          <details className="panel raw-original">
            <summary>Đối chiếu đủ 18 trường nguyên gốc</summary>
            <dl>
              {Object.entries(detail.data.raw).map(([name, value]) => (
                <div key={name}>
                  <dt>
                    <code>{name}</code>
                  </dt>
                  <dd className="preserve-lines">{value || "(rỗng)"}</dd>
                </div>
              ))}
            </dl>
          </details>
        </>
      )}
    </>
  );
}
