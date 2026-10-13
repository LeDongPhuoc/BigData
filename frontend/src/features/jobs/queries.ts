import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Company, Job, Page } from "../../lib/types";

export function useCompanies() {
  return useQuery({
    queryKey: ["companies", "directory"],
    queryFn: async ({ signal }) => {
      const items: Company[] = [];
      for (let offset = 0; offset <= 1000; offset += 100) {
        const page = await api<Page<Company>>(
          `/companies?limit=100&offset=${offset}`,
          { signal },
        );
        items.push(...page.items);
        if (!page.has_more) return { items, truncated: false };
      }
      return { items, truncated: true };
    },
  });
}
export function useJob(id: string) {
  return useQuery({
    queryKey: ["jobs", "detail", id],
    queryFn: ({ signal }) =>
      api<Job>(`/jobs/${encodeURIComponent(id)}`, { signal }),
  });
}
