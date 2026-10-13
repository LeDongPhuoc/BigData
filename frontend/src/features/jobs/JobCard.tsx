import { Link } from "react-router-dom";
import { ArrowUpRight, Building2, MapPin, Wallet } from "lucide-react";
import type { Company, JobPreview, MatchResult } from "../../lib/types";
import { levels, money, workModes } from "../../lib/format";
import { Badge } from "../../components/ui";

export function JobCard({
  job,
  company,
  matching,
}: {
  job: JobPreview;
  company?: Company;
  matching?: MatchResult;
}) {
  return (
    <article className="job-card">
      <div className="job-card-top">
        <span className="company-icon">
          <Building2 size={22} />
        </span>
        <div>
          <p className="company-name">{company?.name || "Doanh nghiệp"}</p>
          <h3>
            <Link to={`/jobs/${job.id}`}>{job.title}</Link>
          </h3>
        </div>
        <Link
          to={`/jobs/${job.id}`}
          className="icon-button job-open"
          aria-label={`Xem ${job.title}`}
        >
          <ArrowUpRight size={19} />
        </Link>
      </div>
      <div className="job-meta">
        <span>
          <MapPin size={15} />
          {job.location}
        </span>
        <span>
          <Wallet size={15} />
          {money(job.salary_min, job.salary_max)}
        </span>
      </div>
      {matching && (
        <div className="job-match">
          <Badge tone="green">
            Phù hợp {Math.round(matching.score * 100)}/100
          </Badge>
          <p>
            Kỹ năng khớp:{" "}
            <strong>
              {matching.explanation.requirements
                .filter((skill) => skill.matched)
                .map((skill) => skill.name)
                .join(", ")}
            </strong>
          </p>
          {!matching.eligible && (
            <p className="muted">
              Còn thiếu điều kiện kỹ năng hoặc kinh nghiệm.
            </p>
          )}
        </div>
      )}
      <div className="job-card-bottom">
        <div className="tag-row">
          {job.source && <Badge tone="green">Có nguồn công khai</Badge>}
          <Badge>{workModes[job.work_mode]}</Badge>
          <Badge>{levels[job.level]}</Badge>
        </div>
        <Link to={`/jobs/${job.id}/paths`} className="text-link">
          Tìm đường giới thiệu <ArrowUpRight size={14} />
        </Link>
      </div>
    </article>
  );
}
