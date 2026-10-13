import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ShieldCheck, Check } from "lucide-react";
import { api, ApiError } from "../../lib/api";
import { queryClient, useMe } from "../../lib/query";
import type { Privacy, User } from "../../lib/types";
import { ErrorState, Heading, PendingButton } from "../../components/ui";

const choices: { key: keyof Privacy; label: string; detail: string }[] = [
  {
    key: "discoverable",
    label: "Cho phép tìm thấy hồ sơ",
    detail:
      "Người khác có thể xem phần hồ sơ nghề nghiệp được chia sẻ của bạn.",
  },
  {
    key: "allow_in_paths",
    label: "Tham gia đường giới thiệu",
    detail:
      "Cho phép tên và kết nối của bạn xuất hiện trong các đường giới thiệu hợp lệ.",
  },
  {
    key: "employment_visible",
    label: "Chia sẻ nơi làm việc",
    detail: "Hiển thị quan hệ làm việc được phép chia sẻ với doanh nghiệp.",
  },
  {
    key: "skills_visible",
    label: "Chia sẻ kỹ năng",
    detail: "Người xem hồ sơ có thể thấy những kỹ năng bạn đã khai báo.",
  },
];
export function PrivacyPage() {
  const user = useMe().data!;
  const [privacy, setPrivacy] = useState<Privacy>(user.privacy),
    [revision, setRevision] = useState(user.revision);
  const save = useMutation({
    mutationFn: () =>
      api<User>("/users/me/privacy", {
        method: "PATCH",
        revision,
        body: privacy,
      }),
    onSuccess: async (next) => {
      setRevision(next.revision);
      setPrivacy(next.privacy);
      queryClient.setQueryData(["me"], next);
      await Promise.all(
        ["paths", "connections", "publicProfile", "profile", "matching"].map(
          (key) => queryClient.resetQueries({ queryKey: [key] }),
        ),
      );
    },
  });
  const reload = useMutation({
    mutationFn: () => api<User>("/users/me"),
    onSuccess: (next) => {
      setRevision(next.revision);
      setPrivacy(next.privacy);
      queryClient.setQueryData(["me"], next);
      save.reset();
    },
  });
  return (
    <>
      <Heading
        eyebrow="QUYỀN RIÊNG TƯ"
        title="Bạn quyết định điều được chia sẻ"
      >
        Mỗi lựa chọn được lưu vào tài khoản và áp dụng cho các truy vấn mạng
        lưới.
      </Heading>
      <section className="panel privacy-panel">
        <div className="privacy-intro">
          <ShieldCheck size={30} />
          <div>
            <h2>Kết nối với sự chủ động</h2>
            <p>
              Bạn luôn xem được hồ sơ của mình. Người khác chỉ xem các phần bạn
              cho phép.
            </p>
          </div>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate();
          }}
        >
          {choices.map((choice) => (
            <label className="privacy-row" key={choice.key}>
              <div>
                <strong>{choice.label}</strong>
                <p>{choice.detail}</p>
              </div>
              <input
                type="checkbox"
                role="switch"
                checked={privacy[choice.key]}
                onChange={(event) => {
                  setPrivacy({
                    ...privacy,
                    [choice.key]: event.target.checked,
                  });
                  save.reset();
                }}
              />
            </label>
          ))}
          <p className="notice">
            Ẩn nơi làm việc hoặc tắt tham gia đường giới thiệu có thể làm mất
            đường kết nối đến bạn. Yêu cầu giới thiệu được kiểm tra lại quyền
            khi thực hiện.
          </p>
          {save.isError && <ErrorState error={save.error} />}
          {reload.isError && <ErrorState error={reload.error} />}
          {save.error instanceof ApiError && save.error.status === 412 && (
            <button
              type="button"
              className="button secondary"
              onClick={() => {
                if (
                  window.confirm(
                    "Thay thế lựa chọn chưa lưu bằng quyền riêng tư hiện tại?",
                  )
                )
                  reload.mutate();
              }}
            >
              Tải quyền riêng tư mới nhất
            </button>
          )}
          {save.isSuccess && (
            <p className="success-message" role="status">
              <Check size={16} />
              Đã lưu quyền riêng tư.
            </p>
          )}
          <PendingButton
            pending={save.isPending || reload.isPending}
            disabled={
              save.error instanceof ApiError && save.error.status === 412
            }
          >
            Lưu quyền riêng tư
          </PendingButton>
        </form>
      </section>
    </>
  );
}
