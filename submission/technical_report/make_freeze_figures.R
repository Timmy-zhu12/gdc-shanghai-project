args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
if (length(file_arg) > 0) {
  script_path <- normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/")
  report_dir <- dirname(script_path)
} else {
  report_dir <- getwd()
}
root <- normalizePath(file.path(report_dir, "..", ".."), winslash = "/", mustWork = FALSE)
out_dir <- file.path(report_dir, "figures")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

read_csv <- function(path) {
  read.csv(path, stringsAsFactors = FALSE, fileEncoding = "UTF-8-BOM")
}

read_json_text <- function(path) {
  paste(readLines(path, encoding = "UTF-8", warn = FALSE), collapse = "\n")
}

json_number <- function(text, key) {
  pattern <- paste0('"', key, '"\\s*:\\s*([0-9.]+)')
  m <- regexec(pattern, text)
  hit <- regmatches(text, m)[[1]]
  if (length(hit) >= 2) as.numeric(hit[2]) else NA_real_
}

json_numbers <- function(text, key) {
  pattern <- paste0('"', key, '"\\s*:\\s*([0-9.]+)')
  hits <- regmatches(text, gregexpr(pattern, text, perl = TRUE))[[1]]
  if (length(hits) == 0 || hits[1] == -1) return(numeric(0))
  as.numeric(sub('.*:\\s*', '', hits))
}

full_metrics <- read_csv(file.path(root, "validation_speedopt", "full_evidence", "newtraining_metrics.csv"))
rep12_metrics <- read_csv(file.path(root, "validation_speedopt", "freeze_runs", "echobench_20260604_175653", "validation", "newtraining_metrics.csv"))
old_summary <- read_json_text(file.path(root, "validation_speedopt", "old_baseline", "newtraining_summary.json"))
cold_summary <- read_json_text(file.path(root, "validation_speedopt", "speedopt_cold", "newtraining_summary.json"))
full_latency <- read_json_text(file.path(root, "validation_speedopt", "full_evidence", "latency_summary.json"))
rep12_latency <- read_json_text(file.path(root, "validation_speedopt", "freeze_runs", "echobench_20260604_175653", "latency_summary.json"))
server_smoke <- read_json_text(file.path(root, "validation_speedopt", "server_smoke_general_20260604.json"))
server_case <- read_json_text(file.path(root, "validation_speedopt", "server_pipeline_case1_240tok_20260604.json"))
integrated <- read_csv(file.path(report_dir, "integrated_test_results.csv"))

theme <- function() {
  par(family = "sans", fg = "#1f2937", col.axis = "#1f2937", col.lab = "#1f2937", col.main = "#111827")
}

labels <- c("mr", "tr", "ar", "low_ef", "rwma", "la_enlargement", "bradycardia")
pretty <- c("MR", "TR", "AR", "Low EF", "RWMA", "LA enlarge", "Brady")

metric_values <- function(df, metric) {
  values <- df[match(labels, df$label), metric]
  values[is.na(values)] <- 0
  values
}

png(file.path(out_dir, "fig1_f1_full_vs_12frame.png"), width = 1700, height = 950, res = 150)
theme()
par(mar = c(8, 5, 4, 2))
mat <- rbind(metric_values(full_metrics, "f1"), metric_values(rep12_metrics, "f1"))
bp <- barplot(mat, beside = TRUE, ylim = c(0, 1.08), names.arg = pretty, las = 2,
              col = c("#2563eb", "#f59e0b"), ylab = "F1 score",
              main = "EchoBench v1 F1: full evidence vs 12-frame input")
text(bp, mat + 0.035, labels = sprintf("%.2f", mat), cex = 0.72)
legend("topright", legend = c("Full evidence", "12-frame"), fill = c("#2563eb", "#f59e0b"), bty = "n")
grid(nx = NA, ny = NULL, col = "#e5e7eb")
dev.off()

png(file.path(out_dir, "fig2_12frame_metric_profile.png"), width = 1700, height = 950, res = 150)
theme()
par(mar = c(8, 5, 4, 2))
mat <- rbind(
  metric_values(rep12_metrics, "accuracy"),
  metric_values(rep12_metrics, "sensitivity"),
  metric_values(rep12_metrics, "specificity"),
  metric_values(rep12_metrics, "f1")
)
bp <- barplot(mat, beside = TRUE, ylim = c(0, 1.08), names.arg = pretty, las = 2,
              col = c("#0f766e", "#dc2626", "#7c3aed", "#f59e0b"),
              ylab = "Metric value", main = "12-frame diagnostic profile by label")
legend("topright", legend = c("Accuracy", "Sensitivity", "Specificity", "F1"),
       fill = c("#0f766e", "#dc2626", "#7c3aed", "#f59e0b"), bty = "n", cex = 0.88)
grid(nx = NA, ny = NULL, col = "#e5e7eb")
dev.off()

png(file.path(out_dir, "fig3_confusion_components_12frame.png"), width = 1700, height = 950, res = 150)
theme()
par(mar = c(8, 5, 4, 2))
mat <- rbind(
  rep12_metrics[match(labels, rep12_metrics$label), "tp"],
  rep12_metrics[match(labels, rep12_metrics$label), "tn"],
  rep12_metrics[match(labels, rep12_metrics$label), "fp"],
  rep12_metrics[match(labels, rep12_metrics$label), "fn"]
)
rownames(mat) <- c("TP", "TN", "FP", "FN")
bp <- barplot(mat, beside = FALSE, names.arg = pretty, las = 2,
              col = c("#16a34a", "#93c5fd", "#f97316", "#ef4444"),
              ylab = "Case count", main = "12-frame confusion components")
legend("topright", legend = rownames(mat), fill = c("#16a34a", "#93c5fd", "#f97316", "#ef4444"), bty = "n")
dev.off()

png(file.path(out_dir, "fig4_latency_speedopt_freeze.png"), width = 1700, height = 950, res = 150)
theme()
par(mar = c(11, 5, 4, 2))
lat <- c(
  "Old baseline\n12-frame" = json_number(old_summary, "mean_case_runtime_seconds"),
  "SpeedOpt cold\n12-frame" = json_number(cold_summary, "mean_case_runtime_seconds"),
  "Freeze warm\n12-frame" = json_number(rep12_latency, "mean"),
  "Freeze warm\nfull evidence" = json_number(full_latency, "mean"),
  "Server report\ncase 1" = json_number(server_case, "diagnosis_seconds")
)
cols <- c("#64748b", "#2563eb", "#16a34a", "#0f766e", "#dc2626")
bp <- barplot(lat, ylim = c(0, max(lat, na.rm = TRUE) * 1.18), col = cols, ylab = "Seconds per case/request",
              main = "Latency ladder: rule path, cache, and Gemma4 server report", las = 1)
text(bp, lat + max(lat, na.rm = TRUE) * 0.03, labels = sprintf("%.2fs", lat), cex = 0.8)
grid(nx = NA, ny = NULL, col = "#e5e7eb")
dev.off()

png(file.path(out_dir, "fig5_server_smoke_hot_reuse.png"), width = 1500, height = 850, res = 150)
theme()
par(mfrow = c(1, 2), mar = c(6, 5, 4, 2), oma = c(0, 0, 3, 0))
elapsed <- c("First completion" = json_number(server_smoke, "elapsed_seconds"),
             "Second completion" = json_numbers(server_smoke, "elapsed_seconds")[2])
tok_s <- c("First prompt tok/s" = json_number(server_smoke, "prompt_per_second"),
           "Second prompt tok/s" = json_numbers(server_smoke, "prompt_per_second")[2])
bp1 <- barplot(elapsed, col = "#f97316", ylab = "Elapsed seconds",
               main = "Completion latency", ylim = c(0, max(elapsed, na.rm = TRUE) * 1.35), las = 1)
text(bp1, elapsed + max(elapsed, na.rm = TRUE) * 0.08, labels = sprintf("%.2fs", elapsed), cex = 0.8)
grid(nx = NA, ny = NULL, col = "#e5e7eb")
bp2 <- barplot(tok_s, col = "#2563eb", ylab = "Prompt tokens per second",
               main = "Prompt throughput", ylim = c(0, max(tok_s, na.rm = TRUE) * 1.25), las = 1)
text(bp2, tok_s + max(tok_s, na.rm = TRUE) * 0.06, labels = sprintf("%.1f", tok_s), cex = 0.8)
grid(nx = NA, ny = NULL, col = "#e5e7eb")
mtext("llama-server hot reuse smoke test", outer = TRUE, cex = 1.35, font = 2)
dev.off()

png(file.path(out_dir, "fig6_echonet_training_metrics.png"), width = 1500, height = 850, res = 150)
theme()
par(mar = c(8, 5, 4, 2))
echonet <- c("EF MAE" = 7.271, "EF RMSE" = 9.603, "EF corr" = 0.647,
             "Low EF acc" = 0.770, "Low EF F1" = 0.496, "Low EF AUC" = 0.764)
barplot(echonet, col = c("#2563eb", "#2563eb", "#0f766e", "#f59e0b", "#f59e0b", "#f59e0b"),
        ylab = "Metric value", main = "V5 EchoNet-Dynamic calibration held-out metrics", las = 2)
grid(nx = NA, ny = NULL, col = "#e5e7eb")
dev.off()

png(file.path(out_dir, "fig7_evidence_coverage_matrix.png"), width = 1700, height = 950, res = 150)
theme()
par(mar = c(5, 12, 4, 2))
status <- ifelse(integrated$availability == "可用" | integrated$availability == "已完成", "Available",
                 ifelse(integrated$availability == "未下载", "Planned", "Partial"))
datasets <- unique(integrated$dataset)
mat <- sapply(datasets, function(d) {
  c(Available = sum(integrated$dataset == d & status == "Available"),
    Partial = sum(integrated$dataset == d & status == "Partial"),
    Planned = sum(integrated$dataset == d & status == "Planned"))
})
barplot(mat, beside = FALSE, horiz = TRUE, las = 1, cex.names = 0.72,
        col = c("#16a34a", "#f59e0b", "#dc2626"),
        xlab = "Validation entries", main = "Evidence coverage by dataset/source")
legend("topright", legend = rownames(mat), fill = c("#16a34a", "#f59e0b", "#dc2626"), bty = "n")
grid(nx = NA, ny = NULL, col = "#e5e7eb")
dev.off()

png(file.path(out_dir, "fig8_cost_privacy_tradeoff.png"), width = 1500, height = 850, res = 150)
theme()
par(mar = c(11, 5, 4, 2))
score <- c("Marginal cost" = 5, "Offline privacy" = 5, "Format coverage" = 4,
           "Auditability" = 4, "Clinical evidence\nmaturity" = 2, "Mobile parity" = 2)
barplot(score, ylim = c(0, 5), col = c("#16a34a", "#16a34a", "#2563eb", "#0f766e", "#f59e0b", "#f59e0b"),
        ylab = "Qualitative readiness score (1-5)", main = "Engineering trade-off profile for freeze review",
        las = 2, cex.names = 0.85)
abline(h = 3, col = "#9ca3af", lty = 2)
grid(nx = NA, ny = NULL, col = "#e5e7eb")
dev.off()

cat("Freeze figures written to:", out_dir, "\n")
