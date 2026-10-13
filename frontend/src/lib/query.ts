import { QueryClient, useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { session } from "./session";
import type { User } from "./types";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, staleTime: 15000 },
    mutations: { retry: false },
  },
});
session.boundary(() => {
  void queryClient.cancelQueries();
  queryClient.clear();
});
export const privateQuery = {
  staleTime: 0,
  gcTime: 0,
  refetchInterval: 15000,
  refetchOnWindowFocus: "always" as const,
};
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: ({ signal }) => api<User>("/users/me", { signal }),
    refetchInterval: 30000,
    refetchOnWindowFocus: "always",
  });
}
export async function invalidate(...keys: string[]) {
  await Promise.all(
    keys.map((key) => queryClient.invalidateQueries({ queryKey: [key] })),
  );
}
