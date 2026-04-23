import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";
import type {
  BulkDownloadRequest,
  ChallengeListParams,
  CrawlChallengeRequest,
  CrawlSyncRequest,
  DownloadMode,
} from "@/lib/types";

export function useChallenges(params: ChallengeListParams) {
  return useQuery({
    queryKey: queryKeys.challenges(params),
    queryFn: () => api.listChallenges(params),
    placeholderData: (prev) => prev,
  });
}

export function useChallengeDetail(id: string | number | undefined | null) {
  return useQuery({
    queryKey: id ? queryKeys.challenge(id) : ["challenge", "none"],
    queryFn: () => api.getChallenge(id as string | number),
    enabled: id !== undefined && id !== null && id !== "",
  });
}

export function useCrawlSync() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: CrawlSyncRequest) => api.crawlSync(body),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.jobs() }),
  });
}

export function useCrawlChallenge() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: CrawlChallengeRequest) => api.crawlChallenge(body),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.jobs() }),
  });
}

export function useDownloadChallenge() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (args: { id: string | number; mode?: DownloadMode }) =>
      api.downloadChallenge(args.id, args.mode ?? "resume"),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: queryKeys.jobs() });
    },
  });
}

export function useBulkDownload() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: BulkDownloadRequest) => api.bulkDownload(body),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.jobs() }),
  });
}

export function useSyncFiles() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.syncFiles(),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: queryKeys.stats() });
      client.invalidateQueries({ queryKey: ["challenges"] });
    },
  });
}

export function useExportManifest() {
  return useMutation({
    mutationFn: () => api.exportManifest(),
  });
}
