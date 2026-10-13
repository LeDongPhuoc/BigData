import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, params } from "../../lib/api";
import type { Company, MatchResult, Page } from "../../lib/types";
import { Empty, ErrorState, Loading, Pagination } from "../../components/ui";
import { JobCard } from "./JobCard";

export function RecommendedJobs({
  companies,
  filters = {},
  offset = 0,
  limit = 12,
  onPage,
}: {
  companies?: Company[];
  filters?: Record<string, string>;
  offset?: number;
  limit?: number;
  onPage?: (offset: number) => void;
}) {
  const matches = useQuery({
    queryKey: ["matching", "recommendations", filters, offset, limit],
    queryFn: ({ signal }) =>
      api<Page<MatchResult>>(
        "/matching/jobs" +
          params({ ...filters, matched_only: "true", offset, limit }),
        { signal },
      ),
  });
  if (matches.isPending) return <Loading label="Đang tìm việc theo hồ sơ…" />;
  if (matches.isError)
    return (
      <ErrorState
        error={matches.error}
        retry={() => {
          void matches.refetch();
        }}
      />
    );
  if (!matches.data.items.length)
    return (
      <Empty title="Chưa có việc làm khớp kỹ năng">
        <p>
          Chọn và lưu kỹ năng trong hồ sơ, hoặc bớt điều kiện lọc. Gợi ý dựa
          trên kỹ năng đã lưu, kinh nghiệm và mong muốn làm việc của bạn.
        </p>
        <Link className="button secondary" to="/profile">
          Cập nhật kỹ năng
        </Link>
      </Empty>
    );
  return (
    <>
      <div className="job-grid search-results recommendation-results">
        {matches.data.items.map((match) => (
          <JobCard
            key={match.job.id}
            job={match.job}
            matching={match}
            company={companies?.find(
              (company) => company.id === match.job.company_id,
            )}
          />
        ))}
      </div>
      {onPage && (
        <Pagination
          offset={offset}
          more={matches.data.has_more}
          busy={matches.isFetching}
          onChange={onPage}
          size={limit}
        />
      )}
    </>
  );
}
