import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  ChallengeStatusBadge,
  DownloadBadge,
  DownloadStatusBadge,
  JobStatusBadge,
  SessionStatusBadge,
} from "@/components/common/StatusBadge";

describe("status badges", () => {
  it("renders session status", () => {
    render(<SessionStatusBadge value="valid" />);
    expect(screen.getByText("Valid")).toBeInTheDocument();
  });
  it("renders job status", () => {
    render(<JobStatusBadge value="running" />);
    expect(screen.getByText("Running")).toBeInTheDocument();
  });
  it("renders challenge status", () => {
    render(<ChallengeStatusBadge value="solved" />);
    expect(screen.getByText("Solved")).toBeInTheDocument();
  });
  it("renders download state", () => {
    render(<DownloadBadge downloaded={false} hasAttachments={true} />);
    expect(screen.getByText("Not downloaded")).toBeInTheDocument();
  });
  it("renders detailed download status", () => {
    render(<DownloadStatusBadge value="partial" />);
    expect(screen.getByText("Partial download")).toBeInTheDocument();
  });
});
