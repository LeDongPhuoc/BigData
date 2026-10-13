import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, BriefcaseBusiness, Network, Send } from "lucide-react";
import { api } from "../../lib/api";
import { useMe } from "../../lib/query";
import type {
  Company,
  Job,
  Page,
  Referral,
  UserSummary,
} from "../../lib/types";
import { Empty, ErrorState, Heading, Loading } from "../../components/ui";
import { JobCard } from "../jobs/JobCard";
import { RecommendedJobs } from "../jobs/RecommendedJobs";

export function DashboardPage() {
  const user = useMe().data!;
  const jobs = useQuery({
    queryKey: ["jobs", "dashboard"],
    queryFn: ({ signal }) => api<Page<Job>>("/jobs?limit=4", { signal }),
  });
  const companies = useQuery({
    queryKey: ["companies", "dashboard"],
    queryFn: ({ signal }) =>
      api<Page<Company>>("/companies?limit=100", { signal }),
  });
  const connections = useQuery({
    queryKey: ["connections", "dashboard"],
    queryFn: ({ signal }) =>
      api<Page<UserSummary>>("/graph/connections?limit=100", { signal }),
  });
  const referrals = useQuery({
    queryKey: ["referrals", "dashboard"],
    queryFn: ({ signal }) =>
      api<Page<Referral>>("/referral-requests/me?limit=100", { signal }),
  });
  return (
    <>
      <Heading
        eyebrow="HÀNH TRÌNH NGHỀ NGHIỆP"
        title={`Chào ${user.display_name.split(" ").slice(-1)[0]}, cùng mở thêm cơ hội.`}
      >
        Những kết nối hôm nay có thể trở thành bước tiến ngày mai.
      </Heading>
      <Link
        to="/explore"
        className="panel"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "20px",
          marginBottom: "22px",
          gap: "16px",
        }}
      >
        <div>
          <h2>Khám phá việc làm qua kỹ năng</h2>
          <p>
            Thử gợi ý, xem kỹ năng chưa khai báo, việc tương tự và phân tích
            trên catalog hiện có.
          </p>
        </div>
        <ArrowRight size={22} />
      </Link>
      <section className="welcome-banner">
        <div>
          <span className="banner-label">BƯỚC TIẾP THEO CỦA BẠN</span>
          <h2>
            Công việc tốt hơn,
            <br />
            qua những người bạn biết.
          </h2>
          <p>
            Khám phá vị trí đang tuyển và tìm một đường kết nối đến người giới
            thiệu phù hợp.
          </p>
          <Link to="/jobs" className="button light">
            Khám phá việc làm <ArrowRight size={17} />
          </Link>
        </div>
        <div className="banner-graph" aria-hidden="true">
          <span className="banner-node center">Bạn</span>
          <span className="banner-node first">
            <Network size={26} />
          </span>
          <span className="banner-node second">
            <BriefcaseBusiness size={28} />
          </span>
          <span className="banner-line one" />
          <span className="banner-line two" />
          <span className="banner-caption">Mỗi kết nối, một khả năng mới.</span>
        </div>
      </section>
      <div className="overview-grid">
        <Link to="/network" className="overview-card">
          <Network size={23} />
          <div>
            <strong>
              {connections.isPending
                ? "…"
                : connections.isError
                  ? "—"
                  : `${connections.data.items.length}${connections.data.has_more ? "+" : ""}`}
            </strong>
            <span>Kết nối được chia sẻ</span>
          </div>
          <ArrowRight size={17} />
        </Link>
        <Link to="/referrals" className="overview-card">
          <Send size={23} />
          <div>
            <strong>
              {referrals.isPending
                ? "…"
                : referrals.isError
                  ? "—"
                  : `${referrals.data.items.length}${referrals.data.has_more ? "+" : ""}`}
            </strong>
            <span>Yêu cầu của bạn</span>
          </div>
          <ArrowRight size={17} />
        </Link>
        <Link to="/profile" className="overview-card profile-prompt">
          <div>
            <strong>Hồ sơ là điểm bắt đầu</strong>
            <span>Cập nhật kỹ năng để cải thiện kết quả phù hợp</span>
          </div>
          <ArrowRight size={18} />
        </Link>
      </div>
      {(connections.isError || referrals.isError) && (
        <ErrorState
          error={connections.error || referrals.error}
          retry={() => {
            void connections.refetch();
            void referrals.refetch();
          }}
        />
      )}
      {user.roles.includes("candidate") && (
        <section aria-label="Gợi ý việc làm theo hồ sơ">
          <div className="section-heading">
            <div>
              <h2>Gợi ý theo hồ sơ của bạn</h2>
              <p>
                Có kỹ năng khớp với hồ sơ; xếp hạng theo kỹ năng, kinh nghiệm và
                mong muốn làm việc. Điểm không phải xác suất được tuyển.
              </p>
            </div>
            <Link className="text-link" to="/jobs?view=recommended">
              Xem tất cả gợi ý <ArrowRight size={16} />
            </Link>
          </div>
          <RecommendedJobs companies={companies.data?.items} limit={4} />
        </section>
      )}
      <section>
        <div className="section-heading">
          <div>
            <h2>Cơ hội đang mở</h2>
            <p>Các vị trí mới nhất từ doanh nghiệp đang hoạt động.</p>
          </div>
          <Link className="text-link" to="/jobs">
            Xem tất cả <ArrowRight size={16} />
          </Link>
        </div>
        {jobs.isPending ? (
          <Loading />
        ) : jobs.isError ? (
          <ErrorState
            error={jobs.error}
            retry={() => {
              void jobs.refetch();
            }}
          />
        ) : jobs.data.items.length ? (
          <div className="job-grid">
            {jobs.data.items.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                company={companies.data?.items.find(
                  (c) => c.id === job.company_id,
                )}
              />
            ))}
          </div>
        ) : (
          <Empty title="Chưa có vị trí đang tuyển">
            Hãy quay lại sau để khám phá cơ hội mới.
          </Empty>
        )}
      </section>
    </>
  );
}
