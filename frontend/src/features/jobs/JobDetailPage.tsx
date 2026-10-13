import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  ExternalLink,
  MapPin,
  Network,
  Wallet,
} from "lucide-react";
import { api } from "../../lib/api";
import { useMe } from "../../lib/query";
import type { Company, MatchResult, Page, Skill } from "../../lib/types";
import { dateTime, levels, money, workModes } from "../../lib/format";
import { Badge, ErrorState, Heading, Loading } from "../../components/ui";
import { useJob } from "./queries";

export function JobDetailPage() {
  const { jobId = "" } = useParams(),
    user = useMe().data!,
    job = useJob(jobId);
  const company = useQuery({
    queryKey: ["companies", "detail", job.data?.company_id],
    queryFn: ({ signal }) =>
      api<Company>(`/companies/${encodeURIComponent(job.data!.company_id)}`, {
        signal,
      }),
    enabled: !!job.data,
  });
  const matching = useQuery({
    queryKey: ["matching", jobId],
    queryFn: ({ signal }) =>
      api<Page<MatchResult>>(`/jobs/${encodeURIComponent(jobId)}/matching`, {
        signal,
      }),
    enabled: user.roles.includes("candidate") && !!job.data,
  });
  const skills = useQuery({
    queryKey: ["skills", "names"],
    queryFn: ({ signal }) => api<Page<Skill>>("/skills?limit=100", { signal }),
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
  const data = job.data,
    match = matching.data?.items[0];
  return (
    <>
      <Link className="back-link" to="/jobs">
        <ArrowLeft size={16} />
        Danh sách việc làm
      </Link>
      <Heading
        eyebrow={company.data?.name || "TIN TUYỂN DỤNG"}
        title={data.title}
      >
        <span className="inline-meta">
          <span>
            <MapPin size={16} />
            {data.location}
          </span>
          <span>
            <Wallet size={16} />
            {money(data.salary_min, data.salary_max)}
          </span>
        </span>
      </Heading>
      <div className="detail-columns">
        <section className="panel job-description">
          <div className="tag-row">
            <Badge tone="green">Đang tuyển</Badge>
            <Badge>{workModes[data.work_mode]}</Badge>
            <Badge>{levels[data.level]}</Badge>
          </div>
          <h2>Về công việc</h2>
          <p className="preserve-lines">{data.description}</p>
          <h2>Kinh nghiệm</h2>
          <p>
            {data.min_experience_years == null
              ? "Số năm kinh nghiệm chưa được chuẩn hóa từ nguồn"
              : `Tối thiểu ${data.min_experience_years} năm kinh nghiệm`}{" "}
            · Cấp độ {levels[data.level]}
          </p>
          <h2>
            {data.source
              ? "Kỹ năng được nhắc trong tin gốc"
              : "Kỹ năng yêu cầu"}
          </h2>
          {data.requirements.length ? (
            <ul className="requirement-list">
              {data.requirements.map((requirement) => (
                <li key={requirement.skill_id}>
                  <strong>
                    {skills.data?.items.find(
                      (skill) => skill.id === requirement.skill_id,
                    )?.name || requirement.skill_id}
                  </strong>
                  <span>
                    {data.source
                      ? "Nhận diện từ nội dung; xem yêu cầu tại tin gốc"
                      : `${requirement.kind === "required" ? "Bắt buộc" : "Ưu tiên"} · Mức ${requirement.min_proficiency}/5 · ${requirement.min_years} năm`}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">
              Doanh nghiệp chưa khai báo yêu cầu kỹ năng riêng.
            </p>
          )}
          {skills.isError && (
            <ErrorState
              error={skills.error}
              retry={() => {
                void skills.refetch();
              }}
            />
          )}
          {data.source && (
            <div className="source-attribution">
              <h2>Nguồn thông tin</h2>
              <p>Nhà đăng tin: {data.source.publisher}</p>
              <p className="muted">
                Ghi nhận: {dateTime(data.source.retrieved_at)}
              </p>
              <a
                className="button secondary"
                href={data.source.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Xem tin tuyển dụng gốc <ExternalLink size={16} />
              </a>
              {(data.source.notes ?? []).map((note, index) => (
                <p className="muted" key={index}>
                  {note}
                </p>
              ))}
            </div>
          )}
        </section>
        <aside className="detail-aside">
          <section className="panel referral-callout">
            <Network size={29} />
            <h2>Một kết nối gần hơn với cơ hội</h2>
            <p>
              Tìm người đang làm việc tại doanh nghiệp này qua mạng lưới của
              bạn.
            </p>
            <Link className="button primary full" to={`/jobs/${data.id}/paths`}>
              Xem đường giới thiệu <ArrowRight size={16} />
            </Link>
          </section>
          {user.roles.includes("candidate") && (
            <section className="panel matching-panel">
              <h2>Mức độ phù hợp</h2>
              {matching.isPending ? (
                <Loading />
              ) : matching.isError ? (
                <ErrorState
                  error={matching.error}
                  retry={() => {
                    void matching.refetch();
                  }}
                />
              ) : match ? (
                <>
                  <div className="match-score">
                    <strong>
                      {Math.round(match.score * 100)}
                      <small>/100</small>
                    </strong>
                    <Badge tone={match.eligible ? "green" : "amber"}>
                      {data.source
                        ? "Đánh giá theo dữ liệu đã chuẩn hóa"
                        : match.eligible
                          ? "Đạt yêu cầu bắt buộc"
                          : "Còn thiếu kỹ năng"}
                    </Badge>
                  </div>
                  {Object.entries(match.explanation.components).map(
                    ([key, value]) => (
                      <div className="match-component" key={key}>
                        <span>
                          {(
                            {
                              skill: "Kỹ năng",
                              experience: "Kinh nghiệm",
                              location: "Địa điểm",
                              level: "Cấp độ",
                              work_mode: "Hình thức làm việc",
                            } as Record<string, string>
                          )[key] || key}
                        </span>
                        <meter
                          min={0}
                          max={1}
                          value={value}
                          aria-label={`Điểm ${key}`}
                        />
                        <span>{Math.round(value * 100)}%</span>
                      </div>
                    ),
                  )}
                  {match.explanation.missing_required.length > 0 && (
                    <p className="notice">
                      Cần bổ sung:{" "}
                      {match.explanation.missing_required
                        .map(
                          (id) =>
                            skills.data?.items.find((skill) => skill.id === id)
                              ?.name || id,
                        )
                        .join(", ")}
                      .
                    </p>
                  )}
                  <p className="muted">
                    Điểm phản ánh hồ sơ hiện tại, không phải xác suất được
                    tuyển.
                  </p>
                  <Link className="text-link" to="/profile">
                    Cập nhật hồ sơ <ArrowRight size={15} />
                  </Link>
                </>
              ) : (
                <p className="notice">
                  Chưa có kết quả phù hợp cho vị trí này.
                </p>
              )}
            </section>
          )}
          <section className="panel">
            <h2>
              <Building2 size={18} />
              Doanh nghiệp
            </h2>
            {company.isPending ? (
              <Loading />
            ) : company.isError ? (
              <ErrorState
                error={company.error}
                retry={() => {
                  void company.refetch();
                }}
              />
            ) : (
              <>
                <strong>{company.data.name}</strong>
                <p className="muted">
                  Doanh nghiệp có trong danh sách tuyển dụng.
                </p>
                {company.data.source && (
                  <a
                    className="text-link"
                    href={company.data.source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Trang tuyển dụng của doanh nghiệp <ExternalLink size={14} />
                  </a>
                )}
                <Link
                  to={`/jobs?company_id=${encodeURIComponent(data.company_id)}`}
                  className="text-link"
                >
                  Việc làm tại doanh nghiệp <ArrowRight size={14} />
                </Link>
              </>
            )}
          </section>
        </aside>
      </div>
    </>
  );
}
