import { useQuery } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";

export function useBackendHealth() {
  return useQuery({
    queryKey: queryKeys.health(),
    queryFn: () => api.health(),
    refetchInterval: 5_000,
    retry: 0,
    staleTime: 0,
  });
}
