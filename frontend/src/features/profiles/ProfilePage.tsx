import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { Check, Plus, ShieldCheck, Trash2, UserRound } from "lucide-react";
import { api, ApiError } from "../../lib/api";
import { invalidate, queryClient, useMe } from "../../lib/query";
import type { Page, PublicProfile, Skill, User } from "../../lib/types";
import { initials, levels, roleNames, workModes } from "../../lib/format";
import {
  Badge,
  Empty,
  ErrorState,
  Field,
  Heading,
  Loading,
  Pagination,
  PendingButton,
} from "../../components/ui";

const schema = z
  .object({
    display_name: z.string().trim().min(1, "Nhập tên hiển thị.").max(120),
    headline: z.string().trim().max(200, "Tối đa 200 ký tự."),
    location: z.string().trim().min(1, "Nhập địa điểm.").max(120),
    experience_years: z.number().min(0, "Không nhỏ hơn 0.").max(100),
    level: z.enum(["junior", "mid", "senior", "lead"]),
    work_modes: z.array(z.enum(["remote", "hybrid", "onsite"])).max(3),
    salary_min: z.number().min(0).nullable(),
    salary_max: z.number().min(0).nullable(),
  })
  .refine(
    (v) =>
      v.salary_min == null ||
      v.salary_max == null ||
      v.salary_min <= v.salary_max,
    {
      message: "Lương tối đa phải lớn hơn hoặc bằng lương tối thiểu.",
      path: ["salary_max"],
    },
  );
type Form = z.infer<typeof schema>;
const values = (user: User): Form => ({
  display_name: user.display_name,
  ...user.profile,
});
const optionalNumber = (v: string) => (v === "" ? null : Number(v));

export function ProfilePage() {
  const user = useMe().data!;
  return (
    <>
      <Heading
        eyebrow="HỒ SƠ CÁ NHÂN"
        title="Để cơ hội tìm thấy bạn"
        action={
          <Link className="button secondary" to="/profile/privacy">
            <ShieldCheck size={17} />
            Quyền riêng tư
          </Link>
        }
      >
        Thông tin và kỹ năng của bạn giúp hệ thống đánh giá mức độ phù hợp.
      </Heading>
      <div className="profile-banner">
        <span className="avatar big-avatar">{initials(user.display_name)}</span>
        <div>
          <h2>{user.display_name}</h2>
          <p>{user.email}</p>
          <div className="tag-row">
            {user.roles.map((role) => (
              <Badge key={role}>{roleNames[role] || role}</Badge>
            ))}
          </div>
        </div>
      </div>
      <div className="profile-columns">
        <ProfileEditor key={user.id} user={user} />
        <SkillsEditor candidate={user.roles.includes("candidate")} />
      </div>
    </>
  );
}
function ProfileEditor({ user }: { user: User }) {
  const [revision, setRevision] = useState(user.revision);
  const form = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: values(user),
  });
  const save = useMutation({
    mutationFn: (v: Form) => {
      const { display_name, ...profile } = v;
      return api<User>("/users/me", {
        method: "PATCH",
        revision,
        body: { display_name, profile },
      });
    },
    onSuccess: async (next) => {
      setRevision(next.revision);
      form.reset(values(next));
      queryClient.setQueryData(["me"], next);
      await invalidate("profile", "matching", "paths", "jobs", "publicProfile");
    },
  });
  const reload = useMutation({
    mutationFn: () => api<User>("/users/me"),
    onSuccess: (next) => {
      setRevision(next.revision);
      form.reset(values(next));
      queryClient.setQueryData(["me"], next);
      save.reset();
    },
  });
  return (
    <section className="panel">
      <div className="section-heading compact">
        <h2>
          <UserRound size={19} />
          Thông tin nghề nghiệp
        </h2>
      </div>
      <form onSubmit={form.handleSubmit((v) => save.mutate(v))} noValidate>
        <Field
          label="Tên hiển thị"
          id="name"
          error={form.formState.errors.display_name?.message}
        >
          <input
            id="name"
            autoComplete="name"
            {...form.register("display_name")}
          />
        </Field>
        <Field
          label="Giới thiệu ngắn"
          id="headline"
          error={form.formState.errors.headline?.message}
        >
          <input
            id="headline"
            placeholder="Ví dụ: Backend Engineer · Python & ArangoDB"
            {...form.register("headline")}
          />
        </Field>
        <div className="form-grid">
          <Field
            label="Địa điểm"
            id="location"
            error={form.formState.errors.location?.message}
          >
            <input
              id="location"
              autoComplete="address-level2"
              {...form.register("location")}
            />
          </Field>
          <Field
            label="Số năm kinh nghiệm"
            id="experience"
            error={form.formState.errors.experience_years?.message}
          >
            <input
              id="experience"
              type="number"
              min="0"
              max="100"
              step="0.5"
              {...form.register("experience_years", { valueAsNumber: true })}
            />
          </Field>
        </div>
        <Field
          label="Cấp độ"
          id="level"
          error={form.formState.errors.level?.message}
        >
          <select id="level" {...form.register("level")}>
            {Object.entries(levels)
              .filter(([key]) => key !== "unspecified")
              .map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
          </select>
        </Field>
        <fieldset className="check-field">
          <legend>Hình thức làm việc mong muốn</legend>
          <div className="checkbox-row">
            {Object.entries(workModes)
              .filter(([key]) => key !== "unspecified")
              .map(([key, label]) => (
                <label key={key}>
                  <input
                    type="checkbox"
                    value={key}
                    {...form.register("work_modes")}
                  />
                  {label}
                </label>
              ))}
          </div>
        </fieldset>
        <div className="form-grid">
          <Field
            label="Lương tối thiểu (VND)"
            id="salary-min"
            error={form.formState.errors.salary_min?.message}
          >
            <input
              id="salary-min"
              type="number"
              min="0"
              step="1000000"
              placeholder="Để trống nếu chưa xác định"
              {...form.register("salary_min", { setValueAs: optionalNumber })}
            />
          </Field>
          <Field
            label="Lương tối đa (VND)"
            id="salary-max"
            error={form.formState.errors.salary_max?.message}
          >
            <input
              id="salary-max"
              type="number"
              min="0"
              step="1000000"
              {...form.register("salary_max", { setValueAs: optionalNumber })}
            />
          </Field>
        </div>
        {save.isError && <ErrorState error={save.error} />}
        {reload.isError && <ErrorState error={reload.error} />}
        {save.error instanceof ApiError && save.error.status === 412 && (
          <button
            type="button"
            className="button secondary"
            disabled={reload.isPending}
            onClick={() => {
              if (
                window.confirm(
                  "Tải bản mới sẽ thay thế các thay đổi chưa lưu của bạn. Tiếp tục?",
                )
              )
                reload.mutate();
            }}
          >
            Tải bản mới của hồ sơ
          </button>
        )}
        {save.isSuccess && (
          <p className="success-message" role="status">
            <Check size={17} />
            Đã lưu hồ sơ.
          </p>
        )}
        <div className="form-actions">
          <PendingButton
            pending={save.isPending}
            disabled={
              reload.isPending ||
              (save.error instanceof ApiError && save.error.status === 412)
            }
          >
            Lưu hồ sơ
          </PendingButton>
          <span className="muted">Cập nhật bất cứ khi nào bạn cần.</span>
        </div>
      </form>
    </section>
  );
}
function SkillsEditor({ candidate }: { candidate: boolean }) {
  const [offset, setOffset] = useState(0),
    [skillId, setSkillId] = useState(""),
    [proficiency, setProficiency] = useState(3),
    [years, setYears] = useState(1);
  const catalog = useQuery({
    queryKey: ["skills", offset],
    queryFn: ({ signal }) =>
      api<Page<Skill>>(`/skills?limit=20&offset=${offset}`, { signal }),
  });
  const own = useQuery({
    queryKey: ["profile", "self"],
    queryFn: ({ signal }) => api<PublicProfile>("/profiles/me", { signal }),
  });
  const change = useMutation({
    mutationFn: ({ id, remove }: { id: string; remove?: boolean }) =>
      api(`/users/me/skills/${encodeURIComponent(id)}`, {
        method: remove ? "DELETE" : "PUT",
        body: remove ? undefined : { proficiency, years_experience: years },
      }),
    onSuccess: async () => {
      setSkillId("");
      await invalidate("profile", "matching", "jobs");
    },
  });
  return (
    <section className="panel">
      <div className="section-heading compact">
        <h2>Kỹ năng của bạn</h2>
      </div>
      <p className="muted">
        Chọn và lưu từng kỹ năng để hệ thống gợi ý việc làm. Nội dung trong ô
        giới thiệu ngắn không tự chuyển thành kỹ năng. Kỹ năng tự khai báo chưa
        được xác minh.
      </p>
      {candidate && (
        <Link className="text-link" to="/jobs?view=recommended">
          Xem việc làm theo kỹ năng đã lưu
        </Link>
      )}
      {own.isPending ? (
        <Loading />
      ) : own.isError ? (
        <ErrorState
          error={own.error}
          retry={() => {
            void own.refetch();
          }}
        />
      ) : !own.data.skills?.length ? (
        <Empty title="Chưa có kỹ năng">
          Thêm kỹ năng đầu tiên để cải thiện kết quả phù hợp.
        </Empty>
      ) : (
        <ul className="skill-list">
          {own.data.skills.map((skill) => (
            <li key={skill.id}>
              <div>
                <strong>{skill.name}</strong>
                <small>
                  Mức {skill.proficiency}/5 · {skill.years_experience} năm
                  {skill.verified ? " · Đã xác minh" : ""}
                </small>
              </div>
              <button
                className="icon-button"
                disabled={change.isPending}
                aria-label={`Xóa kỹ năng ${skill.name}`}
                onClick={() => {
                  if (window.confirm(`Xóa kỹ năng ${skill.name} khỏi hồ sơ?`))
                    change.mutate({ id: skill.id, remove: true });
                }}
              >
                <Trash2 size={17} />
              </button>
            </li>
          ))}
        </ul>
      )}
      <form
        className="skill-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (skillId) change.mutate({ id: skillId });
        }}
      >
        <Field label="Thêm hoặc cập nhật kỹ năng" id="skill-id">
          <select
            id="skill-id"
            value={skillId}
            onChange={(event) => setSkillId(event.target.value)}
            required
            disabled={catalog.isPending || catalog.isError}
          >
            <option value="">Chọn kỹ năng</option>
            {catalog.data?.items.map((skill) => (
              <option key={skill.id} value={skill.id}>
                {skill.name}
              </option>
            ))}
          </select>
        </Field>
        {catalog.isPending && <Loading label="Đang tải danh mục…" />}
        {catalog.isError && (
          <ErrorState
            error={catalog.error}
            retry={() => {
              void catalog.refetch();
            }}
          />
        )}
        {catalog.data && (catalog.data.has_more || offset > 0) && (
          <Pagination
            offset={offset}
            more={catalog.data.has_more}
            onChange={(value) => {
              setOffset(value);
              setSkillId("");
            }}
            size={20}
          />
        )}
        <div className="form-grid">
          <Field label="Mức thành thạo" id="proficiency">
            <select
              id="proficiency"
              value={proficiency}
              onChange={(event) => setProficiency(Number(event.target.value))}
            >
              {[1, 2, 3, 4, 5].map((v) => (
                <option key={v} value={v}>
                  {v}/5
                </option>
              ))}
            </select>
          </Field>
          <Field label="Số năm sử dụng" id="skill-years">
            <input
              id="skill-years"
              type="number"
              min="0"
              max="100"
              step="0.5"
              required
              value={years}
              onChange={(event) => setYears(Number(event.target.value))}
            />
          </Field>
        </div>
        {change.isError && <ErrorState error={change.error} />}
        {change.isSuccess && (
          <p className="success-message" role="status">
            Đã cập nhật kỹ năng.
          </p>
        )}
        <PendingButton
          pending={change.isPending}
          disabled={!skillId || own.isError}
          className="button secondary full"
        >
          <Plus size={17} />
          Lưu kỹ năng
        </PendingButton>
      </form>
    </section>
  );
}
