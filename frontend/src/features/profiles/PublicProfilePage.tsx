import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../../lib/api";
import { privateQuery, useMe } from "../../lib/query";
import type { PublicProfile } from "../../lib/types";
import { initials, levels, workModes } from "../../lib/format";
import {
  Badge,
  Empty,
  ErrorState,
  Heading,
  Loading,
} from "../../components/ui";

export function PublicProfilePage() {
  const { userId = "" } = useParams(),
    user = useMe().data!;
  const profile = useQuery({
    ...privateQuery,
    queryKey: ["publicProfile", userId],
    queryFn: ({ signal }) =>
      api<PublicProfile>(`/users/${encodeURIComponent(userId)}/profile`, {
        signal,
      }),
  });
  if (profile.isPending) return <Loading />;
  if (profile.isError)
    return (
      <ErrorState
        error={profile.error}
        retry={() => {
          void profile.refetch();
        }}
      />
    );
  const person = profile.data;
  return (
    <>
      <Heading
        eyebrow="HỒ SƠ ĐƯỢC CHIA SẺ"
        title={person.display_name}
        action={
          user.id !== person.id ? (
            <Link
              to={`/network?invite=${encodeURIComponent(person.id)}`}
              className="button primary"
            >
              Gửi lời mời kết nối
            </Link>
          ) : (
            <Link to="/profile" className="button secondary">
              Chỉnh sửa hồ sơ
            </Link>
          )
        }
      >
        {person.profile.headline || "Chưa có giới thiệu ngắn."}
      </Heading>
      <section className="panel">
        <div className="profile-banner inline">
          <span className="avatar big-avatar">
            {initials(person.display_name)}
          </span>
          <div>
            <h2>{person.profile.headline || person.display_name}</h2>
            <p>
              {person.profile.location} · {person.profile.experience_years} năm
              kinh nghiệm
            </p>
            <div className="tag-row">
              <Badge>{levels[person.profile.level]}</Badge>
              {person.profile.work_modes.map((mode) => (
                <Badge key={mode}>{workModes[mode]}</Badge>
              ))}
            </div>
          </div>
        </div>
        <h2>Kỹ năng</h2>
        {person.skills === null ? (
          <p className="notice">Người này chưa chia sẻ kỹ năng với bạn.</p>
        ) : person.skills.length ? (
          <ul className="skill-list">
            {person.skills.map((skill) => (
              <li key={skill.id}>
                <strong>{skill.name}</strong>
                <span>
                  Mức {skill.proficiency}/5 · {skill.years_experience} năm
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <Empty title="Chưa có kỹ năng được khai báo" />
        )}
        <h2>Nơi làm việc</h2>
        {person.employment === null ? (
          <p className="notice">Người này chưa chia sẻ nơi làm việc với bạn.</p>
        ) : person.employment.length ? (
          person.employment.map((job, i) => (
            <p key={`${job.company_id}-${i}`}>
              <strong>{job.company_name}</strong> · {job.title}
            </p>
          ))
        ) : (
          <Empty title="Chưa có nơi làm việc được chia sẻ" />
        )}
      </section>
    </>
  );
}
