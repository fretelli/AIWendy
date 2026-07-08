import { type ReportDetail } from "@/lib/research-api";

export function titleFromReport(report: ReportDetail) {
  return report.display_title || report.title?.replace(/\.pdf$/i, "") || "研报详情";
}

export function summaryPoints(report: ReportDetail) {
  return report.display_summary_points?.length
    ? report.display_summary_points
    : report.note?.display_summary_points?.length
      ? report.note.display_summary_points
      : report.note?.key_points || [];
}
