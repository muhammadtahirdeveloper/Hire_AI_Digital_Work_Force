import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, fontSize, spacing } from "../lib/theme";
import { api } from "../lib/api";

interface Stats {
  emails_processed: number;
  emails_today: number;
  auto_reply_rate: number;
  time_saved_hours: number;
}

interface RecentEmail {
  id: string;
  from: string;
  from_name: string;
  subject: string;
  category: string;
  action: string;
  timestamp: string;
}

interface AgentStatus {
  is_paused: boolean;
  status: string;
  last_processed_at: string | null;
}

export default function DashboardScreen() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [emails, setEmails] = useState<RecentEmail[]>([]);
  const [agent, setAgent] = useState<AgentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    const [statsRes, emailsRes, agentRes] = await Promise.all([
      api.get<Stats>("/api/dashboard/stats"),
      api.get<RecentEmail[]>("/api/emails/recent?limit=5"),
      api.get<AgentStatus>("/api/agent/status"),
    ]);
    if (statsRes.data) setStats(statsRes.data);
    if (emailsRes.data) setEmails(Array.isArray(emailsRes.data) ? emailsRes.data : []);
    if (agentRes.data) setAgent(agentRes.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const toggleAgent = async () => {
    const action = agent?.is_paused ? "resume" : "pause";
    await api.post(`/api/agent/${action}`);
    fetchData();
  };

  const actionColor = (action: string) => {
    switch (action) {
      case "auto_replied": return colors.success;
      case "draft_created": return colors.navy;
      case "escalated": return colors.warning;
      case "blocked": return colors.danger;
      default: return colors.textMuted;
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.navy} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.navy} />}
      >
        {/* Header */}
        <Text style={styles.greeting}>Dashboard</Text>

        {/* Agent Status */}
        <View style={styles.agentCard}>
          <View style={styles.agentRow}>
            <View style={[styles.agentDotBase, { backgroundColor: agent?.is_paused ? colors.warning : colors.success }]} />
            <Text style={styles.agentStatusText}>
              Agent {agent?.is_paused ? "Paused" : "Running"}
            </Text>
          </View>
          <TouchableOpacity style={styles.agentToggle} onPress={toggleAgent} activeOpacity={0.7}>
            <Text style={styles.agentToggleText}>
              {agent?.is_paused ? "Resume" : "Pause"}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Stats Cards */}
        <View style={styles.statsGrid}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats?.emails_processed ?? 0}</Text>
            <Text style={styles.statLabel}>Total Processed</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats?.emails_today ?? 0}</Text>
            <Text style={styles.statLabel}>Today</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={[styles.statValue, { color: colors.success }]}>
              {stats?.auto_reply_rate ?? 0}%
            </Text>
            <Text style={styles.statLabel}>Auto-Reply Rate</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={[styles.statValue, { color: colors.navy }]}>
              ~{stats?.time_saved_hours ?? 0}h
            </Text>
            <Text style={styles.statLabel}>Time Saved</Text>
          </View>
        </View>

        {/* Recent Emails */}
        <Text style={styles.sectionTitle}>Recent Activity</Text>
        {emails.map((email) => (
          <View key={email.id} style={styles.emailCard}>
            <View style={styles.emailHeader}>
              <View style={styles.emailAvatar}>
                <Text style={styles.emailAvatarText}>
                  {(email.from_name || email.from || "?")[0].toUpperCase()}
                </Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.emailSender} numberOfLines={1}>
                  {email.from_name || email.from}
                </Text>
                <Text style={styles.emailSubject} numberOfLines={1}>
                  {email.subject}
                </Text>
              </View>
              <View style={[styles.actionBadge, { backgroundColor: actionColor(email.action) + "20" }]}>
                <Text style={[styles.actionBadgeText, { color: actionColor(email.action) }]}>
                  {email.action.replace("_", " ")}
                </Text>
              </View>
            </View>
          </View>
        ))}

        {emails.length === 0 && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyText}>No recent activity</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  loadingContainer: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background },
  scroll: { padding: spacing.md },
  greeting: { fontSize: fontSize.xl, fontWeight: "700", color: colors.text, marginBottom: spacing.md },
  agentCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.backgroundCard,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  agentRow: { flexDirection: "row", alignItems: "center" },
  agentDotBase: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: spacing.sm,
  },
  agentStatusText: { fontSize: fontSize.md, fontWeight: "600", color: colors.text },
  agentToggle: {
    backgroundColor: colors.navyLight,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 8,
  },
  agentToggleText: { fontSize: fontSize.sm, fontWeight: "600", color: colors.navy },
  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginBottom: spacing.lg },
  statCard: {
    width: "48%",
    backgroundColor: colors.backgroundCard,
    borderRadius: 12,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statValue: { fontSize: fontSize.xl, fontWeight: "700", color: colors.text },
  statLabel: { fontSize: fontSize.xs, color: colors.textMuted, marginTop: 2 },
  sectionTitle: { fontSize: fontSize.lg, fontWeight: "600", color: colors.text, marginBottom: spacing.sm },
  emailCard: {
    backgroundColor: colors.backgroundCard,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  emailHeader: { flexDirection: "row", alignItems: "center" },
  emailAvatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.navyLight,
    alignItems: "center",
    justifyContent: "center",
    marginRight: spacing.sm,
  },
  emailAvatarText: { fontSize: fontSize.sm, fontWeight: "600", color: colors.navy },
  emailSender: { fontSize: fontSize.sm, fontWeight: "600", color: colors.text },
  emailSubject: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 1 },
  actionBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  actionBadgeText: { fontSize: 10, fontWeight: "600" },
  emptyState: { alignItems: "center", paddingVertical: spacing.xl },
  emptyText: { fontSize: fontSize.sm, color: colors.textMuted },
});
