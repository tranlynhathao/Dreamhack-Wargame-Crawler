import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";
import type { OpenFolderRequest, SettingsUpdateRequest } from "@/lib/types";

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings(),
    queryFn: () => api.getSettings(),
  });
}

export function useUpdateSettings() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: SettingsUpdateRequest) => api.updateSettings(body),
    onSuccess: (data) => {
      client.setQueryData(queryKeys.settings(), data);
    },
  });
}

export function useRunDoctor() {
  return useMutation({
    mutationFn: () => api.runDoctor(),
  });
}

export function useOpenFolder() {
  return useMutation({
    mutationFn: (body: OpenFolderRequest) => api.openFolder(body),
  });
}
