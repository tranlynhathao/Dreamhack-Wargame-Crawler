import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";
import type { SessionImportRequest } from "@/lib/types";

export function useSession(refresh = true) {
  return useQuery({
    queryKey: queryKeys.session(),
    queryFn: () => api.getSession(refresh),
  });
}

export function useImportSession() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: SessionImportRequest) => api.importSession(body),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.session() }),
  });
}

export function useClearSession() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.clearSession(),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.session() }),
  });
}

export function useTestSession() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.testSession(),
    onSuccess: (data) => client.setQueryData(queryKeys.session(), data),
  });
}
