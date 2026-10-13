export const workModes: Record<string, string> = {
  remote: "Từ xa",
  hybrid: "Kết hợp",
  onsite: "Tại văn phòng",
  unspecified: "Chưa rõ hình thức",
};
export const levels: Record<string, string> = {
  junior: "Junior",
  mid: "Middle",
  senior: "Senior",
  lead: "Lead",
  unspecified: "Chưa rõ cấp độ",
};
export const statusNames: Record<string, string> = {
  pending: "Đang chờ",
  accepted: "Đã chấp nhận",
  rejected: "Đã từ chối",
  cancelled: "Đã hủy",
  submitted: "Đã giới thiệu",
  completed: "Hoàn tất",
  expired: "Hết hạn",
  blocked: "Đã chặn",
};
export const roleNames: Record<string, string> = {
  candidate: "Ứng viên",
  referrer: "Người giới thiệu",
  recruiter: "Nhà tuyển dụng",
  admin: "Quản trị viên",
};
export function money(min?: number | null, max?: number | null) {
  const format = (v: number) =>
    new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(
      v / 1000000,
    );
  if (min != null && max != null)
    return `${format(min)} – ${format(max)} triệu ₫`;
  if (min != null) return `Từ ${format(min)} triệu ₫`;
  if (max != null) return `Đến ${format(max)} triệu ₫`;
  return "Chưa có thông tin lương";
}
export const dateTime = (v: string) =>
  new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(v));
export const initials = (v: string) =>
  v
    .trim()
    .split(/\s+/)
    .slice(-2)
    .map((s) => s[0])
    .join("")
    .toUpperCase();
