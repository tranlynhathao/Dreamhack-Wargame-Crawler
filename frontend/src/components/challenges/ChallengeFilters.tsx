import { Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CATEGORY_OPTIONS, DIFFICULTY_VALUES, STATUS_OPTIONS } from "@/lib/types";
import type { ChallengeSortKey } from "@/components/challenges/ChallengeTable";

export interface ChallengeFiltersState {
  search: string;
  category: string;
  difficulty: string;
  status: string;
  downloaded: string;
  sort: ChallengeSortKey;
}

export const DEFAULT_FILTERS: ChallengeFiltersState = {
  search: "",
  category: "all",
  difficulty: "all",
  status: "all",
  downloaded: "all",
  sort: "newest",
};

interface ChallengeFiltersProps {
  value: ChallengeFiltersState;
  onChange: (next: ChallengeFiltersState) => void;
}

export function ChallengeFilters({ value, onChange }: ChallengeFiltersProps) {
  const set = <K extends keyof ChallengeFiltersState>(key: K, val: ChallengeFiltersState[K]) =>
    onChange({ ...value, [key]: val });

  const hasActive =
    value.search ||
    value.category !== "all" ||
    value.difficulty !== "all" ||
    value.status !== "all" ||
    value.downloaded !== "all";

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card/40 p-3">
      <div className="relative min-w-[220px] flex-1">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={value.search}
          placeholder="Search title, ID, URL, slug, or description"
          onChange={(e) => set("search", e.target.value)}
          className="pl-8"
        />
      </div>
      <Select value={value.category} onValueChange={(v) => set("category", v)}>
        <SelectTrigger className="w-[170px]">
          <SelectValue placeholder="Category" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All categories</SelectItem>
          {CATEGORY_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={value.difficulty} onValueChange={(v) => set("difficulty", v)}>
        <SelectTrigger className="w-[130px]">
          <SelectValue placeholder="Difficulty" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Any level</SelectItem>
          {DIFFICULTY_VALUES.map((n) => (
            <SelectItem key={n} value={String(n)}>
              Level {n}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={value.status} onValueChange={(v) => set("status", v)}>
        <SelectTrigger className="w-[130px]">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Any status</SelectItem>
          {STATUS_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={value.downloaded} onValueChange={(v) => set("downloaded", v)}>
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="Downloaded" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="yes">Downloaded</SelectItem>
          <SelectItem value="no">Not downloaded</SelectItem>
        </SelectContent>
      </Select>
      <Select value={value.sort} onValueChange={(v) => set("sort", v as ChallengeSortKey)}>
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="Sort" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="newest">Newest</SelectItem>
          <SelectItem value="oldest">Oldest</SelectItem>
          <SelectItem value="title">Title A–Z</SelectItem>
          <SelectItem value="difficulty">Difficulty</SelectItem>
          <SelectItem value="category">Category</SelectItem>
          <SelectItem value="downloaded">Downloaded first</SelectItem>
        </SelectContent>
      </Select>
      {hasActive && (
        <Button variant="ghost" size="sm" onClick={() => onChange(DEFAULT_FILTERS)}>
          <X className="h-3.5 w-3.5" />
          Reset
        </Button>
      )}
    </div>
  );
}
