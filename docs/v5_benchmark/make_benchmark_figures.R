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

full_metrics_path <- file.path(root, "08_benchmark_framework", "runs", "echobench_20260604_114319", "validation", "newtraining_metrics.csv")
rep12_metrics_path <- file.path(root, "08_benchmark_framework", "runs", "echobench_20260604_114016", "validation", "newtraining_metrics.csv")

full <- read.csv(full_metrics_path, stringsAsFactors = FALSE)
rep12 <- read.csv(rep12_metrics_path, stringsAsFactors = FALSE)

labels <- c("mr", "ar", "low_ef", "rwma", "la_enlargement", "bradycardia")
pretty_labels <- c("MR", "AR", "Low EF", "RWMA", "LA enlargement", "Bradycardia")

get_values <- function(df, metric) {
  values <- df[match(labels, df$label), metric]
  values[is.na(values)] <- 0
  values
}

png(file.path(out_dir, "fig1_f1_full_vs_12frame.png"), width = 1400, height = 850, res = 140)
par(mar = c(7, 5, 4, 2), family = "sans")
mat <- rbind(get_values(full, "f1"), get_values(rep12, "f1"))
barplot(
  mat,
  beside = TRUE,
  names.arg = pretty_labels,
  ylim = c(0, 1),
  col = c("#315f72", "#d88c43"),
  ylab = "F1 score",
  main = "EchoBench v1 F1: full evidence vs representative 12-frame input",
  las = 2
)
legend("topright", legend = c("Full evidence", "Representative 12-frame"), fill = c("#315f72", "#d88c43"), bty = "n")
grid(nx = NA, ny = NULL, col = "gray85")
dev.off()

png(file.path(out_dir, "fig2_accuracy_full_vs_12frame.png"), width = 1400, height = 850, res = 140)
par(mar = c(7, 5, 4, 2), family = "sans")
mat <- rbind(get_values(full, "accuracy"), get_values(rep12, "accuracy"))
barplot(
  mat,
  beside = TRUE,
  names.arg = pretty_labels,
  ylim = c(0, 1),
  col = c("#315f72", "#d88c43"),
  ylab = "Accuracy",
  main = "EchoBench v1 accuracy: full evidence vs representative 12-frame input",
  las = 2
)
legend("bottomleft", legend = c("Full evidence", "Representative 12-frame"), fill = c("#315f72", "#d88c43"), bty = "n")
grid(nx = NA, ny = NULL, col = "gray85")
dev.off()

latency_full <- c(mean = 3.761, p50 = 3.311, p90 = 5.012, p95 = 5.513, p99 = 6.704, max = 7.282)
latency_12 <- c(mean = 2.562, p50 = 2.471, p90 = 2.796, p95 = 3.201, p99 = 3.624, max = 3.680)

png(file.path(out_dir, "fig3_latency_full_vs_12frame.png"), width = 1400, height = 850, res = 140)
par(mar = c(6, 5, 4, 2), family = "sans")
mat <- rbind(latency_full, latency_12)
barplot(
  mat,
  beside = TRUE,
  ylim = c(0, 8),
  col = c("#315f72", "#d88c43"),
  ylab = "Seconds per case",
  main = "EchoBench v1 latency percentiles",
  las = 2
)
legend("topleft", legend = c("Full evidence", "Representative 12-frame"), fill = c("#315f72", "#d88c43"), bty = "n")
grid(nx = NA, ny = NULL, col = "gray85")
dev.off()

echonet_metrics <- c(
  "EF MAE" = 7.271,
  "EF RMSE" = 9.603,
  "EF corr" = 0.647,
  "Low EF acc" = 0.770,
  "Low EF F1" = 0.496,
  "Low EF AUC" = 0.764
)

png(file.path(out_dir, "fig4_echonet_training_metrics.png"), width = 1400, height = 850, res = 140)
par(mar = c(7, 5, 4, 2), family = "sans")
barplot(
  echonet_metrics,
  col = c("#315f72", "#315f72", "#6b8f71", "#d88c43", "#d88c43", "#d88c43"),
  ylab = "Metric value",
  main = "V5 EchoNet-Dynamic calibration held-out metrics",
  las = 2
)
grid(nx = NA, ny = NULL, col = "gray85")
dev.off()

cat("Figures written to:", out_dir, "\n")
