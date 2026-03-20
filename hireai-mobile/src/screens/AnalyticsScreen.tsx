import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, fontSize, spacing } from "../lib/theme";
import { api } from "../lib/api";

interface ROIData {
  emails_handled: number;
  time_saved_hours: number;
  plan_cost: number;
  hourly_rate: number;
  value_saved: number;
  roi_percentage: number;
  plan_name: string;
}

interface WeeklyStat {
  metric: string;
  this_week: number;
  last_week: number;
  change: number;
  unit: string;
}

interface AnalyticsData {
  total_processed: number;
  auto_reply_rate: number;
  avg_response_time: number;
  emails_escalated: number;
  time_saved_hours: number;
  agent_uptime: number;
  weekly_comparison: WeeklyStat[];
}

export default function AnalyticsScreen() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [roi, setRoi] = useState<ROIData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    const [analyticsRes, roiRes] = await Promise.all([
      api.get<AnalyticsData>("/api/analytics?period=week"),
      api.get<ROIData>("/api/dashboard/roi"),
    ]);
    if (analyticsRes.data) setAnalytics(analyticsRes.data);
    if (roiRes.data) setRoi(roiRes.data);
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.navy} />
      </View>
    );
  }

  const metrics = [
    { label: "Total Processed", value: String(analytics?.total_processed ?? 0), color: colors.navy },
    { label: "Auto-Reply Rate", value: `${analytics?.auto_reply_rate ?? 0}%`, color: colors.success },
    { label: "Avg Response", value: `${analytics?.avg_response_time ?? 0}m`, color: colors.navy },
    { label: "Escalated", value: String(analytics?.emails_escalated ?? 0), color: colors.warning },
    { label: "Time Saved", value: `~${analytics?.time_saved_hours ?? 0}h`, color: colors.success },
    { label: "Uptime", value: `${analytics?.agent_uptime ?? 0}%`, color: colors.navy },
  ];

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.navy} />}
      >
        <Text style={styles.title}>Analytics</Text>

        {/* ROI Card */}
        {roi && (
          <View style={styles.roiCard}>
            <Text style={styles.roiLabel}>This Month</Text>
            <Text style={styles.roiValue}>
              Your agent saved you ${(roi.value_saved ?? 0).toLocaleString()}!
            </Text>
            <Text style={styles.roiSubtext}>
              {roi.roi_percentage > 0
                ? `${roi.roi_percentage.toFixed(0)}% ROI on ${roi.plan_name}`
                : "Connect your agent to start saving"}
            </Text>

            <View style={styles.roiGrid}>
              <View style={styles.roiItem}>
                <Text style={styles.roiItemValue}>{roi.emails_handled}</Text>
                <Text style={styles.roiItemLabel}>Emails</Text>
              </View>
              <View style={styles.roiItem}>
                <Text style={styles.roiItemValue}>~{roi.time_saved_hours}h</Text>
                <Text style={styles.roiItemLabel}>Saved</Text>
              </View>
              <View style={styles.roiItem}>
                <Text style={styles.roiItemValue}>${roi.plan_cost}</Text>
                <Text style={styles.roiItemLabel}>Cost</Text>
              </View>
              <View style={styles.roiItem}>
                <Text style={[styles.roiItemValue, { color: "#166534" }]}>${roi.value_saved}</Text>
                <Text style={styles.roiItemLabel}>Value</Text>
              </View>
            </View>
          </View>
        )}

        {/* Metrics Grid */}
        <Text style={styles.sectionTitle}>This Week</Text>
        <View style={styles.metricsGrid}>
          {metrics.map((m) => (
            <View key={m.label} style={styles.metricCard}>
              <Text style={[styles.metricValue, { color: m.color }]}>{m.value}</Text>
              <Text style={styles.metricLabel}>{m.label}</Text>
            </View>
          ))}
        </View>

        {/* Weekly Comparison */}
        {analytics?.weekly_comparison && analytics.weekly_comparison.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Week over Week</Text>
            {analytics.weekly_comparison.map((item) => {
              const improved =
                item.metric === "Escalated" || item.metric === "Avg Response"
                  ? item.change < 0
                  : item.change > 0;
              return (
                <View key={item.metric} style={styles.compCard}>
                  <Text style={styles.compMetric}>{item.metric}</Text>
                  <View style={styles.compRow}>
                    <Text style={styles.compValue}>
                      {item.this_week}{item.unit}
                    </Text>
                    <Text style={styles.compPrev}>
                      vs {item.last_week}{item.unit}
                    </Text>
                    <Text style={[styles.compChange, { color: improved ? colors.success : colors.danger }]}>
                      {improved ? "↑" : "↓"} {Math.abs(item.change).toFixed(1)}%
                    </Text>
                  </View>
                </View>
              );
            })}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  loadingContainer: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background },
  scroll: { padding: spacing.md, paddingBottom: 100 },
  title: { fontSize: fontSize.xl, fontWeight: "700", color: colors.text, marginBottom: spacing.md },
  sectionTitle: { fontSize: fontSize.lg, fontWeight: "600", color: colors.text, marginBottom: spacing.sm, marginTop: spacing.md },
  roiCard: {
    backgroundColor: colors.successLight,
    borderRadius: 16,
    padding: spacing.lg,
    alignItems: "center",
    marginBottom: spacing.md,
  },
  roiLabel: { fontSize: fontSize.sm, fontWeight: "500", color: colors.success },
  roiValue: { fontSize: fontSize.xl, fontWeight: "700", color: "#166534", marginTop: 4, textAlign: "center" },
  roiSubtext: { fontSize: fontSize.xs, color: colors.success, marginTop: 4 },
  roiGrid: { flexDirection: "row", marginTop: spacing.md, gap: spacing.md },
  roiItem: { alignItems: "center" },
  roiItemValue: { fontSize: fontSize.md, fontWeight: "700", color: "#166534" },
  roiItemLabel: { fontSize: fontSize.xs, color: colors.success, marginTop: 2 },
  metricsGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  metricCard: {
    width: "48%",
    backgroundColor: colors.backgroundCard,
    borderRadius: 12,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  metricValue: { fontSize: fontSize.xl, fontWeight: "700" },
  metricLabel: { fontSize: fontSize.xs, color: colors.textMuted, marginTop: 2 },
  compCard: {
    backgroundColor: colors.backgroundCard,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  compMetric: { fontSize: fontSize.sm, fontWeight: "600", color: colors.text },
  compRow: { flexDirection: "row", alignItems: "center", marginTop: 6, gap: spacing.sm },
  compValue: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text },
  compPrev: { fontSize: fontSize.sm, color: colors.textMuted },
  compChange: { fontSize: fontSize.sm, fontWeight: "600" },
});
