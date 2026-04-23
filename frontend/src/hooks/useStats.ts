import { useQuery } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";

export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats(),
    queryFn: () => api.getStats(),
    refetchInterval: 15_000,
  });
}
